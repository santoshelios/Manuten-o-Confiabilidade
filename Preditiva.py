import streamlit as st
import pandas as pd
import altair as alt
import requests
from datetime import datetime
import unicodedata
import io

import pytz

st.set_page_config(
    page_title="Rota Preditiva",
    page_icon="⚙️",
    layout="wide"
)

# ================= LOGIN =================
USUARIOS = {
    "admin": "1234",
    "analista": "1234",
    "leandro.sales": "dalevi"
}

if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario = None

if "filtro_defeito_click" not in st.session_state:
    st.session_state.filtro_defeito_click = None

# ================= CSS =================
st.markdown(f"""
<style>

section[data-testid="stSidebar"]{{
    background-color:#F4F7F3;
}}

section[data-testid="stSidebar"] label{{
    color:#5B7F4F;
    font-weight:600;
}}

.kpi-card {{
    background: linear-gradient(135deg, #FFFFFF, #F7F9F8);
    border-radius: 18px;
    padding: 20px;
    text-align: center;
    box-shadow: 0px 8px 20px rgba(0,0,0,0.08);
    border: 1px solid #E6ECE8;
    transition: all 0.25s ease;
}}

.kpi-card:hover {{
    transform: translateY(-5px);
    box-shadow: 0px 12px 25px rgba(0,0,0,0.12);
}}

.kpi-title {{
    font-size: 12px;
    color: #7A8B85;
    font-weight: 600;
    margin-bottom: 8px;
}}

.kpi-value {{
    font-size: 34px;
    font-weight: 700;
}}

[data-testid="stAltairChart"] {{
    background: #FFFFFF;
    border-radius: 16px;
    padding: 10px;
    box-shadow: 0px 6px 16px rgba(0,0,0,0.08);
    border: 1px solid #E6ECE8;
}}

</style>
""", unsafe_allow_html=True)

SUPABASE_URL="https://kplsspnxemhzxfpzxbbl.supabase.co"
SUPABASE_KEY="sb_publishable_M-_WauseWVAmnb1SIzOmQg_VLcc-O2e"

# ================= FUNÇÕES =================
def normalizar_coluna(col):
    col = unicodedata.normalize('NFKD', col).encode('ASCII','ignore').decode('ASCII')
    return col.lower().replace(" ","_")

def enviar(df):
    url = f"{SUPABASE_URL}/rest/v1/rota_preditiva"

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }

    delete_url = f"{SUPABASE_URL}/rest/v1/rota_preditiva?id=gt.0"

    headers_delete = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Prefer": "return=minimal"
    }

    requests.delete(delete_url, headers=headers_delete)

    df = df.astype(object).where(pd.notnull(df), None)
    df.columns = [normalizar_coluna(c) for c in df.columns]

    if "om" in df.columns and "oficina" in df.columns:
        df["om"] = df["om"].astype(str).str.strip()
        df["oficina"] = df["oficina"].astype(str).str.strip().str.upper()
        df = df.drop_duplicates(subset=["om","oficina"], keep="last")

    if "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"]).dt.strftime("%Y-%m-%d")

    r = requests.post(url, json=df.to_dict("records"), headers=headers)

    return r.status_code, r.text

@st.cache_data(ttl=60)
def carregar():
    headers={"apikey":SUPABASE_KEY,"Authorization":f"Bearer {SUPABASE_KEY}"}
    dados=[]; offset=0

    while True:
        url=f"{SUPABASE_URL}/rest/v1/rota_preditiva?select=*&limit=1000&offset={offset}"
        r=requests.get(url,headers=headers).json()
        if not r: break
        dados.extend(r); offset+=1000

    df=pd.DataFrame(dados)
    df.columns=df.columns.str.upper()
    df["DATA"]=pd.to_datetime(df["DATA"])
    df["SAFRA"] = df["DATA"].dt.year.astype(str).str[-2:] + "/" + (df["DATA"].dt.year+1).astype(str).str[-2:]
    return df

