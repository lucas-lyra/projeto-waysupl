import base64
import io
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# --- 1. CONEXÃO COM O BANCO DE DADOS (SUPABASE) ---
# As chaves devem estar configuradas no 'Secrets' do Streamlit Cloud
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Criamos o cliente globalmente para que todas as funções o alcancem
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. CONFIGURAÇÕES VISUAIS ---
DIR_BASE = Path(__file__).resolve().parent
CAMINHO_LOGO = DIR_BASE / "assets" / "logo-way.png"
CAMINHO_FUNDO = DIR_BASE / "assets" / "way-fundo.png" 
COR_MARCA = "#E31837"

ORDEM_COLUNAS = [
    "Filial", "Código de Barras", "Nome", "Marca", 
    "Validade", "Quantidade", "Observações"
]
ORDEM_EXIBICAO = [
    "Código de Barras", "Nome", "Marca", "Validade", "Quantidade"
]
FILIAL_PADRAO = "Principal"

# --- 3. LÓGICA DE AUTENTICAÇÃO ---

def gerenciar_login():
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        st.markdown(f"<h2 style='text-align: center; color: {COR_MARCA};'>LOGIN WAY SUPLEMENTOS</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Senha", type="password")
            if st.form_submit_button("Entrar na Conta"):
                try:
                    res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res.user
                    st.rerun()
                except Exception:
                    st.error("Credenciais inválidas. Verifique seu email e senha no Supabase.")
        st.stop()
    
    if st.sidebar.button("🚪 Sair do Sistema"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

# --- 4. FUNÇÕES DE DADOS (SUPABASE) ---

def carregar_filiais() -> list[str]:
    try:
        res = supabase.table("filiais").select("nome").execute()
        return [item['nome'] for item in res.data] if res.data else [FILIAL_PADRAO]
    except:
        return [FILIAL_PADRAO]

def adicionar_filial(nome: str) -> bool:
    nome = nome.strip()
    if not nome: return False
    try:
        supabase.table("filiais").insert({"nome": nome}).execute()
        return True
    except:
        return False

def excluir_filial(nome: str) -> None:
    try:
        supabase.table("filiais").delete().eq("nome", nome).execute()
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")

def carregar_estoque_completo() -> pd.DataFrame:
    try:
        res = supabase.table("produtos").select("*, filiais(nome)").execute()
        if not res.data:
            return pd.DataFrame(columns=ORDEM_COLUNAS)
        
        dados = []
        for p in res.data:
            dados.append({
                "id": p["id"],
                "Filial": p["filiais"]["nome"] if p.get("filiais") else "Sem Filial",
                "Código de Barras": p["codigo_barras"],
                "Nome": p["nome"],
                "Marca": p["marca"],
                "Validade": p["validade"],
                "Quantidade": p["quantidade"],
                "Observações": p["observacoes"]
            })
        return pd.DataFrame(dados)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(columns=ORDEM_COLUNAS)

def adicionar_produto(filial, codigo, nome, marca, validade, quantidade, observacoes):
    try:
        # Busca o ID da filial pelo nome
        res_f = supabase.table("filiais").select("id").eq("nome", filial).single().execute()
        if not res_f.data:
            st.error("Filial não encontrada.")
            return
        
        f_id = res_f.data["id"]
        
        supabase.table("produtos").insert({
            "filial_id": f_id,
            "codigo_barras": str(codigo),
            "nome": str(nome),
            "marca": str(marca),
            "validade": str(validade),
            "quantidade": int(quantidade),
            "observacoes": str(observacoes)
        }).execute()
        st.success("Produto adicionado com sucesso!")
    except Exception as e:
        st.error(f"Erro ao adicionar: {e}")

def remover_produtos(ids: list[int]) -> None:
    if ids:
        try:
            supabase.table("produtos").delete().in_("id", ids).execute()
        except Exception as e:
            st.error(f"Erro ao remover: {e}")

# --- 5. FUNÇÕES DE ESTÉTICA ---

def _obter_logo_base64() -> str | None:
    if CAMINHO_LOGO.exists():
        try:
            with open(CAMINHO_LOGO, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except: pass
    return None

def _injetar_css_way() -> None:
    fundo_b64 = ""
    if CAMINHO_FUNDO.exists():
        try:
            with open(CAMINHO_FUNDO, "rb") as f:
                fundo_b64 = base64.b64encode(f.read()).decode()
        except: pass

    bg_style = ""
    if fundo_b64:
        bg_style = f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/png;base64,{fundo_b64}");
            background-size: cover; background-position: center;
            background-repeat: no-repeat; background-attachment: fixed;
        }}
        [data-testid="stHeader"], [data-testid="stAppViewContainer"] {{
            background-color: transparent !important;
        }}
        [data-testid="stAppViewContainer"]::before {{
            content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(14, 17, 23, 0.85); z-index: -1;
        }}
        </style>
        """
    st.markdown(bg_style, unsafe_allow_html=True)
    st.markdown(f"""
        <style>
        .stButton > button {{ background-color: {COR_MARCA} !important; color: white !important; }}
        [data-testid="stMetric"], .stDataFrame {{ background-color: rgba(20, 20, 25, 0.8) !important; border-radius: 10px; padding: 10px; }}
        </style>
        """, unsafe_allow_html=True)

# --- 6. IMPORTAÇÃO / EXPORTAÇÃO ---

def exportar_planilha(df_filial: pd.DataFrame) -> bytes:
    df_export = df_filial[ORDEM_EXIBICAO].copy() if not df_filial.empty else pd.DataFrame(columns=ORDEM_EXIBICAO)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_export.to_excel(writer, sheet_name="Estoque", index=False)
    return buffer.getvalue()

# --- 7. MAIN ---

def main():
    st.set_page_config(page_title="Estoque Way Suplementos", page_icon="📦", layout="wide")
    _injetar_css_way()
    
    gerenciar_login()

    st.title("📦 ESTOQUE WAY SUPLEMENTOS")

    filiais = carregar_filiais()
    
    with st.sidebar:
        logo_b64 = _obter_logo_base64()
        if logo_b64:
            st.markdown(f'<div style="text-align:center;"><img src="data:image/png;base64,{logo_b64}" style="max-height:80px;" /></div>', unsafe_allow_html=True)
        
        st.header("🏪 Filial")
        filial_selecionada = st.selectbox("Selecionar filial", options=filiais)

    st.caption(f"Filial: **{filial_selecionada}** | Logado como: {st.session_state.user.email}")

    with st.expander("➕ Adicionar Produto", expanded=True):
        with st.form("form_adicionar", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cod = col1.text_input("Código de Barras")
            nom = col2.text_input("Nome")
            col3, col4 = st.columns(2)
            mar = col3.text_input("Marca")
            val = col4.date_input("Validade", format="DD/MM/YYYY")
            col_q, col_o = st.columns([1, 2])
            qtd = col_q.number_input("Quantidade", min_value=1, value=1)
            obs = col_o.text_input("Observações")
            if st.form_submit_button("Adicionar") and nom:
                adicionar_produto(filial_selecionada, cod, nom, mar, val, qtd, obs)
                st.rerun()

    df_completo = carregar_estoque_completo()
    df_filial = df_completo[df_completo["Filial"] == filial_selecionada].copy()

    tab1, tab2 = st.tabs(["📋 Estoque", "🔍 Buscar"])

    with tab1:
        if not df_filial.empty:
            st.dataframe(df_filial[ORDEM_EXIBICAO], use_container_width=True, hide_index=True)
            rem = st.multiselect("Remover Produtos", options=df_filial.index.tolist(), format_func=lambda x: f"{df_filial.loc[x, 'Nome']}")
            if st.button("Excluir Selecionados") and rem:
                remover_produtos(df_filial.loc[rem, "id"].tolist())
                st.rerun()
        else: st.info("Estoque vazio.")

    with tab2:
        termo = st.text_input("Buscar por nome, marca ou código")
        if termo:
            mask = df_filial.apply(lambda r: termo.lower() in str(r).lower(), axis=1)
            st.dataframe(df_filial[mask][ORDEM_EXIBICAO], use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()