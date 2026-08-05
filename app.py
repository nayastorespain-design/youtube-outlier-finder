from datetime import datetime, timedelta, timezone
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

# Clave API desde Secrets
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY")

# --- CONSULTA A LA API (OPTIMIZADA + FILTRO TEMPORAL) ---
@st.cache_data(ttl=43200, show_spinner=False)
def fetch_youtube_outliers(api_key, query, order, days_back, max_results):
    youtube = build("youtube", "v3", developerKey=api_key)

    # Calcular la fecha límite dinámica
    published_after = (
        datetime.now(timezone.utc) - timedelta(days=days_back)
    ).isoformat()

    # 1. Búsqueda filtrada por fecha
    search_res = (
        youtube.search()
        .list(
            q=query,
            part="snippet",
            type="video",
            order=order,
            publishedAfter=published_after,
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
                    "visitas_num": views,
                    "suscriptores_num": subs,
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

# --- BARRA LATERAL (LEGAL) ---
with st.sidebar:
    st.header("⚙️ Información")
    st.success("⚡ Modo completo activado")
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
col_q, col_s, col_t = st.columns([2, 1, 1])

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

with col_t:
    time_option = st.selectbox(
        "📅 Antigüedad máxima:",
        options=[
            "Último mes",
            "Últimos 3 meses",
            "Últimos 6 meses",
            "Último año",
        ],
        index=3,
    )

max_results = st.slider(
    "Profundidad de escaneo (vídeos):",
    min_value=10,
    max_value=50,
    value=30,
    step=5,
)

sort_mapping = {
    "Relevancia": "relevance",
    "Más reproducidos": "viewCount",
    "Más recientes": "date",
}

time_mapping = {
    "Último mes": 30,
    "Últimos 3 meses": 90,
    "Últimos 6 meses": 180,
    "Último año": 365,
}

# --- EJECUCIÓN ---
if st.button("Buscar Vídeos Outliers", type="primary", use_container_width=True):
    if not YOUTUBE_API_KEY:
        st.error("⚠️ Configura YOUTUBE_API_KEY en los Secrets de Streamlit Cloud.")
    elif not query:
        st.warning("⚠️ Escribe un término para buscar.")
    else:
        with st.spinner(f"Escaneando YouTube ({time_option.lower()}) en busca de outliers..."):
            try:
                days_back = time_mapping[time_option]

                outliers = fetch_youtube_outliers(
                    YOUTUBE_API_KEY,
                    query,
                    sort_mapping[sort_option],
                    days_back,
                    max_results,
                )

                if outliers:
                    st.session_state["outliers_data"] = outliers
                    st.session_state["search_query"] = query
                else:
                    st.session_state.pop("outliers_data", None)
                    st.info("No se han encontrado vídeos para los criterios seleccionados.")

            except Exception as e:
                st.error(f"Error en la consulta: {e}")

# --- MOSTRAR RESULTADOS Y BOTÓN DE DESCARGA CSV ---
if "outliers_data" in st.session_state and st.session_state["outliers_data"]:
    outliers = st.session_state["outliers_data"]
    st.divider()

    col_res_header, col_csv = st.columns([2, 1])

    with col_res_header:
        st.success(f"🔥 ¡Encontrados {len(outliers)} vídeos outliers!")

    with col_csv:
        df_export = pd.DataFrame(outliers)
        df_csv = df_export[
            ["titulo", "canal", "visitas_num", "suscriptores_num", "ratio", "url"]
        ].rename(
            columns={
                "titulo": "Título",
                "canal": "Canal",
                "visitas_num": "Visitas",
                "suscriptores_num": "Suscriptores",
                "ratio": "Multiplicador Outlier",
                "url": "Enlace YouTube",
            }
        )
        csv_bytes = df_csv.to_csv(index=False).encode("utf-8")
        clean_query = "".join(
            c for c in st.session_state.get("search_query", "outliers")
            if c.isalnum() or c in (" ", "_")
        ).rstrip().replace(" ", "_")

        st.download_button(
            label="📥 Descargar resultados en CSV",
            data=csv_bytes,
            file_name=f"outliers_{clean_query}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    render_outliers(outliers)