# ================= SIDEBAR =================
with st.sidebar:

    st.markdown("## 🔐 Acesso")

    if not st.session_state.logado:

        user = st.text_input("Usuário",autocomplete = 'off')
        senha = st.text_input("Senha", type="password",autocomplete = "password")

        if st.button("Entrar no sistema"):
            if user in USUARIOS and USUARIOS[user] == senha:
                st.session_state.logado = True
                st.session_state.usuario = user
                st.rerun()
            else:
                st.error("Usuário ou senha inválido")

    else:
        st.success(f"Usuário ativo: {st.session_state.usuario}")

        if st.button("Sair do sistema"):
            st.session_state.logado = False
            st.rerun()

        st.markdown("### ⚙️ Controles")

        if st.button("🔄 LIMPAR TODOS FILTROS"):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")

        with st.expander("📤 Upload de Dados"):
            arquivo = st.file_uploader("Planilha (.xlsx)", type=["xlsx"])

            if arquivo:
                df_up = pd.read_excel(arquivo, sheet_name="STATUS")
                df_up.columns = df_up.columns.str.replace("Satus_Usuário", "Status_Usuário")

                st.success(f"{len(df_up)} registros carregados")

                confirmar = st.checkbox("⚠️ Confirmar substituição total dos dados")

                if st.button("🚀 Enviar carga") and confirmar:
                    status, msg = enviar(df_up)
                    st.write("Status:", status)

                    if status in [200, 201]:
                        st.success("Carga enviada com sucesso")
                    else:
                        st.error(f"Erro:\n{msg}")

# ================= DADOS =================
df=carregar()
if df.empty: st.stop()

tz = pytz.timezone("America/Sao_Paulo")
agora = datetime.now(tz)

st.caption(f"Última atualização: {agora.strftime('%d/%m/%Y %H:%M:%S')}")

# ================= HEADER =================
c_title, c_logo = st.columns([8,1])

with c_title:
    st.markdown("""
    <h1 style='margin-bottom:0;'>Relatório Confiabilidade</h1>
    <h3 style='margin-top:0; color:#5B7F4F;'>Rotas Preditivas</h3>
    """, unsafe_allow_html=True)

with c_logo:
    st.image("raizen_shell.png", width=200)
   

# ================= FILTROS =================
c1,c2,c3=st.columns(3)

setor=c1.multiselect("Setor",sorted(df.SETOR.dropna().unique()),placeholder = "Selecione o Setor")
oficina=c2.multiselect("Oficina",sorted(df.OFICINA.dropna().unique()),placeholder = "Selecione Oficina")
safra=c3.multiselect("Safra",sorted(df.SAFRA.unique()),default=[sorted(df.SAFRA.unique())[-1]],placeholder = "Selecione a Safra")

if setor: df=df[df.SETOR.isin(setor)]
if oficina: df=df[df.OFICINA.isin(oficina)]
if safra: df=df[df.SAFRA.isin(safra)]

# ================= FILTROS AVANÇADOS =================
if st.session_state.logado:

    st.sidebar.markdown("### 🔎 Filtros")

    status_user=st.sidebar.multiselect("Status Usuário",sorted(df.STATUS_USUARIO.dropna().unique()))
    efet=st.sidebar.multiselect("Manutenção Efetuada",sorted(df.EFETUADA_MANUTENCAO.dropna().unique()))
    defeito=st.sidebar.multiselect("Defeito",sorted(df.DEFEITO.dropna().unique()))
    causa=st.sidebar.multiselect("Causa",sorted(df.CAUSA.dropna().unique()))
    critic=st.sidebar.multiselect("Criticidade",sorted(df.CRITICIDADE.dropna().unique()))
    stat_pred=st.sidebar.multiselect("Status Preditiva",sorted(df.STATUS_PREDITIVA.dropna().unique()))

    if status_user: df=df[df.STATUS_USUARIO.isin(status_user)]
    if efet: df=df[df.EFETUADA_MANUTENCAO.isin(efet)]
    if defeito: df=df[df.DEFEITO.isin(defeito)]
    if causa: df=df[df.CAUSA.isin(causa)]
    if critic: df=df[df.CRITICIDADE.isin(critic)]
    if stat_pred: df=df[df.STATUS_PREDITIVA.isin(stat_pred)]

# ================= KPI =================
total=len(df)
executadas=(df.STATUS_PREDITIVA=="Manutenção Executada").sum()
pendentes=(df.STATUS_PREDITIVA=="Pendente").sum()
nao_conf=(df.STATUS_PREDITIVA=="Não Conforme").sum()

exec_real = round(executadas/(executadas+pendentes+nao_conf)*100,1) if (executadas+pendentes+nao_conf)>0 else 0

back=df[df.STATUS_PREDITIVA.isin(["Pendente","Não Conforme"])]

def card(titulo, valor, cor, icone):
    return f"""
    <div class="kpi-card">
        <div class="kpi-title">{icone} {titulo}</div>
        <div class="kpi-value" style="color:{cor};">{valor}</div>
    </div>
    """

k1,k2,k3,k4,k5,k6=st.columns(6)

k1.markdown(card("Total", total, "#2F3E46", "📊"), unsafe_allow_html=True)
k2.markdown(card("Executadas", executadas, "#2E7D32", "✅"), unsafe_allow_html=True)
k3.markdown(card("Pendentes", pendentes, "#F9A825", "⏳"), unsafe_allow_html=True)
k4.markdown(card("Não Conforme", nao_conf, "#C62828", "⚠️"), unsafe_allow_html=True)
k5.markdown(card("Execução %", f"{exec_real}%", "#1565C0", "📈"), unsafe_allow_html=True)
k6.markdown(card("Backlog", len(back), "#6A1B9A", "🔥"), unsafe_allow_html=True)

