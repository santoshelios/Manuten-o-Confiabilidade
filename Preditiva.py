import streamlit as st
import pandas as pd
import altair as alt
from io import BytesIO
import requests

st.set_page_config(
    layout="wide",
    page_title="Confiabilidade Rota Preditiva - Raízen",
    page_icon="📡"
)

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# =============================
# LER SUPABASE PAGINADO
# =============================

@st.cache_data
def ler_dados_supabase():

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

        df = df.rename(columns={
            "DESCRICAO_LI": "DESCRIÇÃO_LI"
        })

        df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')

    return df


# =============================
# ENVIO SUPABASE BATCH + MERGE
# =============================

def enviar_para_supabase(df):

    df.columns = df.columns.str.upper().str.strip()

    # GARANTE DEFEITO
    for col in df.columns:
        if "DEFEITO" in col:
            df = df.rename(columns={col:"DEFEITO"})

    df_insert = df.rename(columns={
        'DATA':'data',
        'OM':'om',
        'LI':'li',
        'DESCRIÇÃO_LI':'descricao_li',
        'SETOR':'setor',
        'OFICINA':'oficina',
        'CRITICIDADE':'criticidade',
        'TEXTO_BREVE':'texto_breve',
        'CAUSA':'causa',
        'STATUS_PREDITIVA':'status_preditiva',
        'DEFEITO':'defeito'
    })

    colunas_banco = [
        "data","om","li","descricao_li","setor",
        "oficina","criticidade","texto_breve",
        "causa","status_preditiva","defeito"
    ]

    df_insert = df_insert[colunas_banco]

    df_insert = df_insert.drop_duplicates(
        subset=["om","oficina"]
    )

    df_insert["data"] = pd.to_datetime(
        df_insert["data"],
        errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    df_insert = df_insert.astype(object)
    df_insert = df_insert.where(pd.notnull(df_insert), None)
    st.write(df_insert[['om','oficina','defeito']].head(20))

    registros = df_insert.to_dict(orient="records")

    url = f"{SUPABASE_URL}/rest/v1/rota_preditiva?on_conflict=om,oficina"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    batch_size = 500
    total = len(registros)

    for i in range(0, total, batch_size):

        lote = registros[i:i+batch_size]

        r = requests.post(url, json=lote, headers=headers)

        if r.status_code not in [200,201]:
            st.error(f"Erro lote {i}: {r.text}")
            return r.status_code

    return 201


# =============================
# HEADER
# =============================

c1, c2 = st.columns([8,1])
c1.markdown("<h2>Raízen Bioparque Gasa</h2>", unsafe_allow_html=True)
c2.image("logo_gasa.png", width=120)

st.markdown("---")
st.title("📡 Relatório Confiabilidade - Rotas Preditivas")

# =============================
# CARREGA BANCO
# =============================

df = ler_dados_supabase()

# =============================
# UPLOAD
# =============================

with st.expander("📥 Upload nova carga (.xlsx)"):

    arquivo = st.file_uploader("Enviar planilha", type=["xlsx"])

    if arquivo:

        df_upload = pd.read_excel(arquivo, sheet_name="STATUS")

        st.info(f"{len(df_upload)} registros prontos para envio")

        if st.button("🚀 Enviar carga para o banco"):

            status = enviar_para_supabase(df_upload)

            if status == 201:
                st.success("Carga enviada! Atualize a página.")
            else:
                st.error("Erro ao enviar")

# =============================
# SE VAZIO
# =============================

if df.empty:
    st.warning("Banco sem dados")
    st.stop()

# =============================
# SIDEBAR
# =============================

st.sidebar.header("Filtros Engenharia")

critic = st.sidebar.multiselect(
    "Criticidade",
    sorted(df['CRITICIDADE'].dropna().unique())
)

status_pred = st.sidebar.multiselect(
    "Status Preditiva",
    sorted(df['STATUS_PREDITIVA'].dropna().unique())
)

causa = st.sidebar.multiselect(
    "Causa",
    sorted(df['CAUSA'].dropna().unique())
)

defeito = st.sidebar.multiselect(
    "Defeito",
    sorted(df['DEFEITO'].dropna().unique())
)

if critic:
    df = df[df['CRITICIDADE'].isin(critic)]

if status_pred:
    df = df[df['STATUS_PREDITIVA'].isin(status_pred)]

if causa:
    df = df[df['CAUSA'].isin(causa)]

if defeito:
    df = df[df['DEFEITO'].isin(defeito)]

# =============================
# FILTROS TOPO
# =============================

c1, c2, c3 = st.columns(3)

setor = c1.multiselect("Setor", sorted(df['SETOR'].unique()))
oficina = c2.multiselect("Oficina", sorted(df['OFICINA'].unique()))

periodo = c3.date_input(
    "Período",
    [df['DATA'].min(), df['DATA'].max()]
)

if setor:
    df = df[df['SETOR'].isin(setor)]

if oficina:
    df = df[df['OFICINA'].isin(oficina)]

if len(periodo)==2:
    df = df[
        (df['DATA']>=pd.to_datetime(periodo[0])) &
        (df['DATA']<=pd.to_datetime(periodo[1]))
    ]

# =============================
# KPI
# =============================

total = len(df)
executada = (df['STATUS_PREDITIVA']=="MANUTENÇÃO EXECUTADA").sum()
pendente = (df['STATUS_PREDITIVA']=="PENDENTE").sum()
nao_conf = (df['STATUS_PREDITIVA']=="NÃO CONFORME").sum()

k1,k2,k3,k4 = st.columns(4)

k1.metric("Total Anomalias", total)
k2.metric("Executadas", executada)
k3.metric("Pendentes", pendente)
k4.metric("Não Conforme", nao_conf)

st.divider()

# =============================
# GRAFICOS
# =============================

def grafico_barra(data, coluna, cor, titulo):

    base = data[coluna].value_counts().reset_index()
    base.columns=[coluna,'QTD']

    chart = alt.Chart(base).mark_bar(color=cor).encode(
        x=alt.X(f"{coluna}:N", sort='-y', axis=alt.Axis(labelAngle=-45)),
        y='QTD'
    )

    text = chart.mark_text(dy=-5).encode(text='QTD')

    st.subheader(titulo)
    st.altair_chart(chart+text, use_container_width=True)

g1,g2 = st.columns(2)

with g1:
    grafico_barra(df,'SETOR','#5E7F73','Ranking por Setor')

with g2:
    grafico_barra(df,'OFICINA','#8FAF9F','Ranking por Oficina')

st.divider()

g3,g4 = st.columns(2)

with g3:
    grafico_barra(df,'STATUS_PREDITIVA','#3E5F55','Status Preditiva')

with g4:
    grafico_barra(df,'CAUSA','#5E7F73','Ocorrências por Causa')

st.divider()

backlog = df[df['STATUS_PREDITIVA'].isin(['PENDENTE','NÃO CONFORME'])]

grafico_barra(backlog,'OFICINA','#3E5F55','Backlog por Oficina')

st.divider()

df['DATA']=df['DATA'].dt.strftime('%d/%m/%Y')

c1,c2 = st.columns([6,2])

c1.subheader("Tabela de Anomalias")

output = BytesIO()
df.to_excel(output,index=False)
output.seek(0)

c2.download_button(
    "⬇️ Baixar Base Filtrada",
    data=output,
    file_name="rota_filtrada.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)

cols = [
    'DATA','OM','LI','DESCRIÇÃO_LI','SETOR',
    'OFICINA','CRITICIDADE','TEXTO_BREVE',
    'CAUSA','STATUS_PREDITIVA','DEFEITO'
]

st.dataframe(df[cols], use_container_width=True)