import streamlit as st
import pandas as pd
import altair as alt
import requests

st.set_page_config(
    layout="wide",
    page_title="Confiabilidade Rota Preditiva - Raízen",
    page_icon="🛠️"
)

SUPABASE_URL = "https://kplsspnxemhzxfpzxbbl.supabase.co"
SUPABASE_KEY = "sb_publishable_M-_WauseWVAmnb1SIzOmQg_VLcc-O2e"


@st.cache_data(ttl=60)
def carregar_dados():

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    dados = []
    offset = 0
    limit = 1000

    while True:

        url = f"{SUPABASE_URL}/rest/v1/rota_preditiva?select=*&limit={limit}&offset={offset}"
        r = requests.get(url, headers=headers)
        lote = r.json()

        if not lote:
            break

        dados.extend(lote)
        offset += limit

    df = pd.DataFrame(dados)

    if not df.empty:
        df.columns = df.columns.str.upper()
        df = df.rename(columns={"DESCRICAO_LI": "DESCRIÇÃO_LI"})
        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")

    return df


def enviar_para_supabase(df):

    df.columns = df.columns.str.upper().str.strip()

    df_insert = df.rename(columns={
        'DATA':'data','OM':'om','LI':'li','DESCRIÇÃO_LI':'descricao_li',
        'SETOR':'setor','OFICINA':'oficina','CRITICIDADE':'criticidade',
        'TEXTO_BREVE':'texto_breve','CAUSA':'causa',
        'STATUS_PREDITIVA':'status_preditiva','DEFEITO':'defeito'
    })

    colunas = [
        "data","om","li","descricao_li","setor",
        "oficina","criticidade","texto_breve",
        "causa","status_preditiva","defeito"
    ]

    df_insert = df_insert[colunas]

    df_insert["data"] = pd.to_datetime(
        df_insert["data"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    df_insert = df_insert.astype(object)
    df_insert = df_insert.where(pd.notnull(df_insert), None)

    registros = df_insert.to_dict("records")

    url = f"{SUPABASE_URL}/rest/v1/rota_preditiva?on_conflict=om,oficina"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    r = requests.post(url, json=registros, headers=headers)

    return r.status_code


# HEADER
c1, c2 = st.columns([8,1])
c1.markdown("<h2>Raízen Bioparque Gasa</h2>", unsafe_allow_html=True)
c2.image("logo_gasa.png", width=120)

st.markdown("---")
st.title("⚙️ Relatório Confiabilidade - Rotas Preditivas")


with st.expander("📥 Upload nova carga (.xlsx)"):

    arquivo = st.file_uploader("Enviar planilha", type=["xlsx"])

    if arquivo is not None:

        df_upload = pd.read_excel(arquivo, sheet_name="STATUS")

        st.info(f"{len(df_upload)} registros prontos")

        if st.button("🚀 Enviar carga para banco"):

            status = enviar_para_supabase(df_upload)

            if status in [200,201]:
                st.success("Carga enviada! Atualize a página.")
                st.cache_data.clear()


df_base = carregar_dados()

if df_base.empty:
    st.stop()

df = df_base.copy()

# FILTROS TOPO
c1, c2, c3 = st.columns(3)

setor = c1.multiselect("Setor", sorted(df_base['SETOR'].dropna().unique()))
oficina = c2.multiselect("Oficina", sorted(df_base['OFICINA'].dropna().unique()))

periodo = c3.date_input(
    "Período",
    [df_base['DATA'].min(), df_base['DATA'].max()]
)

if setor:
    df = df[df['SETOR'].isin(setor)]

if oficina:
    df = df[df['OFICINA'].isin(oficina)]

if len(periodo) == 2:
    df = df[
        (df['DATA'] >= pd.to_datetime(periodo[0])) &
        (df['DATA'] <= pd.to_datetime(periodo[1]))
    ]

# SIDEBAR
st.sidebar.header("Filtros Engenharia")

critic = st.sidebar.multiselect(
    "Criticidade",
    sorted(df_base['CRITICIDADE'].dropna().unique())
)

status_pred = st.sidebar.multiselect(
    "Status Preditiva",
    sorted(df_base['STATUS_PREDITIVA'].dropna().unique())
)

causa = st.sidebar.multiselect(
    "Causa",
    sorted(df_base['CAUSA'].dropna().unique())
)

defeito = st.sidebar.multiselect(
    "Defeito",
    sorted(df_base['DEFEITO'].dropna().unique())
)

if critic:
    df = df[df['CRITICIDADE'].isin(critic)]

if status_pred:
    df = df[df['STATUS_PREDITIVA'].isin(status_pred)]

if causa:
    df = df[df['CAUSA'].isin(causa)]

if defeito:
    df = df[df['DEFEITO'].isin(defeito)]


# ===== KPI CORRIGIDO =====

df_kpi = df.copy()

total = len(df_kpi)

executada = df_kpi[
    df_kpi['STATUS_PREDITIVA'] == 'Manutenção Executada'
].shape[0]

pendente = df_kpi[
    df_kpi['STATUS_PREDITIVA'] == 'Pendente'
].shape[0]

nao_conf = df_kpi[
    df_kpi['STATUS_PREDITIVA'] == 'Não Conforme'
].shape[0]

k1, k2, k3, k4 = st.columns(4)

k1.metric("Total de Anomalias", total)
k2.metric("Manutenção Executada", executada)
k3.metric("Pendentes", pendente)
k4.metric("Não Conforme", nao_conf)

st.divider()


def grafico_barra(data, coluna, cor, titulo):

    if data.empty:
        st.info("Sem dados para os filtros selecionados")
        return

    base = data[coluna].value_counts().reset_index()
    base.columns = [coluna,'QTD']

    chart = alt.Chart(base).mark_bar(color=cor).encode(
        x=alt.X(f"{coluna}:N", sort='-y', axis=alt.Axis(labelAngle=-45)),
        y='QTD:Q',
        tooltip=['QTD']
    )

    st.subheader(titulo)
    st.altair_chart(chart, use_container_width=True)


g1, g2 = st.columns(2)

with g1:
    grafico_barra(df,'SETOR','#5E7F73','Ranking por Setor')

with g2:
    grafico_barra(df,'OFICINA','#8FAF9F','Ranking por Oficina')

st.divider()

g3, g4 = st.columns(2)

with g3:
    grafico_barra(df,'STATUS_PREDITIVA','#3E5F55','Status Preditiva')

with g4:
    grafico_barra(df,'CAUSA','#5E7F73','Ocorrências por Causa')

st.divider()


# ===== BACKLOG CORRIGIDO =====

backlog = df_kpi[
    df_kpi['STATUS_PREDITIVA'].isin(
        ['Pendente','Não Conforme']
    )
]

grafico_barra(
    backlog,
    'OFICINA',
    '#3E5F55',
    'Backlog por Oficina'
)

st.divider()

st.subheader("Tabela de Anomalias")

df['DATA'] = df['DATA'].dt.strftime("%d/%m/%Y")

st.dataframe(df, use_container_width=True)