st.divider()

# ================= RANKINGS =================
r1,r2=st.columns(2)

def add_labels(chart):
    return chart + chart.mark_text(
        dy=-8,
        color="#263238",
        fontSize=13,
        fontWeight="bold"
    ).encode(text="QTD:Q")

with r1:
    base=df["SETOR"].value_counts().reset_index()
    base.columns=["SETOR","QTD"]

    chart = alt.Chart(base).mark_bar(
        color="#5B7F4F",
        cornerRadiusTopLeft=8,
        cornerRadiusTopRight=8
    ).encode(
        x=alt.X("SETOR:N",sort="-y",axis=alt.Axis(labelAngle=-45)),
        y="QTD:Q"
    )

    st.altair_chart(add_labels(chart).properties(title="Ranking por Setor"), use_container_width=True)

with r2:
    base=df["OFICINA"].value_counts().reset_index()
    base.columns=["OFICINA","QTD"]

    chart = alt.Chart(base).mark_bar(
        color="#92A197",
        cornerRadiusTopLeft=8,
        cornerRadiusTopRight=8
    ).encode(
        x=alt.X("OFICINA:N", sort="-y", axis=alt.Axis(labelAngle=0)),
        y="QTD:Q"
    )

    st.altair_chart(add_labels(chart).properties(title="Ranking por Oficina"), use_container_width=True)

st.divider()

# ================= BACKLOG =================
b1,b2=st.columns(2)

with b1:
    base=back["OFICINA"].value_counts().reset_index()
    base.columns=["OFICINA","QTD"]

    chart = alt.Chart(base).mark_bar(
        color="#92A197",
        cornerRadiusTopLeft=8,
        cornerRadiusTopRight=8
    ).encode(
        x=alt.X("OFICINA:N", sort="-y", axis=alt.Axis(labelAngle=0)),
        y="QTD:Q"
    )

    st.altair_chart(add_labels(chart).properties(title="Backlog por Oficina"), use_container_width=True)

with b2:
    top_n = st.slider("Quantidade de defeitos no ranking",5,20,10)

    base=df["DEFEITO"].value_counts().reset_index()
    base.columns=["DEFEITO","QTD"]
    base=base.head(top_n)

    base["COR"] = ["#2E7D32" if i==0 else "#A5D6A7" for i in range(len(base))]

    chart = alt.Chart(base).mark_bar(
        cornerRadiusTopLeft=8,
        cornerRadiusBottomLeft=8
    ).encode(
        y=alt.Y("DEFEITO:N", sort="-x", axis=alt.Axis(labelLimit=300)),
        x=alt.X(
            "QTD:Q",
            axis=alt.Axis(labels=False, ticks=False, title=None)
        ),
        color=alt.Color("COR:N", scale=None),
        tooltip=[
            alt.Tooltip("DEFEITO:N", title="Defeito"),
            alt.Tooltip("QTD:Q", title="Quantidade")
        ]
    )

    text = chart.mark_text(
        align="left",
        dx=6,
        fontSize=13,
        color="#263238",
        fontWeight="bold"
    ).encode(text="QTD:Q")

    st.altair_chart((chart + text).properties(height=400,title="Ranking de Defeitos"), use_container_width=True)

st.divider()

# ================= TABELA =================
tabela=df.copy()

tabela["IDADE"]=(datetime.now()-tabela["DATA"]).dt.days

tabela["STATUS"]=tabela["STATUS_PREDITIVA"].apply(lambda x:
    "🟢" if x=="Manutenção Executada"
    else "🔴" if x=="Não Conforme"
    else "🟡")

tabela["PRIORIDADE"]=tabela["CRITICIDADE"].apply(lambda x:
    "🔴 Crítico" if x=="A"
    else "🟡 Alerta" if x=="B"
    else "🟢 Normal")

tabela=tabela[
    ["DATA","OM","STATUS","OFICINA","DESCRICAO_LI","STATUS_PREDITIVA","DEFEITO","PRIORIDADE","IDADE"]
]

tabela["DATA"] = tabela["DATA"].dt.strftime("%d/%m/%Y")

# 🔥 DOWNLOAD EXCEL
buffer = io.BytesIO()

with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    tabela.to_excel(writer, index=False, sheet_name="Relatorio")

buffer.seek(0)

st.download_button(
    label="📥 Baixar tabela (Excel)",
    data=buffer,
    file_name=f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.dataframe(tabela,use_container_width=True)