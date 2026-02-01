"""
Gerenciador de Estoque - Way Suplementos
Gerenciamento de estoque multi-filial com interface web usando Streamlit e Pandas.
"""

import base64
import io
import os
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

# Caminho da logo (coloque a imagem em assets/logo-way.png)
DIR_BASE = Path(__file__).resolve().parent
CAMINHO_LOGO = DIR_BASE / "assets" / "logo-way.png"
COR_MARCA = "#E31837"

ARQUIVO_DADOS = "estoque.xlsx"
ABA_ESTOQUE = "Estoque"
ABA_FILIAIS = "Filiais"
ORDEM_COLUNAS = [
    "Filial",
    "Código de Barras",
    "Nome",
    "Marca",
    "Validade",
    "Quantidade",
    "Observações",
]
ORDEM_EXIBICAO = [
    "Código de Barras",
    "Nome",
    "Marca",
    "Validade",
    "Quantidade",
]
FILIAL_PADRAO = "Principal"


def carregar_filiais() -> list[str]:
    """Carrega a lista de filiais do Excel."""
    if not os.path.exists(ARQUIVO_DADOS):
        return [FILIAL_PADRAO]

    try:
        df = pd.read_excel(ARQUIVO_DADOS, sheet_name=ABA_FILIAIS)
        if df.empty or "Filial" not in df.columns:
            return [FILIAL_PADRAO]
        return df["Filial"].astype(str).str.strip().dropna().unique().tolist()
    except Exception:
        return [FILIAL_PADRAO]


def salvar_filiais(filiais: list[str]) -> None:
    """Salva a lista de filiais no Excel (preservando a aba de estoque)."""
    df_filiais = pd.DataFrame({"Filial": filiais})
    df_estoque = carregar_estoque_completo()

    with pd.ExcelWriter(ARQUIVO_DADOS, engine="openpyxl") as writer:
        df_estoque.to_excel(writer, sheet_name=ABA_ESTOQUE, index=False)
        df_filiais.to_excel(writer, sheet_name=ABA_FILIAIS, index=False)


def _arquivo_formato_antigo() -> bool:
    """Verifica se o arquivo está no formato antigo (single-sheet, sem aba Filiais)."""
    if not os.path.exists(ARQUIVO_DADOS):
        return False
    try:
        pd.read_excel(ARQUIVO_DADOS, sheet_name=ABA_FILIAIS)
        return False
    except Exception:
        return True


def _garantir_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """Garante que o DataFrame tenha todas as colunas na ordem correta."""
    if "Nome" not in df.columns:
        if "Nome do Produto" in df.columns:
            df["Nome"] = df["Nome do Produto"]
        elif "Produto" in df.columns:
            df["Nome"] = df["Produto"]
        else:
            df["Nome"] = ""
    for col in ("Produto", "Nome do Produto", "Tipo"):
        if col in df.columns:
            df = df.drop(columns=[col], errors="ignore")
    for col in ORDEM_COLUNAS:
        if col not in df.columns:
            df[col] = FILIAL_PADRAO if col == "Filial" else ""
    return df.reindex(columns=ORDEM_COLUNAS, fill_value="")


def carregar_estoque_completo() -> pd.DataFrame:
    """Carrega todo o estoque do Excel (todas as filiais)."""
    if not os.path.exists(ARQUIVO_DADOS):
        return pd.DataFrame(columns=ORDEM_COLUNAS)

    try:
        df = pd.read_excel(ARQUIVO_DADOS, sheet_name=ABA_ESTOQUE)
    except Exception:
        df = pd.read_excel(ARQUIVO_DADOS)

    df = _garantir_colunas(df)

    if _arquivo_formato_antigo():
        salvar_estoque(df)

    return df


def salvar_estoque(df: pd.DataFrame) -> None:
    """Salva o estoque no Excel (preservando a aba de filiais)."""
    df_filiais = pd.DataFrame({"Filial": carregar_filiais()})
    df_ordenado = df.reindex(columns=ORDEM_COLUNAS, fill_value="")
    with pd.ExcelWriter(ARQUIVO_DADOS, engine="openpyxl") as writer:
        df_ordenado.to_excel(writer, sheet_name=ABA_ESTOQUE, index=False)
        df_filiais.to_excel(writer, sheet_name=ABA_FILIAIS, index=False)


