import base64
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# --- 1. CONEXÃO COM O SUPABASE ---
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(URL, KEY)

# --- 2. CONFIGURAÇÕES VISUAIS ---
DIR_BASE = Path(__file__).resolve().parent
CAMINHO_LOGO = DIR_BASE / "assets" / "logo-way.png"
CAMINHO_FUNDO = DIR_BASE / "assets" / "way-fundo.png" 
COR_MARCA = "#E31837"

# Nomes exatos que usaremos no DataFrame para evitar KeyError
COLUNAS_DF = ["Filial", "Código de Barras", "Nome", "Marca", "Validade", "Quantidade"]
FILIAL_PADRAO = "Principal"

# --- 3. FUNÇÕES DE DADOS ---

def carregar_filiais():
    try:
        res = supabase.table("filiais").select("nome").execute()
        return [item['nome'] for item in res.data] if res.data else [FILIAL_PADRAO]
    except:
        return [FILIAL_PADRAO]

def adicionar_produto(filial, codigo, nome, marca, validade, quantidade, obs):
    try:
        # Busca o ID da filial selecionada
        res_f = supabase.table("filiais").select("id").eq("nome", filial).execute()
        if not res_f.data:
            st.error("Unidade não encontrada!")
            return
        
        f_id = res_f.data[0]["id"]
        
        # Dados para o banco
        dados = {
            "filial_id": f_id,
            "codigo_barras": str(codigo),
            "nome": str(nome),
            "marca": str(marca),
            "validade": str(validade),
            "quantidade": int(quantidade),
            "observacoes": str(obs)
        }
        
        # SALVAMENTO
        supabase.table("produtos").insert(dados).execute()
        st.success("✅ Produto salvo com sucesso!")
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")

def carregar_estoque():
    try:
        # Faz o join com a tabela de filiais para pegar o nome
        res = supabase.table("produtos").select("*, filiais(nome)").execute()
        if not res.data:
            return pd.DataFrame(columns=COLUNAS_DF)
        
        lista_final = []
        for p in res.data:
            # Formatação de data BR
            dt_exibicao = p["validade"]
            try:
                dt_exibicao = datetime.strptime(p["validade"], "%Y-%m-%d").strftime("%d/%m/%Y")
            except: pass

            lista_final.append({
                "Filial": p["filiais"]["nome"] if p.get("filiais") else "N/A",
                "Código de Barras": p["codigo_barras"],
                "Nome": p["nome"],
                "Marca": p["marca"],
                "Validade": dt_exibicao,
                "Quantidade": p["quantidade"]
            })
        return pd.DataFrame(lista_final)
    except:
        return pd.DataFrame(columns=COLUNAS_DF)

# --- 4. INTERFACE ---

def _obter_base64(caminho):
    if caminho.exists():
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

def main():
    st.set_page_config(page_title="Way Suplementos", layout="wide")
    
    # CSS Customizado (Fundo e Botões)
    fundo_b64 = _obter_base64(CAMINHO_FUNDO)
    if fundo_b64:
        st.markdown(f"""
        <style>
        [data-testid="stAppViewContainer"] {{
            background-image: url("data:image/png;base64,{fundo_b64}");
            background-size: cover; background-attachment: fixed;
        }}
        [data-testid="stAppViewContainer"]::before {{
            content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background-color: rgba(14, 17, 23, 0.85); z-index: -1;
        }}
        .stButton > button {{ background-color: {COR_MARCA} !important; color: white !important; }}
        </style>
        """, unsafe_allow_html=True)

    # Sidebar
    filiais = carregar_filiais()
    with st.sidebar:
        st.header("🏪 Unidade")
        unidade_atual = st.selectbox("Escolher Filial", options=filiais)

    # Título e Formulário
    st.title("📦 CONTROLE DE ESTOQUE")
    with st.expander("➕ Novo Lançamento", expanded=True):
        with st.form("form_novo_prod", clear_on_submit=True):
            c1, c2 = st.columns(2)
            cod = c1.text_input("Código de Barras")
            nome = c2.text_input("Nome do Produto")
            marca = st.text_input("Marca")
            
            c3, c4 = st.columns(2)
            val = c3.date_input("Validade", format="DD/MM/YYYY")
            qtd = c4.number_input("Quantidade", min_value=1)
            obs = st.text_area("Observações")
            
            if st.form_submit_button("Salvar no Sistema"):
                adicionar_produto(unidade_atual, cod, nome, marca, val, qtd, obs)

    # Exibição da Tabela
    df = carregar_estoque()
    st.subheader(f"Lista de Produtos - {unidade_atual}")
    
    # Filtragem segura para evitar KeyError
    if not df.empty and "Filial" in df.columns:
        df_filtrado = df[df["Filial"] == unidade_atual]
        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)
    else:
        st.write("Nenhum produto encontrado para esta unidade.")

if __name__ == "__main__":
    main()