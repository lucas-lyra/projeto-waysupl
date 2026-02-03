import base64
import io
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
from supabase import create_client, Client

# --- 1. CONEXÃO COM O SUPABASE ---
# Pegamos as credenciais dos Secrets do Streamlit
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]

# Criamos o cliente global corretamente
supabase: Client = create_client(URL, KEY)

# --- 2. CONFIGURAÇÕES VISUAIS ---
DIR_BASE = Path(__file__).resolve().parent
CAMINHO_LOGO = DIR_BASE / "assets" / "logo-way.png"
CAMINHO_FUNDO = DIR_BASE / "assets" / "way-fundo.png" 
COR_MARCA = "#E31837"

ORDEM_EXIBICAO = ["Código de Barras", "Nome", "Marca", "Validade", "Quantidade"]
FILIAL_PADRAO = "Principal"

# --- 3. FUNÇÕES DE DADOS (COM TRATAMENTO DE ERRO) ---

def carregar_filiais():
    try:
        res = supabase.table("filiais").select("nome").execute()
        return [item['nome'] for item in res.data] if res.data else [FILIAL_PADRAO]
    except Exception:
        return [FILIAL_PADRAO]

def adicionar_filial(nome):
    if nome.strip():
        supabase.table("filiais").insert({"nome": nome.strip()}).execute()
        return True
    return False

def excluir_filial(nome):
    try:
        supabase.table("filiais").delete().eq("nome", nome).execute()
        return True
    except:
        return False

def adicionar_produto(filial, codigo, nome, marca, validade, quantidade, obs):
    # Criamos um feedback visual imediato
    msg = st.empty()
    msg.warning("Enviando dados para o banco...")
    
    try:
        # Busca o ID da filial
        res_f = supabase.table("filiais").select("id").eq("nome", filial).execute()
        if not res_f.data:
            msg.error("Erro: Unidade não encontrada!")
            return

        f_id = res_f.data[0]["id"]
        
        # Insere o produto
        dados = {
            "filial_id": f_id,
            "codigo_barras": str(codigo),
            "nome": str(nome),
            "marca": str(marca),
            "validade": str(validade),
            "quantidade": int(quantidade),
            "observacoes": str(obs)
        }
        
        supabase.table("produtos").insert(dados).execute()
        msg.success("✅ PRODUTO SALVO COM SUCESSO!")
        import time
        time.sleep(1) # Pausa para o usuário ver o sucesso
        st.rerun()
    except Exception as e:
        msg.error(f"Erro ao salvar: {str(e)}")

def carregar_estoque():
    res = supabase.table("produtos").select("*, filiais(nome)").execute()
    if not res.data:
        return pd.DataFrame(columns=ORDEM_EXIBICAO)
    
    dados = []
    for p in res.data:
        # Converte data para formato BR
        dt_br = p["validade"]
        try:
            dt_br = datetime.strptime(p["validade"], "%Y-%m-%d").strftime("%d/%m/%Y")
        except: pass

        dados.append({
            "Filial": p["filiais"]["nome"] if p.get("filiais") else "N/A",
            "Código de Barras": p["codigo_barras"],
            "Nome": p["nome"],
            "Marca": p["marca"],
            "Validade": dt_br,
            "Quantidade": p["quantidade"]
        })
    return pd.DataFrame(dados)

# --- 4. CSS E INTERFACE ---

def _obter_base64(caminho):
    if caminho.exists():
        with open(caminho, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return None

def main():
    st.set_page_config(page_title="Way Suplementos", layout="wide")
    
    # Injeta Fundo
    fundo_b64 = _obter_base64(CAMINHO_FUNDO)
    if fundo_b64:
        st.markdown(f"""<style>[data-testid="stAppViewContainer"] {{ background-image: url("data:image/png;base64,{fundo_b64}"); background-size: cover; background-attachment: fixed; }} [data-testid="stAppViewContainer"]::before {{ content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(14, 17, 23, 0.85); z-index: -1; }} .stButton > button {{ background-color: {COR_MARCA} !important; color: white !important; }}</style>""", unsafe_allow_html=True)

    # Sidebar
    filiais = carregar_filiais()
    with st.sidebar:
        st.header("🏪 Unidades")
        unidade = st.selectbox("Escolher Filial", options=filiais)
        
        with st.expander("⚙️ Gerenciar Unidades"):
            nova_u = st.text_input("Nome da Unidade")
            if st.button("Adicionar"):
                if adicionar_filial(nova_u): st.rerun()
            u_del = st.selectbox("Excluir Unidade", options=filiais)
            if st.button("Remover"):
                if excluir_filial(u_del): st.rerun()

    # Formulário
    st.title("📦 CONTROLE DE ESTOQUE")
    with st.expander("➕ Novo Lançamento", expanded=True):
        with st.form("form_prod", clear_on_submit=True):
            col1, col2 = st.columns(2)
            c_bar = col1.text_input("Código de Barras")
            nome = col2.text_input("Nome do Produto")
            marca = st.text_input("Marca")
            
            col3, col4 = st.columns(2)
            val = col3.date_input("Validade", format="DD/MM/YYYY")
            qtd = col4.number_input("Quantidade", min_value=1)
            obs = st.text_area("Observações")
            
            if st.form_submit_button("Salvar no Sistema"):
                adicionar_produto(unidade, c_bar, nome, marca, val, qtd, obs)

    # Tabela
    df = carregar_estoque()
    st.subheader(f"Lista de Produtos - {unidade}")
    st.dataframe(df[df["Filial"] == unidade][ORDEM_EXIBICAO], use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()