def inicializar_sessao():
    """Garante que dados estejam no st.session_state."""
    if "df_estoque" not in st.session_state:
        st.session_state.df_estoque = carregar_estoque_completo()
    if "filial_selecionada" not in st.session_state:
        filiais = carregar_filiais()
        st.session_state.filial_selecionada = filiais[0] if filiais else FILIAL_PADRAO


def adicionar_filial(nome: str) -> bool:
    """Adiciona uma nova filial. Retorna True se sucesso."""
    nome = nome.strip()
    if not nome:
        return False
    filiais = carregar_filiais()
    if nome in filiais:
        return False
    filiais.append(nome)
    salvar_filiais(filiais)
    return True


def excluir_filial(nome: str) -> None:
    """Exclui uma filial e todos os produtos vinculados a ela."""
    df = carregar_estoque_completo()
    df = df[df["Filial"] != nome].reset_index(drop=True)
    filiais = [f for f in carregar_filiais() if f != nome]
    if not filiais:
        filiais = [FILIAL_PADRAO]
    df_filiais = pd.DataFrame({"Filial": filiais})
    with pd.ExcelWriter(ARQUIVO_DADOS, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=ABA_ESTOQUE, index=False)
        df_filiais.to_excel(writer, sheet_name=ABA_FILIAIS, index=False)
    st.session_state.df_estoque = df
    if st.session_state.filial_selecionada == nome:
        st.session_state.filial_selecionada = filiais[0]


def adicionar_produto(
    filial: str,
    codigo_barras: str,
    nome: str,
    marca: str,
    validade,
    quantidade: int,
    observacoes: str,
) -> None:
    """Adiciona um novo produto ao estoque da filial."""
    novo = pd.DataFrame([{
        "Filial": filial,
        "Código de Barras": codigo_barras.strip(),
        "Nome": nome.strip(),
        "Marca": marca.strip(),
        "Validade": validade,
        "Quantidade": int(quantidade),
        "Observações": observacoes.strip() or "",
    }])
    st.session_state.df_estoque = pd.concat(
        [st.session_state.df_estoque, novo], ignore_index=True
    )
    salvar_estoque(st.session_state.df_estoque)


def remover_produtos(indices: list[int]) -> None:
    """Remove produtos pelos índices do DataFrame completo."""
    if not indices:
        return
    st.session_state.df_estoque = st.session_state.df_estoque.drop(indices).reset_index(drop=True)
    salvar_estoque(st.session_state.df_estoque)


def _obter_logo_base64() -> str | None:
    """Retorna a logo em base64 para uso em CSS, ou None se não existir."""
    caminhos = [CAMINHO_LOGO]
    assets_dir = DIR_BASE / "assets"
    if assets_dir.exists():
        caminhos.extend(assets_dir.glob("*.png"))
    for caminho in caminhos:
        if caminho.exists():
            try:
                with open(caminho, "rb") as f:
                    return base64.b64encode(f.read()).decode()
            except Exception:
                pass
    return None


def _injetar_css_way(logo_b64: str | None) -> None:
    """Aplica tema dark, cores da marca e marca d'água."""
    watermark = ""
    if logo_b64:
        watermark = f"""
        .stApp::before {{
            content: "";
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 40%;
            max-width: 400px;
            height: auto;
            min-height: 200px;
            background-image: url("data:image/png;base64,{logo_b64}");
            background-repeat: no-repeat;
            background-position: center;
            background-size: contain;
            opacity: 0.06;
            pointer-events: none;
            z-index: 0;
        }}
        """
    st.markdown(
        f"""
        <style>
        /* Tema escuro Way Suplementos */
        .stApp {{ background-color: #0E1117; }}
        .stMarkdown, .stMarkdown p, .stMetric label {{ color: #FAFAFA !important; }}
        .stMetric [data-testid="stMetricValue"] {{ color: #FAFAFA !important; }}
        
        /* Botões vermelhos - Adicionar, Exportar, Importar */
        .stButton > button,
        .stFormSubmitButton > button,
        button[kind="primary"] {{
            background-color: {COR_MARCA} !important;
            color: white !important;
            border: none !important;
            font-weight: 600 !important;
        }}
        .stButton > button:hover,
        .stFormSubmitButton > button:hover {{
            background-color: #c41430 !important;
            color: white !important;
            border: none !important;
        }}
        .stDownloadButton > button {{
            background-color: {COR_MARCA} !important;
            color: white !important;
            border: none !important;
            font-weight: 600 !important;
        }}
        .stDownloadButton > button:hover {{
            background-color: #c41430 !important;
            color: white !important;
        }}
        .stDownloadButton > button:disabled {{
            background-color: #555 !important;
            color: #999 !important;
        }}
        
        /* Cards de resumo (métricas) com borda vermelha */
        [data-testid="stMetric"] {{
            background-color: #262730;
            padding: 1rem;
            border-radius: 0.5rem;
            border: 1px solid {COR_MARCA};
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        
        /* Expanders e containers */
        .streamlit-expanderHeader {{ color: #FAFAFA !important; }}
        [data-testid="stExpander"] {{ border: 1px solid #333; border-radius: 0.5rem; }}
        
        {watermark}
        </style>
        """,
        unsafe_allow_html=True,
    )


