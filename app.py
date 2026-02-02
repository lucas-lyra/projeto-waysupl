import base64
import io
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# --- 1. CONEXÃO COM O SUPABASE ---
# As chaves devem estar no "Secrets" do Streamlit Cloud exatamente com esses nomes
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# Criamos o cliente global para uso em todas as funções
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
                    st.error("Credenciais inválidas. Verifique seu email e senha no Supabase.")
        st.stop()
    
    if st.sidebar.button("🚪 Sair do Sistema"):
        supabase.auth.sign_out()
        st.session_state.user = None
        st.rerun()

# --- 4. FUNÇÕES DE DADOS ---

def carregar_filiais():
    try:
        res = supabase.table("filiais").select("nome").execute()
        return [item['nome'] for item in res.data] if res.data else [FILIAL_PADRAO]
    except:
        return [FILIAL_PADRAO]

def adicionar_produto(filial, codigo, nome, marca, validade, quantidade, observacoes):
    try:
        # Busca ID da filial selecionada
        res_f = supabase.table("filiais").select("id").eq("nome", filial).single().execute()
        if not res_f.data:
            st.error("Filial não encontrada no banco.")
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
        st.success("Produto cadastrado!")
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def carregar_estoque_completo():
    res = supabase.table("produtos").select("*, filiais(nome)").execute()
    if not res.data:
        return pd.DataFrame(columns=ORDEM_COLUNAS)
    
    dados = []
    for p in res.data:
        dados.append({
            "id": p["id"],
            "Filial": p["filiais"]["nome"] if p.get("filiais") else "N/A",
            "Código de Barras": p["codigo_barras"],
            "Nome": p["nome"],
            "Marca": p["marca"],
            "Validade": p["validade"],
            "Quantidade": p["quantidade"],
            "Observações": p["observacoes"]
        })
    return pd.DataFrame(dados)

# --- 5. ESTÉTICA E CSS ---

def _obter_base64(caminho):
    if caminho.exists():
        try:
            with open(caminho, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except: pass
    return None

def _obter_logo_base64():
    if CAMINHO_LOGO.exists():
        try:
            with open(CAMINHO_LOGO, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except: pass
    return None

def _injetar_estilo():
    fundo_b64 = _obter_base64(CAMINHO_FUNDO)
    
    estilo_customizado = f"""
    <style>
    /* 1. Imagem de Fundo com Sobreposição Escura */
    [data-testid="stAppViewContainer"] {{
        background-image: url("data:image/png;base64,{fundo_b64 if fundo_b64 else ''}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-attachment: fixed;
    }}
    
    [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: fixed;
        top: 0; left: 0; width: 100%; height: 100%;
        background-color: rgba(14, 17, 23, 0.85);
        z-index: -1;
    }}

    /* 2. Estilização dos Textos */
    .stMarkdown, h1, h2, h3, label, .stMetric {{
        color: #FAFAFA !important;
        text-shadow: 1px 1px 3px rgba(0,0,0,1);
    }}

    /* 3. Botão Vermelho (Cor da Way Suplementos) */
    .stButton > button {{
        background-color: {COR_MARCA} !important;
        color: white !important;
        border: none !important;
        width: 100%;
        border-radius: 5px;
        transition: 0.3s;
    }}
    
    .stButton > button:hover {{
        background-color: #ff1f3d !important;
        transform: scale(1.02);
    }}

    /* 4. Cards (Métricas e Tabelas) */
    [data-testid="stMetric"], .stDataFrame, [data-testid="stExpander"] {{
        background-color: rgba(20, 20, 25, 0.8) !important;
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 15px;
    }}
    </style>
    """
    st.markdown(estilo_customizado, unsafe_allow_html=True)

# --- 6. FUNÇÃO PRINCIPAL ---

def main():
    st.set_page_config(page_title="Way Suplementos", page_icon="📦", layout="wide")
    _injetar_estilo()
    
    gerenciar_login()

    st.title("📦 CONTROLE DE ESTOQUE")
    
    filiais = carregar_filiais()
    
    with st.sidebar:
        logo_b64 = _obter_logo_base64()
        if logo_b64:
            st.markdown(f'<div style="text-align:center; margin-bottom:1.5rem;"><img src="data:image/png;base64,{logo_b64}" style="max-height:80px;" /></div>', unsafe_allow_html=True)
        
        st.header("🏪 Unidade")
        filial_selecionada = st.sidebar.selectbox("🏪 Unidade", options=filiais)

    st.caption(f"Filial: **{filial_selecionada}** | Logado como: {st.session_state.user.email}")

    with st.expander("➕ Novo Lançamento", expanded=True):
        with st.form("add_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            cod = col1.text_input("Código de Barras")
            nom = col2.text_input("Nome do Produto")
            mar = st.text_input("Marca")
            col3, col4 = st.columns(2)
            val = col3.date_input("Validade")
            qtd = col4.number_input("Quantidade", min_value=1)
            obs = st.text_area("Observações")
            if st.form_submit_button("Salvar no Sistema"):
                adicionar_produto(filial_selecionada, cod, nom, mar, val, qtd, obs)
                st.rerun()

    df = carregar_estoque_completo()
    df_f = df[df["Filial"] == filial_selecionada]
    
    st.subheader(f"Lista de Produtos - {filial_selecionada}")
    st.dataframe(df_f[ORDEM_EXIBICAO], use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()