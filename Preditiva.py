import streamlit as st
import pandas as pd
import altair as alt
import requests
from datetime import datetime

st.set_page_config(
    page_title="Rota Preditiva",
    page_icon="⚙️",
    layout="wide"
)


# ================= CSS =================

st.markdown("""
<style>

/* SIDEBAR */
section[data-testid="stSidebar"]{
    background-color:#F4F7F3;
}

section[data-testid="stSidebar"] label{
    color:#5B7F4F;
    font-weight:600;
}

/* BOTÃO */
div[data-testid="stSidebar"] button {
    background: linear-gradient(135deg, #5B7F4F, #7FA36B);
    color: white;
    border-radius: 10px;
    border: none;
    padding: 10px 12px;
    font-weight: 600;
    transition: all 0.25s ease;
    box-shadow: 0px 3px 6px rgba(0,0,0,0.1);
}

div[data-testid="stSidebar"] button:hover {
    transform: translateY(-2px);
    box-shadow: 0px 6px 12px rgba(0,0,0,0.15);
    background: linear-gradient(135deg, #4E6F44, #6D8F5A);
}

div[data-testid="stSidebar"] button:active {
    transform: scale(0.98);
}

/* ===== KPI CARDS ===== */
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E6ECE8;
    border-radius: 12px;
    padding: 16px 12px;
    text-align: center;
    box-shadow: 0px 3px 8px rgba(0,0,0,0.04);
    transition: all 0.2s ease;
}

.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0px 6px 14px rgba(0,0,0,0.08);
}

.kpi-title {
    font-size: 13px;
    color: #6B7C75;
    font-weight: 600;
    margin-bottom: 6px;
}

.kpi-value {
    font-size: 28px;
    font-weight: 700;
    color: #2F3E46;
}

</style>
""", unsafe_allow_html=True)

SUPABASE_URL="https://kplsspnxemhzxfpzxbbl.supabase.co"
SUPABASE_KEY="sb_publishable_M-_WauseWVAmnb1SIzOmQg_VLcc-O2e"

# ================= LIMPAR FILTROS =================

with st.sidebar:
    st.markdown("### ⚙️ Controles")
    if st.button("🔄 LIMPAR TODOS FILTROS"):
        st.cache_data.clear()
        st.rerun()

# ================= FUNÇÃO CARREGAR =================

@st.cache_data(ttl=60)
def carregar():
    headers={
        "apikey":SUPABASE_KEY,
        "Authorization":f"Bearer {SUPABASE_KEY}"
    }

    dados=[]
    offset=0

    while True:
        url=f"{SUPABASE_URL}/rest/v1/rota_preditiva?select=*&limit=1000&offset={offset}"
        r=requests.get(url,headers=headers)
        lote=r.json()

        if not lote:
            break

        dados.extend(lote)
        offset+=1000

    df=pd.DataFrame(dados)

    df.columns=df.columns.str.upper()
    df["DATA"]=pd.to_datetime(df["DATA"],errors="coerce")

    return df

# ================= HEADER =================

c_title, c_logo = st.columns([8, 1])

with c_title:
    st.markdown("""
    <h1 style='margin-bottom:0;'>Relatório Confiabilidade</h1>
    <h3 style='margin-top:0; color:#5B7F4F;'>Rotas Preditivas</h3>
    """, unsafe_allow_html=True)

with c_logo:
    st.image("logo.png", width=70)

df=carregar()

if df.empty:
    st.stop()

# ================= FILTROS TOPO =================

c1,c2,c3=st.columns(3)

setor=c1.multiselect("Setor",sorted(df.SETOR.dropna().unique()))
oficina=c2.multiselect("Oficina",sorted(df.OFICINA.dropna().unique()))
periodo=c3.date_input("Período",[df.DATA.min(),df.DATA.max()])

if setor:
    df=df[df.SETOR.isin(setor)]

if oficina:
    df=df[df.OFICINA.isin(oficina)]

if len(periodo)==2:
    df=df[(df.DATA>=pd.to_datetime(periodo[0]))&(df.DATA<=pd.to_datetime(periodo[1]))]

# ================= SIDEBAR =================

st.sidebar.markdown("### 🔎 Filtros")

status_user=st.sidebar.multiselect("Status Usuário",sorted(df.STATUS_USUARIO.dropna().unique()))


efet=st.sidebar.multiselect("Efetuada",sorted(df.EFETUADA_MANUTENCAO.dropna().unique()))


defeito=st.sidebar.multiselect("Defeito",sorted(df.DEFEITO.dropna().unique()))

causa=st.sidebar.multiselect("Causa",sorted(df.CAUSA.dropna().unique()))

critic=st.sidebar.multiselect("Criticidade",sorted(df.CRITICIDADE.dropna().unique()))

stat_pred=st.sidebar.multiselect("Status Preditiva",sorted(df.STATUS_PREDITIVA.dropna().unique()))


if status_user:
    df=df[df.STATUS_USUARIO.isin(status_user)]

if efet:
    df=df[df.EFETUADA_MANUTENCAO.isin(efet)]

