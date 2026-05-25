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

# ================= SUPABASE =================
SUPABASE_URL = "https://kplsspnxemhzxfpzxbbl.supabase.co"
SUPABASE_KEY = "sb_publishable_M-_WauseWVAmnb1SIzOmQg_VLcc-O2e"

# ================= FUNÇÕES =================
def normalizar_coluna(col):
    col = unicodedata.normalize('NFKD', col).encode('ASCII', 'ignore').decode('ASCII')
    return col.lower().replace(" ", "_")

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

    try:

        requests.delete(
            delete_url,
            headers=headers_delete,
            timeout=60
        )

        df = df.astype(object).where(pd.notnull(df), None)
        df.columns = [normalizar_coluna(c) for c in df.columns]

        if "om" in df.columns and "oficina" in df.columns:
            df["om"] = df["om"].astype(str).str.strip()
            df["oficina"] = df["oficina"].astype(str).str.strip().str.upper()

            df = df.drop_duplicates(
                subset=["om", "oficina"],
                keep="last"
            )

        if "data" in df.columns:
            df["data"] = pd.to_datetime(df["data"]).dt.strftime("%Y-%m-%d")

        r = requests.post(
            url,
            json=df.to_dict("records"),
            headers=headers,
            timeout=120
        )

        return r.status_code, r.text

    except Exception as e:
        return 500, str(e)

@st.cache_data(ttl=60)
def carregar():

    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}"
    }

    dados = []
    offset = 0

    while True:

        url = (
            f"{SUPABASE_URL}/rest/v1/rota_preditiva"
            f"?select=*&limit=1000&offset={offset}"
        )

        try:

            response = requests.get(
                url,
                headers=headers,
                timeout=30
            )

            print("STATUS:", response.status_code)
            print("RETORNO:", response.text[:300])

            response.raise_for_status()

            try:
                r = response.json()

            except ValueError:

                st.error("❌ Supabase retornou resposta inválida")

                with st.expander("Detalhes técnicos"):
                    st.code(response.text[:3000])

                return pd.DataFrame()

        except requests.exceptions.Timeout:

            st.error("⏳ Timeout ao conectar no Supabase")
            return pd.DataFrame()

        except requests.exceptions.ConnectionError:

            st.error("🌐 Erro de conexão com Supabase")
            return pd.DataFrame()

        except requests.exceptions.HTTPError:

            st.error(f"❌ Erro HTTP {response.status_code}")

            with st.expander("Detalhes do erro"):

                st.code(response.text[:3000])

            return pd.DataFrame()

        except Exception as e:

            st.error(f"❌ Erro inesperado: {e}")

            return pd.DataFrame()

        if not r:
            break

        dados.extend(r)
        offset += 1000

    df = pd.DataFrame(dados)

    if df.empty:
        return df

    df.columns = df.columns.str.upper()

    if "DATA" in df.columns:

        df["DATA"] = pd.to_datetime(
            df["DATA"],
            errors="coerce"
        )

        df["SAFRA"] = (
            df["DATA"].dt.year.astype(str).str[-2:]
            + "/"
            + (df["DATA"].dt.year + 1).astype(str).str[-2:]
        )

    return df

# ================= SIDEBAR =================
with st.sidebar:

    st.markdown("## 🔐 Acesso")

    if not st.session_state.logado:

        user = st.text_input("Usuário", autocomplete='off')

        senha = st.text_input(
            "Senha",
            type="password",
            autocomplete="password"
        )

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

            arquivo = st.file_uploader(
                "Planilha (.xlsx)",
                type=["xlsx"]
            )

            if arquivo:

                try:

                    df_up = pd.read_excel(
                        arquivo,
                        sheet_name="STATUS"
                    )

                    df_up.columns = df_up.columns.str.replace(
                        "Satus_Usuário",
                        "Status_Usuário"
                    )

                    st.success(f"{len(df_up)} registros carregados")

                    confirmar = st.checkbox(
                        "⚠️ Confirmar substituição total dos dados"
                    )

                    if st.button("🚀 Enviar carga") and confirmar:

                        with st.spinner("Enviando dados..."):

                            status, msg = enviar(df_up)

                        st.write("Status:", status)

                        if status in [200, 201]:

                            st.success("✅ Carga enviada com sucesso")

                            st.cache_data.clear()

                        else:

                            st.error(f"❌ Erro:\n{msg}")

                except Exception as e:

                    st.error(f"Erro leitura planilha: {e}")