def obter_estoque_filial(df: pd.DataFrame, filial: str) -> pd.DataFrame:
    """Retorna o estoque filtrado por filial, ordenado por validade e quantidade."""
    df_filial = df[df["Filial"] == filial].copy()
    return df_filial.sort_values(by=["Validade", "Quantidade"])


def exportar_planilha(df_filial: pd.DataFrame) -> bytes:
    """Gera arquivo Excel para download com dados da filial (sem coluna Filial)."""
    df_export = df_filial[ORDEM_EXIBICAO].copy() if not df_filial.empty else pd.DataFrame(columns=ORDEM_EXIBICAO)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_export.to_excel(writer, sheet_name="Estoque", index=False)
    return buffer.getvalue()


def importar_planilha(arquivo, filial: str) -> tuple[int, str]:
    """
    Importa produtos de arquivo Excel para a filial.
    Retorna (qtd_importados, mensagem_erro).
    Aceita colunas: Código de Barras, Nome/Nome do Produto, Marca, Validade, Quantidade.
    """
    try:
        df = pd.read_excel(arquivo)
    except Exception as e:
        return 0, f"Erro ao ler arquivo: {e}"
    mapa = {
        "codigo de barras": "Código de Barras",
        "código de barras": "Código de Barras",
        "codigo_barras": "Código de Barras",
        "nome": "Nome",
        "nome do produto": "Nome",
        "marca": "Marca",
        "validade": "Validade",
        "quantidade": "Quantidade",
    }
    encontradas = {}
    for col in df.columns:
        k = str(col).strip().lower()
        if k in mapa:
            encontradas[mapa[k]] = col
        elif str(col).strip() in ("Código de Barras", "Nome", "Marca", "Validade", "Quantidade"):
            encontradas[str(col).strip()] = col
    if "Nome" not in encontradas:
        return 0, "Coluna 'Nome' ou 'Nome do Produto' não encontrada."
    if "Quantidade" not in encontradas:
        return 0, "Coluna 'Quantidade' não encontrada."
    n = len(df)
    df_import = pd.DataFrame()
    df_import["Filial"] = [filial] * n
    df_import["Código de Barras"] = df[encontradas["Código de Barras"]].fillna("").astype(str) if "Código de Barras" in encontradas else [""] * n
    df_import["Nome"] = df[encontradas["Nome"]].fillna("").astype(str)
    df_import["Marca"] = df[encontradas["Marca"]].fillna("").astype(str) if "Marca" in encontradas else [""] * n
    if "Validade" in encontradas:
        df_import["Validade"] = pd.to_datetime(df[encontradas["Validade"]], errors="coerce")
    else:
        df_import["Validade"] = pd.NaT
    df_import["Quantidade"] = pd.to_numeric(df[encontradas["Quantidade"]], errors="coerce").fillna(0).astype(int)
    df_import["Observações"] = ""
    df_import = df_import[(df_import["Nome"].str.strip() != "") & (df_import["Quantidade"] > 0)]
    if df_import.empty:
        return 0, "Nenhum registro válido encontrado no arquivo."
    qtd = len(df_import)
    st.session_state.df_estoque = pd.concat(
        [st.session_state.df_estoque, df_import], ignore_index=True
    )
    salvar_estoque(st.session_state.df_estoque)
    return qtd, ""


