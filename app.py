import pandas as pd
import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# --- 1. CONFIGURAÇÃO E CONEXÃO SEGURA ---
st.set_page_config(page_title="Way Suplementos", layout="wide")

# Tenta conectar. Se falhar, avisa o usuário e para o código.
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Erro crítico: Não foi possível conectar ao banco de dados.")
    st.warning("Verifique se criou o arquivo '.streamlit/secrets.toml' com as chaves corretas.")
    st.stop() # Para a execução aqui para evitar o erro "supabase not defined"

COLUNAS_TABELA = ["Código de Barras", "Nome", "Marca", "Validade", "Quantidade", "Observações"]

# --- 2. FUNÇÕES ---

def carregar_estoque_seguro(unidade):
    try:
        # Busca produtos e nome da filial
        res = supabase.table("produtos").select("*, filiais(nome)").execute()
        
        # Se não tiver dados, retorna tabela vazia estruturada
        if not res.data:
            return pd.DataFrame(columns=["Filial"] + COLUNAS_TABELA)
        
        dados = []
        for p in res.data:
            # Formata data
            dt_show = p["validade"]
            try:
                dt_show = datetime.strptime(p["validade"], "%Y-%m-%d").strftime("%d/%m/%Y")
            except: pass

            dados.append({
                "Filial": p["filiais"]["nome"] if p.get("filiais") else "N/A",
                "Código de Barras": p["codigo_barras"],
                "Nome": p["nome"],
                "Marca": p["marca"],
                "Validade": dt_show,
                "Quantidade": p["quantidade"],
                "Observações": p.get("observacoes", "")
            })
        return pd.DataFrame(dados)
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame(columns=["Filial"] + COLUNAS_TABELA)

def salvar_produto(unidade, cod, nome, marca, val, qtd, obs):
    try:
        # Pega ID da filial
        res_f = supabase.table("filiais").select("id").eq("nome", unidade).execute()
        f_id = res_f.data[0]['id']
        
        dados = {
            "filial_id": f_id,
            "codigo_barras": cod,
            "nome": nome,
            "marca": marca,
            "validade": str(val),
            "quantidade": qtd,
            "observacoes": obs
        }
        supabase.table("produtos").insert(dados).execute()
        st.success("✅ Produto salvo!")
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

# --- 3. INTERFACE ---
def main():
    st.title("📦 CONTROLE DE ESTOQUE")

    # Carrega filiais
    try:
        res_f = supabase.table("filiais").select("nome").execute()
        lista_filiais = [f['nome'] for f in res_f.data] if res_f.data else ["Principal"]
    except:
        lista_filiais = ["Principal"]

    with st.sidebar:
        st.header("Configurações")
        unidade = st.selectbox("Unidade Atual", options=lista_filiais)

    # Formulário
    with st.expander("➕ Novo Lançamento", expanded=True):
        with st.form("main_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            cod = c1.text_input("Código de Barras")
            nome = c2.text_input("Nome do Produto")
            marca = st.text_input("Marca")
            
            c3, c4 = st.columns(2)
            val = c3.date_input("Validade", format="DD/MM/YYYY")
            qtd = c4.number_input("Quantidade", min_value=1)
            obs = st.text_area("Observações")
            
            if st.form_submit_button("Salvar no Sistema"):
                if salvar_produto(unidade, cod, nome, marca, val, qtd, obs):
                    st.rerun()

    # Tabela
    st.divider()
    st.subheader(f"Estoque: {unidade}")
    
    df = carregar_estoque_seguro(unidade)
    
    # Filtro seguro (Evita KeyError)
    if not df.empty and "Filial" in df.columns:
        df_filtrado = df[df["Filial"] == unidade]
        st.dataframe(df_filtrado[COLUNAS_TABELA], use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum produto encontrado.")

if __name__ == "__main__":
    main()