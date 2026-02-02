import base64
import io
import os
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client


SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_supabase() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase()

# --- 2. CONFIGURAÇÕES VISUAIS  ---
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

# --- 3. LÓGICA DE AUTENTICAÇÃO  ---

def gerenciar_login():
    if "user" not in st.session_state:
        st.session_state.user = None

    if st.session_state.user is None:
        # Mantendo o estilo centralizado para o login
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

# --- 4. FUNÇÕES DE DADOS  ---

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
    res = supabase.table("produtos").select("*, filiais(nome)").execute()
    if not res.data:
        return pd.DataFrame(columns=ORDEM_COLUNAS)
    
    dados = []
    for p in res.data:
        dados.append({
            "id": p["id"],
            "Filial": p["filiais"]["nome"],
            "Código de Barras": p["codigo_barras"],
            "Nome": p["nome"],
            "Marca": p["marca"],
            "Validade": p["validade"],
            "Quantidade": p["quantidade"],
            "Observações": p["observacoes"]
        })
    return pd.DataFrame(dados)

def adicionar_produto(filial, codigo, nome, marca, validade, quantidade, observacoes):
    res_f = supabase.table("filiais").select("id").eq("nome", filial).single().execute()
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

def remover_produtos(ids: list[int]) -> None:
    if ids:
        supabase.table("produtos").delete().in_("id", ids).execute()

# --- 5. FUNÇÕES DE ESTÉTICA  ---

def _obter_logo_base64() -> str | None:
    if CAMINHO_LOGO.exists():
        try:
            with open(CAMINHO_LOGO, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except: pass
    return None

def _injetar_css_way(logo_b64: str | None) -> None:
    fundo_b64 = ""
    try:
        if CAMINHO_FUNDO.exists():
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
        .main {{ background-color: transparent; }}
        .stMarkdown, .stMarkdown p, .stMetric label, h1, h2, h3, label {{ 
            color: #FAFAFA !important; text-shadow: 1px 1px 3px rgba(0,0,0,1);
        }}
        .stButton > button, .stFormSubmitButton > button, .stDownloadButton > button {{
            background-color: {COR_MARCA} !important; color: white !important;
            border: none !important; width: 100%;
        }}
        [data-testid="stMetric"], [data-testid="stExpander"], .stDataFrame {{
            background-color: rgba(20, 20, 25, 0.8) !important;
            border: 1px solid rgba(255,255,255,0.1); border-radius: 10px; padding: 10px;
        }}
        </style>
        """, unsafe_allow_html=True)

# --- 6. IMPORTAÇÃO / EXPORTAÇÃO ---

def exportar_planilha(df_filial: pd.DataFrame) -> bytes:
    df_export = df_filial[ORDEM_EXIBICAO].copy() if not df_filial.empty else pd.DataFrame(columns=ORDEM_EXIBICAO)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_export.to_excel(writer, sheet_name="Estoque", index=False)
    return buffer.getvalue()

def importar_planilha(arquivo, filial: str) -> tuple[int, str]:
    try:
        df = pd.read_excel(arquivo)
        count = 0
        for _, row in df.iterrows():
            nome = str(row.get("Nome", row.get("Nome do Produto", "")))
            if nome and nome != "nan":
                adicionar_produto(
                    filial, 
                    str(row.get("Código de Barras", "")),
                    nome,
                    str(row.get("Marca", "")),
                    str(row.get("Validade", "")),
                    int(row.get("Quantidade", 0)),
                    ""
                )
                count += 1
        return count, ""
    except Exception as e:
        return 0, str(e)

# --- 7. MAIN  ---

def main():
    st.set_page_config(page_title="Estoque Way Suplementos", page_icon="📦", layout="wide")
    _injetar_css_way(_obter_logo_base64())
    
    # LOGIN OBRIGATÓRIO
    gerenciar_login()

    st.title("📦 ESTOQUE WAY SUPLEMENTOS")

    filiais = carregar_filiais()
    if "filial_selecionada" not in st.session_state:
        st.session_state.filial_selecionada = filiais[0]

    with st.sidebar:
        logo_b64 = _obter_logo_base64()
        if logo_b64:
            st.markdown(f'<div style="text-align:center; margin-bottom:1.5rem;"><img src="data:image/png;base64,{logo_b64}" style="max-height:80px;" /></div>', unsafe_allow_html=True)
        
        st.header("🏪 Filial")
        filial_selecionada = st.selectbox("Selecionar filial", options=filiais, index=filiais.index(st.session_state.filial_selecionada) if st.session_state.filial_selecionada in filiais else 0)
        st.session_state.filial_selecionada = filial_selecionada

        with st.expander("⚙️ Gerenciar Filiais"):
            with st.form("form_filial", clear_on_submit=True):
                nova_filial = st.text_input("Cadastrar nova filial")
                if st.form_submit_button("Cadastrar") and nova_filial:
                    if adicionar_filial(nova_filial): st.rerun()

            filial_excluir = st.selectbox("Excluir filial", options=filiais)
            if st.button("Confirmar Exclusão") and len(filiais) > 1:
                excluir_filial(filial_excluir)
                st.rerun()

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
                st.success("Produto adicionado ao Supabase!")
                st.rerun()

    # Dados filtrados
    df_completo = carregar_estoque_completo()
    df_filial = df_completo[df_completo["Filial"] == filial_selecionada].copy()

    # Importar/Exportar
    c_exp, c_imp, _ = st.columns([1, 1, 3])
    with c_exp:
        st.download_button("📥 Exportar Excel", data=exportar_planilha(df_filial), file_name=f"estoque_{filial_selecionada}.xlsx")
    with c_imp:
        arq = st.file_uploader("📤 Importar Excel", type=["xlsx"])
        if arq and st.button("Iniciar Importação"):
            q, erro = importar_planilha(arq, filial_selecionada)
            if not erro: st.success(f"{q} produtos importados!"); st.rerun()

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📋 Estoque Completo", "🔍 Buscar", "⚠️ Vencimentos"])

    with tab1:
        if not df_filial.empty:
            st.dataframe(df_filial[ORDEM_EXIBICAO], use_container_width=True, hide_index=True)
            with st.form("form_rem"):
                rem = st.multiselect("Remover Produtos", options=df_filial.index.tolist(), format_func=lambda x: f"{df_filial.loc[x, 'Nome']}")
                if st.form_submit_button("Excluir Selecionados"):
                    remover_produtos(df_filial.loc[rem, "id"].tolist())
                    st.rerun()
        else: st.info("Estoque vazio.")

    with tab2:
        termo = st.text_input("Buscar por nome, marca ou código")
        if termo:
            mask = df_filial.apply(lambda r: termo.lower() in str(r).lower(), axis=1)
            st.dataframe(df_filial[mask][ORDEM_EXIBICAO], use_container_width=True, hide_index=True)

    with tab3:
        hoje = pd.Timestamp(datetime.now().date())
        df_filial["Validade_DT"] = pd.to_datetime(df_filial["Validade"], errors='coerce')
        vencendo = df_filial[df_filial["Validade_DT"] <= (hoje + pd.Timedelta(days=30))]
        st.dataframe(vencendo[ORDEM_EXIBICAO], use_container_width=True, hide_index=True)

    # Rodapé
    st.divider()
    col_a, col_b = st.columns(2)
    col_a.metric("Total de Itens", len(df_filial))
    col_b.metric("Qtd Total", int(df_filial["Quantidade"].sum()) if not df_filial.empty else 0)

if __name__ == "__main__":
    main()