def main():
    st.set_page_config(
        page_title="Estoque Way Suplementos",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    _injetar_css_way(_obter_logo_base64())

    st.title("📦 ESTOQUE WAY SUPLEMENTOS")

    inicializar_sessao()
    st.session_state.df_estoque = carregar_estoque_completo()
    filiais = carregar_filiais()

    # Sidebar - logo e filial
    with st.sidebar:
        logo_b64 = _obter_logo_base64()
        if logo_b64:
            st.markdown(
                f'<div style="text-align:center; margin-bottom:1.5rem;">'
                f'<img src="data:image/png;base64,{logo_b64}" '
                f'style="max-width:100%; height:auto; max-height:80px;" /></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<p style="text-align:center; color:#E31837; font-weight:bold; '
                'font-size:1.2rem; margin-bottom:1.5rem;">WAY SUPLEMENTOS</p>',
                unsafe_allow_html=True,
            )
        st.header("🏪 Filial")
        filial_selecionada = st.selectbox(
            "Selecionar filial",
            options=filiais,
            key="select_filial",
            index=filiais.index(st.session_state.filial_selecionada)
            if st.session_state.filial_selecionada in filiais
            else 0,
        )
        st.session_state.filial_selecionada = filial_selecionada

        with st.expander("⚙️ Gerenciar Filiais"):
            with st.form("form_filial", clear_on_submit=True):
                nova_filial = st.text_input(
                    "Cadastrar nova filial", placeholder="Ex: Loja Centro"
                )
                if st.form_submit_button("Cadastrar"):
                    if nova_filial and nova_filial.strip():
                        if adicionar_filial(nova_filial):
                            st.success("Filial cadastrada!")
                            st.rerun()
                        else:
                            st.error("Filial já existe.")
                    else:
                        st.error("Informe o nome da filial.")

            st.caption("Excluir filial")
            with st.form("form_excluir_filial"):
                filial_excluir = st.selectbox(
                    "Selecionar filial para excluir",
                    options=filiais,
                    key="select_excluir",
                )
                if st.form_submit_button("Excluir Filial"):
                    if len(filiais) <= 1:
                        st.error("Não é possível excluir a única filial.")
                    else:
                        excluir_filial(filial_excluir)
                        st.warning("Filial e produtos excluídos.")
                        st.rerun()

    # Página principal - Adicionar Produto e botões Exportar/Importar
    st.caption(f"Filial: **{filial_selecionada}**")

    with st.expander("➕ Adicionar Produto", expanded=True):
        with st.form("form_adicionar", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                codigo_barras = st.text_input(
                    "Código de Barras", placeholder="Ex: 7891234567890"
                )
            with col2:
                nome_produto = st.text_input(
                    "Nome", placeholder="Ex: Whey Protein"
                )
            col3, col4 = st.columns(2)
            with col3:
                marca = st.text_input("Marca", placeholder="Ex: Growth, Max Titanium")
            with col4:
                validade = st.date_input("Validade", format="DD/MM/YYYY")
            col_qtd, col_obs = st.columns([1, 2])
            with col_qtd:
                quantidade = st.number_input("Quantidade", min_value=1, value=1, step=1)
            with col_obs:
                observacoes = st.text_input("Observações (opcional)")

            if st.form_submit_button("Adicionar"):
                if nome_produto and nome_produto.strip():
                    adicionar_produto(
                        filial_selecionada,
                        codigo_barras,
                        nome_produto,
                        marca,
                        validade,
                        quantidade,
                        observacoes,
                    )
                    st.success("Produto adicionado!")
                    st.rerun()
                else:
                    st.error("Informe o nome do produto.")

    # Botões Exportar / Importar
    df_filial_export = obter_estoque_filial(
        st.session_state.df_estoque, filial_selecionada
    )
    col_exp, col_imp, _ = st.columns([1, 1, 3])
    with col_exp:
        buf = exportar_planilha(df_filial_export)
        st.download_button(
            label="📥 Baixar Planilha (Exportar)",
            data=buf,
            file_name=f"estoque_{filial_selecionada.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_btn",
            disabled=df_filial_export.empty,
        )
    with col_imp:
        arquivo = st.file_uploader(
            "📤 Subir Planilha (Importar)",
            type=["xlsx", "xls"],
            key="upload_import",
        )
        if arquivo is not None and st.button("Importar", key="btn_importar"):
            qtd, erro = importar_planilha(arquivo, filial_selecionada)
            if erro:
                st.error(erro)
            else:
                st.success(f"{qtd} produto(s) importado(s).")
                st.rerun()

    st.divider()

    # Dados filtrados pela filial selecionada
    df = st.session_state.df_estoque.copy()
    df_filial = obter_estoque_filial(df, filial_selecionada)

    # Tabs principais
    tab1, tab2, tab3 = st.tabs([
        "📋 Estoque Completo",
        "🔍 Buscar",
        "⚠️ Produtos Próximos do Vencimento",
    ])

    with tab1:
        st.subheader(f"Estoque - {filial_selecionada}")
        if df_filial.empty:
            st.info("O estoque desta filial está vazio. Adicione produtos acima.")
        else:
            df_tabela = df_filial[ORDEM_EXIBICAO].copy()
            st.dataframe(
                df_tabela,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Validade": st.column_config.DateColumn(
                        "Validade", format="DD/MM/YYYY"
                    ),
                    "Quantidade": st.column_config.NumberColumn(
                        "Quantidade", min_value=0, step=1
                    ),
                },
            )

            st.divider()
            st.subheader("Remover Produtos")
            with st.form("form_remover"):
                def _rotulo(idx):
                    row = df_filial.loc[idx]
                    return f"{row['Código de Barras'] or '(sem código)'} - {row['Nome']}"

                indices_remover = st.multiselect(
                    "Selecione os produtos a remover",
                    options=df_filial.index.tolist(),
                    format_func=_rotulo,
                )
                if st.form_submit_button("Remover selecionados"):
                    indices = list(indices_remover)
                    remover_produtos(indices)
                    st.success(f"{len(indices)} produto(s) removido(s).")
                    st.rerun()

    with tab2:
        st.subheader(f"Buscar no Estoque - {filial_selecionada}")
        termo = st.text_input(
            "Digite para buscar (código, nome ou marca)",
            placeholder="Ex: Whey, Growth",
            key="busca",
        )
        if termo:
            mask = (
                df_filial["Código de Barras"].astype(str).str.contains(termo, case=False, na=False)
                | df_filial["Nome"].astype(str).str.contains(termo, case=False, na=False)
                | df_filial["Marca"].astype(str).str.contains(termo, case=False, na=False)
            )
            df_busca = df_filial[mask]
            if df_busca.empty:
                st.warning("Nenhum produto encontrado.")
            else:
                st.dataframe(
                    df_busca[ORDEM_EXIBICAO],
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("Digite um termo para buscar.")

    with tab3:
        st.subheader(f"Produtos Próximos do Vencimento - {filial_selecionada}")
        if df_filial.empty:
            st.info("O estoque desta filial está vazio.")
        else:
            df_filial["Validade"] = pd.to_datetime(df_filial["Validade"])
            hoje = pd.Timestamp(datetime.now().date())
            dias_vencimento = 30
            df_proximos = df_filial[
                df_filial["Validade"] <= hoje + pd.Timedelta(days=dias_vencimento)
            ]
            df_proximos = df_proximos.sort_values(by=["Validade", "Quantidade"])

            if df_proximos.empty:
                st.success(
                    f"Nenhum produto vence nos próximos {dias_vencimento} dias."
                )
            else:
                st.warning(
                    f"⚠️ {len(df_proximos)} produto(s) vencendo nos próximos "
                    f"{dias_vencimento} dias:"
                )
                st.dataframe(
                    df_proximos[ORDEM_EXIBICAO],
                    use_container_width=True,
                    hide_index=True,
                )

    # Rodapé - estatísticas (da filial selecionada)
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total de itens", len(df_filial))
    with col2:
        total_qtd = df_filial["Quantidade"].sum() if not df_filial.empty else 0
        st.metric("Quantidade total", int(total_qtd))


if __name__ == "__main__":
    main()