# ================= DADOS =================
df = carregar()

if df.empty:

    st.warning("⚠️ Nenhum dado encontrado")

    st.stop()

tz = pytz.timezone("America/Sao_Paulo")

agora = datetime.now(tz)

st.caption(
    f"Última atualização: "
    f"{agora.strftime('%d/%m/%Y %H:%M:%S')}"
)

# ================= HEADER =================
c_title, c_logo = st.columns([8,1])

with c_title:

    st.markdown("""
    <h1 style='margin-bottom:0;'>
        Relatório Confiabilidade
    </h1>

    <h3 style='margin-top:0; color:#5B7F4F;'>
        Rotas Preditivas
    </h3>
    """, unsafe_allow_html=True)

with c_logo:

    try:
        st.image("raizen_shell.png", width=200)
    except:
        pass

# ================= FILTROS =================
c1, c2, c3 = st.columns(3)

setor = c1.multiselect(
    "Setor",
    sorted(df.SETOR.dropna().unique()),
    placeholder="Selecione o Setor"
)

oficina = c2.multiselect(
    "Oficina",
    sorted(df.OFICINA.dropna().unique()),
    placeholder="Selecione Oficina"
)

safra = c3.multiselect(
    "Safra",
    sorted(df.SAFRA.unique()),
    default=[sorted(df.SAFRA.unique())[-1]],
    placeholder="Selecione a Safra"
)

if setor:
    df = df[df.SETOR.isin(setor)]

if oficina:
    df = df[df.OFICINA.isin(oficina)]

if safra:
    df = df[df.SAFRA.isin(safra)]

# ================= KPI =================
total = len(df)

executadas = (
    df.STATUS_PREDITIVA == "Manutenção Executada"
).sum()

pendentes = (
    df.STATUS_PREDITIVA == "Pendente"
).sum()

nao_conf = (
    df.STATUS_PREDITIVA == "Não Conforme"
).sum()

base_exec = executadas + pendentes + nao_conf

exec_real = round(
    executadas / base_exec * 100,
    1
) if base_exec > 0 else 0

back = df[
    df.STATUS_PREDITIVA.isin(
        ["Pendente", "Não Conforme"]
    )
]

def card(titulo, valor, cor, icone):

    return f"""
    <div class="kpi-card">
        <div class="kpi-title">{icone} {titulo}</div>
        <div class="kpi-value" style="color:{cor};">
            {valor}
        </div>
    </div>
    """

k1,k2,k3,k4,k5,k6 = st.columns(6)

k1.markdown(card("Total", total, "#2F3E46", "📊"), unsafe_allow_html=True)

k2.markdown(card("Executadas", executadas, "#2E7D32", "✅"), unsafe_allow_html=True)

k3.markdown(card("Pendentes", pendentes, "#F9A825", "⏳"), unsafe_allow_html=True)

k4.markdown(card("Não Conforme", nao_conf, "#C62828", "⚠️"), unsafe_allow_html=True)

k5.markdown(card("Execução %", f"{exec_real}%", "#1565C0", "📈"), unsafe_allow_html=True)

k6.markdown(card("Backlog", len(back), "#6A1B9A", "🔥"), unsafe_allow_html=True)

st.divider()

# ================= TABELA =================
tabela = df.copy()

tabela["IDADE"] = (
    datetime.now() - tabela["DATA"]
).dt.days

tabela = tabela[
    [
        "DATA",
        "OM",
        "OFICINA",
        "DESCRICAO_LI",
        "STATUS_PREDITIVA",
        "DEFEITO",
        "IDADE"
    ]
]

tabela["DATA"] = tabela["DATA"].dt.strftime("%d/%m/%Y")

# ================= DOWNLOAD =================
buffer = io.BytesIO()

with pd.ExcelWriter(buffer, engine="openpyxl") as writer:

    tabela.to_excel(
        writer,
        index=False,
        sheet_name="Relatorio"
    )

buffer.seek(0)

st.download_button(
    label="📥 Baixar tabela (Excel)",
    data=buffer,
    file_name=f"relatorio_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.dataframe(
    tabela,
    width='stretch'
)