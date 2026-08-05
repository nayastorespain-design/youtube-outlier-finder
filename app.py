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
    layout="wide"
)

# Header principal en el Dashboard
st.markdown("""
    <h1 style='text-align: center; margin-bottom: 0;'>⚡ APEX OUTLIERS</h1>
    <p style='text-align: center; color: #888; font-size: 1.1rem; margin-top: 4px;'>
        Buscador de vídeos con rendimiento excepcional para YouTube
    </p>
    <hr style='border: 0; height: 1px; background: #333; margin-bottom: 30px;'>
""", unsafe_allow_html=True)

# --- ESTILOS CSS REFINADOS ---
st.markdown(
    """
    <style>
    .main {
        background-color: #0d1117;
    }
    
    /* Header principal */
    .app-header {
        text-align: center;
        padding: 1.5rem 0 2rem 0;
    }
    .app-title {
        font-size: 2.4rem !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #FFFFFF 0%, #A5B4FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.4rem;
    }
    .app-subtitle {
        color: #8b949e;
        font-size: 1rem;
        font-weight: 400;
        max-width: 620px;
        margin: 0 auto;
    }

    /* Tarjetas estilo SaaS moderno */
    .outlier-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 16px;
        transition: border-color 0.2s ease;
    }
    .outlier-card:hover {
        border-color: #58a6ff;
    }
    .thumbnail-img {
        width: 100%;
        border-radius: 8px;
        object-fit: cover;
        aspect-ratio: 16/9;
        display: block;
    }
    .outlier-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #f0f6fc !important;
        text-decoration: none;
        line-height: 1.35;
    }
    .outlier-title:hover {
        color: #58a6ff !important;
    }
    .outlier-meta {
        color: #8b949e;
        font-size: 0.85rem;
        margin-top: 6px;
        display: flex;
        gap: 12px;
        align-items: center;
    }
    
    /* Badge Outlier Ratio */
    .badge-outlier {
        background: rgba(248, 81, 73, 0.15);
        color: #ff7b72;
        border: 1px solid rgba(248, 81, 73, 0.4);
        font-weight: 800;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.95rem;
        display: inline-block;
        text-align: center;
    }

    /* Caja de métricas */
    .metric-container {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 10px;
        margin-top: 14px;
    }
    .metric-box {
        background: #0d1117;
        border-radius: 6px;
        padding: 8px 12px;
        border: 1px solid #21262d;
    }
    .metric-label {
        font-size: 0.7rem;
        color: #8b949e;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .metric-value {
        font-size: 1.05rem;
        font-weight: 700;
        color: #c9d1d9;
        margin-top: 2px;
    }

    /* Botón YouTube */
    .btn-yt {
        display: flex;
        align-items: center;
        justify-content: center;
        background-color: #21262d;
        color: #c9d1d9 !important;
        border: 1px solid #30363d;
        padding: 9px 16px;
        border-radius: 6px;
        text-decoration: none;
        font-weight: 600;
        font-size: 0.85rem;
        transition: all 0.2s ease;
        width: 100%;
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

    # Reintento automático en caso de parpadeos de servidor de Google (503, 500)
    def execute_with_retry(request, max_retries=3):
        for attempt in range(max_retries):
            try:
                return request.execute()
            except HttpError as e:
                if e.resp.status in [500, 502, 503, 504] and attempt < max_retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                else:
                    raise e

    def chunk_list(data, size=50):
        for i in range(0, len(data), size):
            yield data[i : i + size]

    # 1. Búsqueda de vídeos CON PAGINACIÓN
    # La API de YouTube solo permite 50 resultados por página, así que
    # para obtener más (hasta 500) hay que encadenar varias llamadas
    # usando el pageToken que devuelve cada respuesta.
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

    # 2. Detalles de vídeos (visitas y duración), en lotes de 50 IDs
    # (límite máximo permitido por la API en una sola llamada)
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

    # 3. Detalles de canales (suscriptores), también en lotes de 50 IDs
    subs_map = {}
    for id_batch in chunk_list(channel_ids, 50):
        c_req = youtube.channels().list(
            part="statistics", id=",".join(id_batch)
        )
        c_res = execute_with_retry(c_req)

        subs_map.update(
            {
                c_item["id"]: int(c_item["statistics"].get("subscriberCount", 0))
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

        # Filtro de Shorts (vídeos de 60 segundos o menos)
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

        # Condición para Outliers válidos
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
                    <div>
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
        <div class="app-title">YouTube Outlier Finder</div>
        <div class="app-subtitle">Localiza vídeos de alto rendimiento que superan exponencialmente la audiencia base de sus canales.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- PANEL DE CONTROL ---
with st.container(border=True):
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
            help="Cantidad de vídeos a analizar. Valores altos consumen más cuota de la API "
            "(cada bloque de 50 vídeos gasta ~100 unidades de cuota diaria).",
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
        "🔍 Buscar Outliers", type="primary", use_container_width=True
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
        with st.spinner("Escaneando vídeos y filtrando métricas..."):
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
            expected_cols = [
                "titulo",
                "canal",
                "fecha",
                "visitas_num",
                "suscriptores_num",
                "ratio",
                "url",
                "thumbnail",
            ]
            available_cols = [
                col for col in expected_cols if col in df_export.columns
            ]

            df_csv = df_export[available_cols].rename(
                columns={
                    "titulo": "Título",
                    "canal": "Canal",
                    "fecha": "Fecha Publicación",
                    "visitas_num": "Visitas",
                    "suscriptores_num": "Suscriptores",
                    "ratio": "Multiplicador",
                    "url": "Enlace",
                    "thumbnail": "URL Miniatura",
                }
            )

            csv_bytes = df_csv.to_csv(index=False).encode("utf-8")
            clean_query = (
                "".join(
                    c
                    for c in st.session_state.get("search_query", "outliers")
                    if c.isalnum() or c in (" ", "_")
                )
                .rstrip()
                .replace(" ", "_")
            )

            st.download_button(
                label="📥 Exportar CSV",
                data=csv_bytes,
                file_name=f"outliers_{clean_query}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        render_outliers(outliers)

# --- FOOTER ---
st.markdown(
    """
    <hr style="border: none; border-top: 1px solid #21262d; margin-top: 50px;">
    <div style="text-align: center; font-size: 12px; color: #8b949e; padding-bottom: 20px;">
        YouTube Outlier Finder • Powered by YouTube Data API v3<br>
        <a href="https://www.youtube.com/t/terms" target="_blank" style="color: #58a6ff;">Términos de YouTube</a> | 
        <a href="http://www.google.com/policies/privacy" target="_blank" style="color: #58a6ff;">Política de Privacidad</a>
    </div>
    """,
    unsafe_allow_html=True,
)
