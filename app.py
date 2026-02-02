import base64
import io
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# --- 1. CONEXÃO COM O SUPABASE ---
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 2. CONFIGURAÇÕES VISUAIS ---
DIR_BASE = Path(__file__).resolve().parent
CAMINHO_LOGO = DIR_BASE / "assets" / "logo-way.png"
CAMINHO_FUNDO = DIR_BASE / "assets" / "way-fundo.png" 
COR_MARCA = "#E31837"

ORDEM_COLUNAS = ["Filial", "Código de Barras", "Nome", "Marca", "Validade", "Quantidade", "Observações"]
ORDEM_EXIBICAO = ["Código de Barras", "Nome", "Marca", "Validade", "Quantidade"]
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
                    st.error("Credenciais inválidas.")
        st.stop()
    
    if st.sidebar.button("🚪 Sair do Sistema"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

# --- 4. FUNÇÕES DE DADOS (FILIAIS E PRODUTOS) ---

def carregar_filiais():
    try:
        res = supabase.table("filiais").select("nome").execute()
        return [item['nome'] for item in res.data] if res.data else [FILIAL_PADRAO]
    except:
        return [FILIAL_PADRAO]

def adicionar_filial(nome: str):
    nome = nome.strip()
    if nome:
        try:
            supabase.table("filiais").insert({"nome": nome}).execute()
            st.success(f"Filial '{nome}' cadastrada!")
            return True
        except:
            st.error("Erro ao cadastrar filial.")
    return False

def excluir_filial(nome: str):
    try:
        supabase.table("filiais").delete().eq("nome", nome).execute()
        st.warning(f"Filial '{nome}' removida!")
        return True
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")
    return False

def adicionar_produto(filial, codigo, nome, marca, validade, quantidade, observacoes):
    try:
        res_f = supabase.table("filiais").select("id").eq("nome", filial).single().execute()
        f_id = res_f.data["id"]
        
        # Salvamos a data como string ISO para o banco, mas a exibição trataremos depois
        supabase.table("produtos").insert({
            "filial_id": f_id,
            "codigo_barras": str(codigo),
            "nome": str(nome),
            "marca": str(marca),
            "validade": str(validade),
            "quantidade": int(quantidade),
            "observacoes": str(observacoes)
        }).execute()
        st.success("Produto cadastrado!")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def carregar_estoque_completo():
    res = supabase.table("produtos").select("*, filiais(nome)").execute()
    if not res.data:
        return pd.DataFrame(columns=ORDEM_COLUNAS)
    
    dados = []
    for p in res.data:
        # Formatação da data para o padrão Brasileiro (DD/MM/YYYY)
        data_formatada = ""
        if p.get("validade"):
            try:
                dt = datetime.strptime(p["validade"], "%Y-%m-%d")
                data_formatada = dt.strftime("%d/%m/%Y")
            except:
                data_formatada = p["validade"]

        dados.append({
            "id": p["id"],
            "Filial": p["filiais"]["nome"] if p.get("filiais") else "N/A",
            "Código de Barras": p["codigo_barras"],
            "Nome": p["nome"],
            "Marca": p["marca"],
            "Validade": data_formatada,
            "Quantidade": p["quantidade"],
            "Observações": p["observacoes"]
        })
    return pd.DataFrame(dados)

# --- 5. ESTÉTICA E CSS ---

def _obter_base64(caminho):
    if caminho.exists():
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

def _injetar_estilo():
    fundo_b64 = _obter_base64(CAMINHO_FUNDO)
    estilo = f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background-image: url("data:image/png;base64,{fundo_b64 if fundo_b64 else ''}");
        background-size: cover; background-attachment: fixed;
    }}
    [data-testid="stAppViewContainer"]::before {{
        content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background-color: rgba(14, 17, 23, 0.85); z-index: -1;
    }}
    .stButton > button {{ background-color: {COR_MARCA} !important; color: white !important; }}
    [data-testid="stMetric"], .stDataFrame, [data-testid="stExpander"] {{
        background-color: rgba(20, 20, 25, 0.8) !important; border-radius: 10px;
    }}
    </style>
    """
    st.markdown(estilo, unsafe_allow_html=True)

# --- 6. EXECUÇÃO PRINCIPAL ---

def main():
    st.set_page_config(page_title="Way Suplementos", page_icon="📦", layout="wide")
    _injetar_estilo()
    gerenciar_login()

    st.title("📦 CONTROLE DE ESTOQUE")
    
    filiais = carregar_filiais()

    # --- BARRA LATERAL (FILIAIS) ---
    with st.sidebar:
        logo_b64 = _obter_base64(CAMINHO_LOGO)
        if logo_b64:
            st.markdown(f'<div style="text-align:center;"><img src="data:image/png;base64,{logo_b64}" style="max-height:80px;" /></div>', unsafe_allow_html=True)
        
        st.header("🏪 Unidade")
        filial_selecionada = st.selectbox("Selecionar filial", options=filiais)

        with st.expander("⚙️ Gerenciar Filiais"):
            # Adicionar Filial
            nova_f = st.text_input("Nova Filial")
            if st.button("➕ Adicionar"):
                if adicionar_filial(nova_f): st.rerun()
            
            st.divider()
            
            # Excluir Filial
            f_excluir = st.selectbox("Excluir Filial", options=filiais)
            if st.button("🗑️ Remover"):
                if excluir_filial(f_excluir): st.rerun()

    st.caption(f"Filial: **{filial_selecionada}** | Usuário: {st.session_state.user.email}")

    # --- FORMULÁRIO DE PRODUTO ---
    with st.expander("➕ Novo Lançamento", expanded=True):
        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cod = col1.text_input("Código de Barras")
            nom = col2.text_input("Nome do Produto")
            mar = st.text_input("Marca")
            col3, col4 = st.columns(2)
            val = col3.date_input("Validade", format="DD/MM/YYYY") # Input já em formato BR
            qtd = col4.number_input("Quantidade", min_value=1)
            obs = st.text_area("Observações")
            if st.form_submit_button("Salvar no Sistema"):
                adicionar_produto(filial_selecionada, cod, nom, mar, val, qtd, obs)
                st.rerun()

    # --- TABELA DE ESTOQUE ---
    df = carregar_estoque_completo()
    df_f = df[df["Filial"] == filial_selecionada]
    
    st.subheader(f"Lista de Produtos - {filial_selecionada}")
    st.dataframe(df_f[ORDEM_EXIBICAO], use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()