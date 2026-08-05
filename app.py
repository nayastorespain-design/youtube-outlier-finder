from datetime import datetime, timedelta, timezone
import re
import time
import pandas as pd
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Apex Outliers | YouTube Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- ESTILOS CSS PREMIUM (GLASSMORPHISM & MODERN SAAS) ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Fondo principal */
    .stApp {
        background: radial-gradient(circle at 50% -20%, #1e1b4b 0%, #06080f 60%, #030407 100%);
        color: #f1f5f9;
    }

    /* Header principal */
    .app-header {
        text-align: center;
        padding: 2.5rem 1rem 1.5rem 1rem;
    }
    .app-title {
        font-size: 3rem !important;
        font-weight: 900 !important;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #ffffff 0%, #a5b4fc 50%, #6366f1 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .app-subtitle {
        color: #94a3b8;
        font-size: 1.1rem;
        font-weight: 400;
        max-width: 640px;
        margin: 0 auto;
        line-height: 1.5;
    }
    .app-badge {
        display: inline-block;
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.3);
        color: #a5b4fc;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 12px;
    }

    /* Contenedor del Panel de Control */
    [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] > div {
        background: rgba(15, 23, 42, 0.65) !important;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(99, 102, 241, 0.18) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35) !important;
    }

    /* ETIQUETAS DE TEXTO EN BLANCO PURO */
    [data-testid="stWidgetLabel"] p, label, .stSlider label {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        letter-spacing: 0.01em !important;
    }

    /* BOTÓN PRIMARIO ENTERPRISE */
    .stButton > button {
        background-color: #4f46e5 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        border: 1px solid #6366f1 !important;
        border-radius: 8px !important;
        padding: 14px 28px !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.3) !important;
        letter-spacing: 0.03em !important;
        text-transform: uppercase !important;
    }
    .stButton > button:hover {
        background-color: #4338ca !important;
        border-color: #818cf8 !important;
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.45) !important;
        transform: translateY(-2px) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
        background-color: #3730a3 !important;
    }

    /* Estilo específico para el botón de Exportar CSV */
    .stDownloadButton > button {
        background: rgba(30, 41, 59, 0.85) !important;
        color: #a5b4fc !important;
        border: 1px solid rgba(99, 102, 241, 0.4) !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
        width: 100% !important;
    }
    .stDownloadButton > button:hover {
        background: rgba(99, 102, 241, 0.25) !important;
        color: #ffffff !important;
        border-color: #6366f1 !important;
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4) !important;
        transform: translateY(-1px) !important;
    }

    /* Tarjetas de Outliers */
    .outlier-card {
        background: rgba(15, 23, 42, 0.7);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(99, 102, 241, 0.15);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 18px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
    }
    .outlier-card:hover {
        border-color: rgba(99, 102, 241, 0.45);
        transform: translateY(-3px);
        box-shadow: 0 12px 32px rgba(99, 102, 241, 0.2);
    }
    .thumbnail-container {
        position: relative;
        overflow: hidden;
        border-radius: 10px;
        aspect-ratio: 16/9;
    }
    .thumbnail-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
        transition: transform 0.3s ease;
    }
    .outlier-card:hover .thumbnail-img {
        transform: scale(1.05);
    }

    .outlier-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f8fafc !important;
        text-decoration: none;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        transition: color 0.2s ease;
    }
    .outlier-title:hover {
        color: #a5b4fc !important;
    }

    .outlier-meta {
        color: #94a3b8;
        font-size: 0.85rem;
        margin-top: 8px;
        display: flex;
        gap: 16px;
        align-items: center;
        font-weight: 500;
    }
    
    /* Badge Outlier Ratio */
    .badge-outlier {
        background: rgba(244, 63, 94, 0.12);
        color: #fb7185;
        border: 1px solid rgba(244, 63, 94, 0.35);
        font-weight: 800;
        padding: 8px 18px;
        border-radius: 20px;
        font-size: 1.05rem;
        display: inline-block;
        text-align: center;
        box-shadow: 0 0 15px rgba(244, 63, 94, 0.15);
    }

    /* Caja de métricas */
    .metric-container {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 12px;
        margin-top: 14px;
    }
    .metric-box {
        background: rgba(6, 8, 15, 0.6);
        border-radius: 8px;
        padding: 10px 14px;
        border: 1px solid rgba(255, 255, 255, 0.06);
    }
    .metric-label {
        font-size: 0.68rem;
        color: #64748b;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.06em;
    }
    .metric-value {
        font-size: 1.1rem;
        font-weight: 800;
        color: #f1f5f9;
        margin-top: 2px;
    }

    /* Botón YouTube */
    .btn-yt {
        display: flex;
        align-items: center;
        justify-content: center;
        background: rgba(30, 41, 59, 0.8);
        color: #f1f5f9 !important;
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 10px 18px;
        border-radius: 8px;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.88rem;
        transition: all 0.2s ease;
        width: 100%;
        text-align: center;
    }
    .btn-yt:hover {
        background-color: #FF0000;
        color: #FFFFFF !important;
        border-color: #FF0000;
        box-shadow: 0 4px 15px rgba(255, 0, 0, 0.3);
    }

    /* Ocultar elementos innecesarios de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# Clave API desde Secrets
YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY")


# Helper para convertir la duración en formato ISO 8601 a segundos
def parse_duration_to_seconds(duration_str):
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


# --- CONSULTA A LA API (CON RESILIENCIA 503, PAGINACIÓN Y FILTRADO PRECISO DE SHORTS) ---
@st.cache_data(ttl=43200, show_spinner=False)
def fetch_youtube_outliers(
    api_key, query, order, days_back, max_results, min_views=1000
):
    youtube = build("youtube", "v3", developerKey=api_key)

    published_after = (
        datetime.now(timezone.utc) - timedelta(days=days_back)
    ).isoformat()

    def execute_with_retry(request, max_retries=3):
        for attempt in range(max_retries):
            try:
                return request.execute()
            except HttpError as e:
                if (
                    e.resp.status in [500, 502, 503, 504]
                    and attempt < max_retries - 1
                ):
                    time.sleep(1.5 * (attempt + 1))
                else:
                    raise e

    def chunk_list(data, size=50):
        for i in range(0, len(data), size):
            yield data[i : i + size]

    items = []
    page_token = None
    while len(items) < max_results:
        remaining = max_results - len(items)
        search_req = youtube.search().list(
            q=query,
            part="snippet",
            type="video",
            videoDuration="any",
            order=order,
            publishedAfter=published_after,
            maxResults=min(50, remaining),
            pageToken=page_token,
        )
        search_res = execute_with_retry(search_req)

        page_items = search_res.get("items", [])
        items.extend(page_items)

        page_token = search_res.get("nextPageToken")
        if not page_token or not page_items:
            break

    if not items:
        return []

    video_ids = [item["id"]["videoId"] for item in items]
    channel_ids = list(set(item["snippet"]["channelId"] for item in items))

    video_details = {}
    for id_batch in chunk_list(video_ids, 50):
        v_req = youtube.videos().list(
            part="statistics,contentDetails", id=",".join(id_batch)
        )
        v_res = execute_with_retry(v_req)

        for v_item in v_res.get("items", []):
            v_id = v_item["id"]
            v_views = int(v_item["statistics"].get("viewCount", 0))
            v_duration_raw = v_item.get("contentDetails", {}).get(
                "duration", "PT0S"
            )
            v_seconds = parse_duration_to_seconds(v_duration_raw)

            video_details[v_id] = {"views": v_views, "seconds": v_seconds}

    subs_map = {}
    for id_batch in chunk_list(channel_ids, 50):
        c_req = youtube.channels().list(
            part="statistics", id=",".join(id_batch)
        )
        c_res = execute_with_retry(c_req)

        subs_map.update(
            {
                c_item["id"]: int(
                    c_item["statistics"].get("subscriberCount", 0)
                )
                for c_item in c_res.get("items", [])
            }
        )

    outliers = []
    for item in items:
        vid_id = item["id"]["videoId"]
        chan_id = item["snippet"]["channelId"]

        v_info = video_details.get(vid_id, {"views": 0, "seconds": 0})
        views = v_info["views"]
        duration_sec = v_info["seconds"]
        subs = subs_map.get(chan_id, 0)

        # Anti-Shorts (Duración superior a 60s)
        if duration_sec <= 60:
            continue

        pub_raw = item["snippet"]["publishedAt"]
        pub_date = datetime.fromisoformat(
            pub_raw.replace("Z", "+00:00")
        ).strftime("%d %b %Y")

        thumbnails = item["snippet"].get("thumbnails", {})
        thumb_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url", "")
        )

        if views > subs and subs > 0 and views >= min_views:
            ratio = round(views / subs, 1)
            outliers.append(
                {
                    "titulo": item["snippet"]["title"],
                    "canal": item["snippet"]["channelTitle"],
                    "fecha": pub_date,
                    "thumbnail": thumb_url,
                    "visitas_num": views,
                    "suscriptores_num": subs,
                    "visitas": f"{views:,}",
                    "suscriptores": f"{subs:,}",
                    "ratio": f"{ratio}x",
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                }
            )

    return outliers


# --- RENDERIZADO DE RESULTADOS ---
def render_outliers(outliers):
    for item in outliers:
        st.markdown(
            f"""
            <div class="outlier-card">
                <div style="display: grid; grid-template-columns: 240px 1fr 180px; gap: 20px; align-items: center;">
                    <!-- Columna 1: Thumbnail -->
                    <div class="thumbnail-container">
                        <a href="{item['url']}" target="_blank">
                            <img src="{item['thumbnail']}" class="thumbnail-img" alt="Thumbnail">
                        </a>
                    </div>
                    <!-- Columna 2: Info Principal -->
                    <div>
                        <a href="{item['url']}" target="_blank" class="outlier-title">{item['titulo']}</a>
                        <div class="outlier-meta">
                            <span>📺 {item['canal']}</span>
                            <span>📅 {item['fecha']}</span>
                        </div>
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
                    </div>
                    <!-- Columna 3: Ratio y Acción -->
                    <div style="display: flex; flex-direction: column; gap: 14px; align-items: stretch; text-align: center;">
                        <div>
                            <span class="badge-outlier">🔥 {item['ratio']}</span>
                        </div>
                        <a href="{item['url']}" target="_blank" class="btn-yt">▶ Ver en YouTube</a>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# --- HEADER ---
st.markdown(
    """
    <div class="app-header">
        <div class="app-badge">⚡ YOUTUBE INTELLIGENCE</div>
        <div class="app-title">Apex Outliers</div>
        <div class="app-subtitle">Localiza vídeos de alto rendimiento que superan exponencialmente la audiencia base de sus canales.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- PANEL DE CONTROL ---
with st.container():
    col_q, col_s, col_t = st.columns([2.5, 1, 1])

    with col_q:
        query = st.text_input(
            "Palabra clave o Nicho",
            placeholder="Ej. huerto urbano, riego tomate, finanzas...",
        )

    with col_s:
        sort_option = st.selectbox(
            "Ordenar por",
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

    col_slider, col_min_views = st.columns([2, 1])
    with col_slider:
        max_results = st.select_slider(
            "Muestreo de búsqueda",
            options=[10, 20, 30, 50, 100, 150, 200, 300, 500],
            value=100,
            help="Cantidad de vídeos a analizar. Valores altos consumen más cuota de la API.",
        )
    with col_min_views:
        min_views_input = st.number_input(
            "Mínimo de visitas",
            min_value=100,
            value=1000,
            step=500,
            help="Filtra vídeos irrelevantes de canales recién creados.",
        )

    btn_search = st.button(
        "EJECUTAR ANÁLISIS DE OUTLIERS", type="primary", use_container_width=True
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

# --- EJECUCIÓN DE BÚSQUEDA ---
if btn_search:
    if not YOUTUBE_API_KEY:
        st.error(
            "⚠️ Configura YOUTUBE_API_KEY en los Secrets de Streamlit Cloud."
        )
    elif not query:
        st.warning("⚠️ Introduce una palabra clave.")
    else:
        with st.spinner("Analizando métricas del canal y vídeos..."):
            try:
                days_back = time_mapping[time_option]
                outliers = fetch_youtube_outliers(
                    YOUTUBE_API_KEY,
                    query,
                    sort_mapping[sort_option],
                    days_back,
                    max_results,
                    min_views=min_views_input,
                )

                if outliers:
                    st.session_state["outliers_data"] = outliers
                    st.session_state["search_query"] = query
                else:
                    st.session_state.pop("outliers_data", None)
                    st.info(
                        "No se encontraron outliers con los filtros actuales."
                    )

            except Exception as e:
                st.error(f"Error en la consulta: {e}")

# --- MOSTRAR RESULTADOS Y EXPORTACIÓN ---
if "outliers_data" in st.session_state:
    outliers = st.session_state["outliers_data"]

    if outliers and len(outliers) > 0:
        st.markdown("<br>", unsafe_allow_html=True)
        col_info, col_export = st.columns([3, 1], vertical_alignment="center")

        with col_info:
            st.markdown(f"### ⚡ {len(outliers)} Outliers detectados")

        with col_export:
            df_export = pd.DataFrame(outliers)

            column_mapping = {
                "titulo": "Título",
                "canal": "Canal",
                "fecha": "Fecha Publicación",
                "visitas_num": "Visitas",
                "suscriptores_num": "Suscriptores",
                "ratio": "Multiplicador",
                "url": "Enlace",
                "thumbnail": "URL Miniatura",
            }

            valid_cols = [
                col for col in column_mapping.keys() if col in df_export.columns
            ]
            df_csv = df_export[valid_cols].rename(columns=column_mapping)

            # Usamos utf-8-sig para compatibilidad total con acentos en Excel
            csv_data = df_csv.to_csv(index=False).encode("utf-8-sig")

            clean_query = (
                "".join(
                    c
                    for c in st.session_state.get("search_query", "outliers")
                    if c.isalnum() or c in (" ", "_")
                )
                .strip()
                .replace(" ", "_")
            )

            st.download_button(
                label="📥 Exportar CSV",
                data=csv_data,
                file_name=f"outliers_{clean_query}.csv",
                mime="text/csv",
                use_container_width=True,
                key="btn_download_csv",
            )

        render_outliers(outliers)

# --- FOOTER ---
st.markdown(
    """
    <hr style="border: none; border-top: 1px solid rgba(255, 255, 255, 0.1); margin-top: 50px;">
    <div style="text-align: center; font-size: 12px; color: #94a3b8; padding-bottom: 20px;">
        Apex Outliers • Powered by YouTube Data API v3<br>
        <a href="https://www.youtube.com/t/terms" target="_blank" style="color: #818cf8; text-decoration: none;">Términos de YouTube</a> | 
        <a href="http://www.google.com/policies/privacy" target="_blank" style="color: #818cf8; text-decoration: none;">Política de Privacidad</a>
    </div>
    """,
    unsafe_allow_html=True,
)