if defeito:
    df=df[df.DEFEITO.isin(defeito)]

if causa:
    df=df[df.CAUSA.isin(causa)]

if critic:
    df=df[df.CRITICIDADE.isin(critic)]

if stat_pred:
    df=df[df.STATUS_PREDITIVA.isin(stat_pred)]

# ================= KPI =================

total=len(df)
executadas=(df.STATUS_PREDITIVA=="Manutenção Executada").sum()
pendentes=(df.STATUS_PREDITIVA=="Pendente").sum()
nao_conf=(df.STATUS_PREDITIVA=="Não Conforme").sum()

exec_real = round(executadas/(executadas+pendentes+nao_conf)*100,1) if (executadas+pendentes+nao_conf)>0 else 0

back=df[df.STATUS_PREDITIVA.isin(["Pendente","Não Conforme"])]
aging=(datetime.now()-back["DATA"]).dt.days
back_30=(aging>30).sum()

# ===== FUNÇÃO CARD =====

def card(titulo, valor):
    return f"""
    <div class="kpi-card">
        <div class="kpi-title">{titulo}</div>
        <div class="kpi-value">{valor}</div>
    </div>
    """

k1,k2,k3,k4,k5,k6=st.columns(6)

with k1:
    st.markdown(card("Total", total), unsafe_allow_html=True)

with k2:
    st.markdown(card("Executadas", executadas), unsafe_allow_html=True)

with k3:
    st.markdown(card("Pendentes", pendentes), unsafe_allow_html=True)

with k4:
    st.markdown(card("Não Conforme", nao_conf), unsafe_allow_html=True)

with k5:
    st.markdown(card("Execução Real %", f"{exec_real}%"), unsafe_allow_html=True)

with k6:
    st.markdown(card("Backlog >30 dias", back_30), unsafe_allow_html=True)

st.divider()

# ================= RANKINGS =================

r1,r2=st.columns(2)

with r1:
    base=df["SETOR"].value_counts().reset_index()
    base.columns=["SETOR","QTD"]

    chart=alt.Chart(base).mark_bar(
        color="#5B7F4F",
        cornerRadiusTopLeft=8,
        cornerRadiusTopRight=8
    ).encode(
        x=alt.X("SETOR:N",sort="-y",axis=alt.Axis(labelAngle=-45)),
        y="QTD:Q"
    ).properties(height=300,title="Ranking Setor")

    st.altair_chart(chart,use_container_width=True)

with r2:
    base=df["OFICINA"].value_counts().reset_index()
    base.columns=["OFICINA","QTD"]

    chart=alt.Chart(base).mark_bar(
        color="#92A197",
        cornerRadiusTopLeft=8,
        cornerRadiusTopRight=8
    ).encode(
        x=alt.X("OFICINA:N",sort="-y",axis=alt.Axis(labelAngle=0)),
        y="QTD:Q"
    ).properties(height=300,title="Ranking Oficina")

    st.altair_chart(chart,use_container_width=True)

st.divider()

# ================= BACKLOG =================

b1,b2=st.columns(2)

with b1:
    base=back["OFICINA"].value_counts().reset_index()
    base.columns=["OFICINA","QTD"]

    chart=alt.Chart(base).mark_bar(
        color="#92A197",
        cornerRadiusTopLeft=8,
        cornerRadiusTopRight=8
    ).encode(
        x=alt.X("OFICINA:N",sort="-y",axis=alt.Axis(labelAngle=0)),
        y="QTD:Q"
    ).properties(height=320,title="Backlog")

    st.altair_chart(chart,use_container_width=True)

with b2:

    # PRIORIDADE: backlog
    if len(back) > 0:
        tabela = back.copy()
    else:
        tabela = df.copy()

    tabela["AGING"] = (datetime.now() - tabela["DATA"]).dt.days

    # ICONES
    def status_icon(x):
        if x == "Manutenção Executada":
            return "🟢"
        elif x == "Não Conforme":
            return "🔴"
        else:
            return "🟡"

    def critic_icon(x):
        if x == "A":
            return "🔴 Crítico"
        elif x == "B":
            return "🟡 Alerta"
        else:
            return "🟢 Normal"

    tabela["STATUS"] = tabela["STATUS_PREDITIVA"].apply(status_icon)
    tabela["PRIORIDADE"] = tabela["CRITICIDADE"].apply(critic_icon)

    tabela = tabela[[
        "OM",
        "STATUS",
        "OFICINA",
        "DESCRICAO_LI",        
        "STATUS_PREDITIVA",
        "PRIORIDADE",
        "AGING"
    ]]

    if "CRITICIDADE" in tabela.columns:
        tabela = tabela.sort_values(by=["CRITICIDADE","AGING"], ascending=[True, False])
    else:
        tabela = tabela.sort_values(by=["AGING"], ascending=[False])

    st.dataframe(tabela, use_container_width=True, height=320)

st.divider()

df["DATA"]=df["DATA"].dt.strftime("%d/%m/%Y")

st.dataframe(df,use_container_width=True)