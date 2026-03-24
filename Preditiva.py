import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO

st.set_page_config(
    layout="wide",
    page_title="Confiabilidade Rota Preditiva - Raízen",
    page_icon="🛠️"
)

# =============================
# HEADER CORPORATIVO
# =============================

c1, c2 = st.columns([8,1])

with c1:
    st.markdown(
        "<h2 style='margin-bottom:0px'>Raízen Bioparque Gasa</h2>",
        unsafe_allow_html=True
    )

with c2:
    st.image("logo_gasa.png", width=120)

st.markdown("---")

st.title("⚙️ Relatório Confiabilidade - Rotas Preditivas")

# =============================
# UPLOAD
# =============================

with st.expander("📥 Upload da planilha (.xlsx)"):
    arquivo = st.file_uploader("Selecione o arquivo", type=["xlsx"])

if arquivo:

    df = pd.read_excel(arquivo, sheet_name="STATUS")

    df.columns = df.columns.str.upper().str.strip()

    texto_cols = ['SETOR','OFICINA','CRITICIDADE','STATUS_PREDITIVA','CAUSA']

    for c in texto_cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.upper().str.strip()

    df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')

    # =============================
    # SIDEBAR
    # =============================

    st.sidebar.header("Filtros Engenharia")

    critic = st.sidebar.multiselect("Criticidade", sorted(df['CRITICIDADE'].dropna().unique()))
    status_pred = st.sidebar.multiselect("Status Preditiva", sorted(df['STATUS_PREDITIVA'].dropna().unique()))
    causa = st.sidebar.multiselect("Causa", sorted(df['CAUSA'].dropna().unique()))

    if critic:
        df = df[df['CRITICIDADE'].isin(critic)]

    if status_pred:
        df = df[df['STATUS_PREDITIVA'].isin(status_pred)]

    if causa:
        df = df[df['CAUSA'].isin(causa)]

    # =============================
    # FILTROS TOPO
    # =============================

    c1, c2, c3 = st.columns(3)

    setor = c1.multiselect("Setor", sorted(df['SETOR'].dropna().unique()))
    oficina = c2.multiselect("Oficina", sorted(df['OFICINA'].dropna().unique()))

    periodo = c3.date_input("Período", [df['DATA'].min(), df['DATA'].max()])

    if setor:
        df = df[df['SETOR'].isin(setor)]

    if oficina:
        df = df[df['OFICINA'].isin(oficina)]

    if len(periodo) == 2:
        df = df[
            (df['DATA'] >= pd.to_datetime(periodo[0])) &
            (df['DATA'] <= pd.to_datetime(periodo[1]))
        ]

    # =============================
    # FUNÇÃO GRÁFICO
    # =============================

    def grafico_barra(data, coluna, cor, titulo):

        base = data[coluna].value_counts().reset_index()
        base.columns = [coluna, 'QTD']

        bars = alt.Chart(base).mark_bar(color=cor).encode(
            x=alt.X(f"{coluna}:N", sort='-y', axis=alt.Axis(labelAngle=-45)),
            y='QTD:Q'
        )

        text = bars.mark_text(dy=-5).encode(text='QTD')

        chart = bars + text

        if titulo:
            st.subheader(titulo)

        st.altair_chart(chart, use_container_width=True)

    # =============================
    # KPIs
    # =============================

    total = len(df)
    setores = df['SETOR'].nunique()

    executada = (df['STATUS_PREDITIVA'] == 'MANUTENÇÃO EXECUTADA').sum()
    pendente = (df['STATUS_PREDITIVA'] == 'PENDENTE').sum()
    nao_conf = (df['STATUS_PREDITIVA'] == 'NÃO CONFORME').sum()

    k1, k2, k3, k4, k5 = st.columns(5)

    k1.metric("Total", total)
    k2.metric("Setores", setores)
    k3.metric("Executada", executada)
    k4.metric("Pendente", pendente)
    k5.metric("Não Conforme", nao_conf)

    st.divider()

    # =============================
    # GRÁFICOS
    # =============================

    g1, g2 = st.columns(2)

    with g1:
        grafico_barra(df, 'SETOR', '#5E7F73', 'Ranking por Setor')

    with g2:
        grafico_barra(df, 'OFICINA', '#8FAF9F', 'Ranking por Oficina')

    st.divider()

    g3, g4 = st.columns(2)

    with g3:
        grafico_barra(df, 'STATUS_PREDITIVA', '#3E5F55', 'Status Preditiva')

    with g4:
        grafico_barra(df, 'CAUSA', '#5E7F73', 'Ocorrências por Causa')

    st.divider()

    # =============================
    # BACKLOG
    # =============================

    st.subheader("📦 Backlog por Oficina")

    backlog = df[df['STATUS_PREDITIVA'].isin(['PENDENTE','NÃO CONFORME'])]

    grafico_barra(backlog, 'OFICINA', '#3E5F55', '')

    st.divider()

    # =============================
    # FORMATA DATA
    # =============================

    df['DATA'] = df['DATA'].dt.strftime('%d/%m/%Y')

    # =============================
    # TABELA + BOTÃO DOWNLOAD
    # =============================

    c1, c2 = st.columns([6,2])

    c1.subheader("Tabela de Anomalias")

    output = BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    c2.download_button(
        label="⬇️ Baixar Base Filtrada",
        data=output,
        file_name="rota_filtrada.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    colunas_tabela = [
        'DATA','OM','LI','DESCRIÇÃO_LI','SETOR','OFICINA',
        'CRITICIDADE','TEXTO_BREVE','CAUSA','STATUS_PREDITIVA'
    ]

    colunas_existentes = [c for c in colunas_tabela if c in df.columns]

    st.dataframe(df[colunas_existentes], use_container_width=True)