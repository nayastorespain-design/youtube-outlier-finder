import pandas as pd
import requests
import streamlit as st
from googleapiclient.discovery import build

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="YouTube Outlier Finder",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos CSS personalizados para diseño Pro
st.markdown(
    """
    <style>
    /* Estilo de la tarjeta principal */
    .outlier-card {
        background-color: #1a1c23;
        border: 1px solid #2e323e;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    .outlier-title {
        font-size: 19px;
        font-weight: 700;
        color: #ffffff !important;
        text-decoration: none;
        line-height: 1.3;
    }
    .outlier-title:hover {
        color: #ff4b4b !important;
    }
    .outlier-channel {
        color: #9ea4b0;
        font-size: 14px;
        margin-top: 4px;
        margin-bottom: 16px;
    }
    /* Insignia del multiplicador */
    .badge-outlier {
        background: linear-gradient(135deg, #ff4b4b 0%, #ff7676 100%);
        color: white;
        font-weight: 800;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 15px;
        display: inline-block;
    }
    /* Estilos de datos */
    .metric-box {
        background-color: #242731;
        padding: 10px 15px;
        border-radius: 8px;
        text-align: center;
    }
    .metric-label {
        font-size: 12px;
        color: #9ea4b0;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 18px;
        font-weight: 700;
        color: #ffffff;
    }
    /* Botón de YouTube */
    .btn-yt {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #FF0000;
        color: white !important;
        padding: 8px 18px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        font-size: 14px;
        transition: background-color 0.2s;
    }
    .btn-yt:hover {
        background-color: #cc0000;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Claves API desde Secrets
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY")
LEMON_API_KEY = st.secrets.get("LEMON_API_KEY")

# --- VALIDACIÓN DE LICENCIA ---


def validate_license_key(license_key):
    if not LEMON_API_KEY or not license_key:
        return False
    url = "https://api.lemonsqueezy.com/v1/licenses/validate"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {LEMON_API_KEY}",
    }
    try:
        response = requests.post(
            url, headers=headers, data={"license_key": license_key}
        )
        return response.json().get("valid", False)
    except Exception:
        return False


# --- CONSULTA A LA API (OPTIMIZADA) ---
@st.cache_data(ttl=43200, show_spinner=False)
def fetch_youtube_outliers(api_key, query, order, max_results):
    youtube = build("youtube", "v3", developerKey=api_key)

    # 1. Búsqueda básica
    search_res = (
        youtube.search()
        .list(
            q=query,
            part="snippet",
            type="video",
            order=order,
            maxResults=max_results,
        )
        .execute()
    )

    items = search_res.get("items", [])
    if not items:
        return []

    video_ids = [item["id"]["videoId"] for item in items]
    channel_ids = [item["snippet"]["channelId"] for item in items]

    # 2. Batching de Vídeos
    v_res = (
        youtube.videos()
        .list(part="statistics", id=",".join(video_ids))
        .execute()
    )
    views_map = {
        v_item["id"]: int(v_item["statistics"].get("viewCount", 0))
        for v_item in v_res.get("items", [])
    }

    # 3. Batching de Canales
    c_res = (
        youtube.channels()
        .list(part="statistics", id=",".join(set(channel_ids)))
        .execute()
    )
    subs_map = {
        c_item["id"]: int(c_item["statistics"].get("subscriberCount", 0))
        for c_item in c_res.get("items", [])
    }

    # 4. Cálculo de Outliers
    outliers = []
    for item in items:
        vid_id = item["id"]["videoId"]
        chan_id = item["snippet"]["channelId"]
        views = views_map.get(vid_id, 0)
        subs = subs_map.get(chan_id, 0)

        if views > subs and subs > 0:
            ratio = round(views / subs, 1)
            outliers.append(
                {
                    "titulo": item["snippet"]["title"],
                    "canal": item["snippet"]["channelTitle"],
                    "visitas": f"{views:,}",
                    "suscriptores": f"{subs:,}",
                    "ratio": f"{ratio}x",
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                }
            )

    return outliers


# --- RENDERIZADO DE RESULTADOS EN TARJETAS ---


def render_outliers(outliers):
    for item in outliers:
        st.markdown(
            f"""
            <div class="outlier-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 15px;">
                    <div>
                        <a href="{item['url']}" target="_blank" class="outlier-title">{item['titulo']}</a>
                        <div class="outlier-channel">📺 Canal: <strong>{item['canal']}</strong></div>
                    </div>
                    <div>
                        <span class="badge-outlier">🔥 {item['ratio']}</span>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1.5fr; gap: 15px; margin-top: 10px; align-items: center;">
                    <div class="metric-box">
                        <div class="metric-label">Visitas</div>
                        <div class="metric-value">{item['visitas']}</div>
                    </div>
                    <div class="metric-box">
                        <div class="metric-label">Suscriptores</div>
                        <div class="metric-value">{item['suscriptores']}</div>
                    </div>
                    <div style="text-align: right;">
                        <a href="{item['url']}" target="_blank" class="btn-yt">▶️ Ver en YouTube</a>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --- INTERFAZ PRINCIPAL ---
st.title("🚀 YouTube Outlier Finder")
st.write(
    "Descubre ideas de vídeo virales localizando contenidos que superan con creces la audiencia habitual de sus canales."
)

# --- BARRA LATERAL (PRO ACCESS & LEGAL) ---
with st.sidebar:
    st.header("🔑 Licencia PRO")
    user_license = st.text_input(
        "Clave de licencia:", type="password", placeholder="Paste key here"
    )

    is_pro = False
    if user_license:
        with st.spinner("Validando..."):
            is_pro = validate_license_key(user_license)
            if is_pro:
                st.success("✅ Licencia PRO Activa")
            else:
                st.error("❌ Licencia no válida")
    else:
        st.info("ℹ️ **Modo Demo:** Muestra 1 resultado.")
        st.markdown(
            "[👉 **Obtener clave PRO**](https://tu-tienda.lemonsqueezy.com)"
        )

    st.divider()

    # Requisitos legales exigidos por la API de YouTube
    st.caption("Powered by YouTube Data API")
    st.markdown(
        """
        <div style="font-size: 11px; color: #888;">
            <a href="https://www.youtube.com/t/terms" target="_blank" style="color: #888;">Términos de Servicio de YouTube</a> | 
            <a href="http://www.google.com/policies/privacy" target="_blank" style="color: #888;">Política de Privacidad de Google</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

# --- FORMULARIO DE BÚSQUEDA ---
col_q, col_s = st.columns([2, 1])

with col_q:
    query = st.text_input(
        "🔍 Nicho o palabra clave:",
        placeholder="Ej. huerto urbano, finanzas personales, espresso...",
    )

with col_s:
    sort_option = st.selectbox(
        "📊 Ordenar por:",
        options=["Relevancia", "Más reproducidos", "Más recientes"],
    )

max_results = st.slider(
    "Profundidad de escaneo (vídeos):",
    min_value=10,
    max_value=50,
    value=30,
    step=5,
    disabled=not is_pro,
)

sort_mapping = {
    "Relevancia": "relevance",
    "Más reproducidos": "viewCount",
    "Más recientes": "date",
}

# --- EJECUCIÓN ---
if st.button("Buscar Vídeos Outliers", type="primary", use_container_width=True):
    if not YOUTUBE_API_KEY:
        st.error(
            "⚠️ Configura YOUTUBE_API_KEY en los Secrets de Streamlit Cloud."
        )
    elif not query:
        st.warning("⚠️ Escribe un término para buscar.")
    else:
        with st.spinner("Escaneando YouTube en busca de outliers..."):
            try:
                search_limit = max_results if is_pro else 10
                outliers = fetch_youtube_outliers(
                    YOUTUBE_API_KEY,
                    query,
                    sort_mapping[sort_option],
                    search_limit,
                )

                if not is_pro and outliers:
                    outliers = outliers[:1]

                if outliers:
                    st.divider()
                    if is_pro:
                        st.success(
                            f"🔥 ¡Encontrados {len(outliers)} vídeos outliers!"
                        )
                    else:
                        st.warning(
                            "🔒 **Modo Demo:** Mostrando solo el 1.er resultado. Activa tu licencia PRO para ver el resto."
                        )

                    # Mostrar resultados maquetados en tarjetas
                    render_outliers(outliers)
                else:
                    st.info(
                        "No se han encontrado vídeos con más visitas que suscriptores para esta consulta."
                    )

            except Exception as e:
                st.error(f"Error en la consulta: {e}")
