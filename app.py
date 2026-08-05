from datetime import datetime, timedelta, timezone
import pandas as pd
import requests
import streamlit as st
from googleapiclient.discovery import build

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="YouTube Outlier Finder | SaaS Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- ESTILOS CSS PROFESIONALES (CUSTOM SAAS UI) ---
st.markdown(
    """
    <style>
    /* Estilos generales de la app */
    .main {
        background-color: #0e1117;
    }
    
    /* Header principal */
    .app-header {
        text-align: center;
        padding: 1rem 0 2rem 0;
    }
    .app-title {
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #FFFFFF 0%, #A5B4FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .app-subtitle {
        color: #94A3B8;
        font-size: 1.1rem;
        font-weight: 400;
        max-width: 600px;
        margin: 0 auto;
    }

    /* Targetas de Outliers */
    .outlier-card {
        background: #161922;
        border: 1px solid #262B38;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 18px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .outlier-card:hover {
        border-color: #3B82F6;
    }
    .outlier-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #F8FAFC !important;
        text-decoration: none;
        line-height: 1.4;
    }
    .outlier-title:hover {
        color: #60A5FA !important;
    }
    .outlier-channel {
        color: #64748B;
        font-size: 0.875rem;
        margin-top: 6px;
        font-weight: 500;
    }
    
    /* Badge Outlier Ratio */
    .badge-outlier {
        background: rgba(239, 68, 68, 0.15);
        color: #EF4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
        font-weight: 700;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.9rem;
        display: inline-flex;
        align-items: center;
        gap: 4px;
    }

    /* Caja de métricas */
    .metric-container {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin-top: 16px;
    }
    .metric-box {
        background: #1E2330;
        border-radius: 8px;
        padding: 10px 14px;
        border: 1px solid #2A3042;
    }
    .metric-label {
        font-size: 0.75rem;
        color: #64748B;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.1rem;
        font-weight: 700;
        color: #F1F5F9;
        margin-top: 2px;
    }

    /* Botón directo a YouTube */
    .btn-yt {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: #222734;
        color: #E2E8F0 !important;
        border: 1px solid #333A4D;
        padding: 10px 20px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.875rem;
        transition: all 0.2s ease;
        width: 100%;
        margin-top: 16px;
    }
    .btn-yt:hover {
        background-color: #FF0000;
        color: #FFFFFF !important;
        border-color: #FF0000;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Clave API desde Secrets
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY")

# --- CONSULTA A LA API ---
@st.cache_data(ttl=43200, show_spinner=False)
def fetch_youtube_outliers(api_key, query, order, days_back, max_results):
    youtube = build("youtube", "v3", developerKey=api_key)

    published_after = (
        datetime.now(timezone.utc) - timedelta(days=days_back)
    ).isoformat()

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

    v_res = (
        youtube.videos()
        .list(part="statistics", id=",".join(video_ids))
        .execute()
    )
    views_map = {
        v_item["id"]: int(v_item["statistics"].get("viewCount", 0))
        for v_item in v_res.get("items", [])
    }

    c_res = (
        youtube.channels()
        .list(part="statistics", id=",".join(set(channel_ids)))
        .execute()
    )
    subs_map = {
        c_item["id"]: int(c_item["statistics"].get("subscriberCount", 0))
        for c_item in c_res.get("items", [])
    }

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
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;">
                    <div style="flex-grow: 1;">
                        <a href="{item['url']}" target="_blank" class="outlier-title">{item['titulo']}</a>
                        <div class="outlier-channel">📺 {item['canal']}</div>
                    </div>
                    <div>
                        <span class="badge-outlier">🔥 {item['ratio']}</span>
                    </div>
                </div>
                <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 16px; align-items: center;">
                    <div class="metric-container">
                        <div class="metric-box">
                            <div class="metric-label">Visitas</div>
                            <div class="metric-value">{item['visitas']}</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-label">Suscriptores</div>
                            <div class="metric-value">{item['suscriptores']}</div>
                        </div>
                    </div>
                    <div>
                        <a href="{item['url']}" target="_blank" class="btn-yt">▶ Ver en YouTube</a>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --- HEADER PRINCIPAL ---
st.markdown(
    """
    <div class="app-header">
        <div class="app-title">YouTube Outlier Finder</div>
        <div class="app-subtitle">Encuentra ideas de contenido analizando vídeos de alto rendimiento que han superado la audiencia habitual de sus canales.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- PANEL DE CONTROL DE BÚSQUEDA ---
with st.container(border=True):
    col_q, col_s, col_t = st.columns([2.5, 1, 1])

    with col_q:
        query = st.text_input(
            "Palabra clave o Nicho",
            placeholder="Ej. huerto urbano, finanzas, espresso...",
        )

    with col_s:
        sort_option = st.selectbox(
            "Ordenar resultados",
            options=["Relevancia", "Más reproducidos", "Más recientes"],
        )

    with col_t:
        time_option = st.selectbox(
            "Antigüedad máxima",
            options=[
                "Último mes",
                "Últimos 3 meses",
                "Últimos 6 meses",
                "Último año",
            ],
            index=3,
        )

    max_results = st.select_slider(
        "Muestreo de vídeos analizados",
        options=[10, 20, 30, 40, 50],
        value=30,
        help="A mayor número, más precisión pero consumirá más cuota de búsqueda.",
    )

    btn_search = st.button("🔍 Buscar Outliers", type="primary", use_container_width=True)

# Mapeos de entrada
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
if btn_search:
    if not YOUTUBE_API_KEY:
        st.error("⚠️ Configura YOUTUBE_API_KEY en los Secrets de Streamlit Cloud.")
    elif not query:
        st.warning("⚠️ Introduce una palabra clave para iniciar la búsqueda.")
    else:
        with st.spinner("Escaneando y calculando métricas de canales..."):
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
                    st.info("No se encontraron vídeos que cumplan el criterio de outlier para este nicho.")

            except Exception as e:
                st.error(f"Error procesando la solicitud: {e}")

# --- RESULTADOS Y DESCARGA ---
if "outliers_data" in st.session_state and st.session_state["outliers_data"]:
    outliers = st.session_state["outliers_data"]
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_info, col_export = st.columns([3, 1], vertical_alignment="center")

    with col_info:
        st.markdown(f"### ⚡ {len(outliers)} Outliers detectados")

    with col_export:
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
            label="📥 Exportar CSV",
            data=csv_bytes,
            file_name=f"outliers_{clean_query}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    render_outliers(outliers)

# --- FOOTER DISCRETO ---
st.markdown(
    """
    <hr style="border: none; border-top: 1px solid #1E2330; margin-top: 50px;">
    <div style="text-align: center; font-size: 12px; color: #475569; padding-bottom: 20px;">
        YouTube Outlier Finder • Powered by YouTube Data API v3<br>
        <a href="https://www.youtube.com/t/terms" target="_blank" style="color: #64748B;">Términos de YouTube</a> | 
        <a href="http://www.google.com/policies/privacy" target="_blank" style="color: #64748B;">Política de Privacidad</a>
    </div>
    """,
    unsafe_allow_html=True,
)
