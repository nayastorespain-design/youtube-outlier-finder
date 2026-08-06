import re
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from supabase import Client, create_client

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="U Smart Search",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 2. CONEXIÓN CON SUPABASE ---
SUPABASE_URL = st.secrets["supabase"]["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["supabase"]["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- 3. FUNCIONES DE SUPABASE (CACHÉ Y PLANES) ---
def get_cached_search(query: str):
    """Busca si los resultados de YouTube ya están guardados en Supabase."""
    query_clean = query.strip().lower()
    res = (
        supabase.table("search_cache")
        .select("results_json")
        .eq("query_text", query_clean)
        .execute()
    )
    if res.data:
        return res.data[0]["results_json"]
    return None


def save_search_to_cache(query: str, results: list):
    """Guarda los resultados de una nueva búsqueda de YouTube en Supabase."""
    query_clean = query.strip().lower()
    supabase.table("search_cache").upsert(
        {"query_text": query_clean, "results_json": results}
    ).execute()


def get_or_create_user_profile(email: str) -> str:
    """Busca el email en Supabase. Si no existe, lo guarda como 'free'."""
    if not email or not email.strip():
        return "free"

    email_clean = email.strip().lower()
    try:
        # 1. Consultar el plan actual
        res = (
            supabase.table("profiles")
            .select("plan")
            .eq("email", email_clean)
            .execute()
        )

        if res.data and len(res.data) > 0:
            return res.data[0].get("plan", "free")
        else:
            # 2. Si es la primera vez que entra, registrar el email
            supabase.table("profiles").insert(
                {"email": email_clean, "plan": "free"}
            ).execute()
            st.sidebar.success(f"✅ ¡Bienvenido! Registrado: {email_clean}")
            return "free"

    except Exception as e:
        st.sidebar.error(f"❌ Error Supabase: {e}")
        return "free"

# --- CONFIGURACIÓN DE PAGO ---
PAYMENT_URL = "https://tu-pagina-de-pago.com"  # Reemplazar con tu enlace de pago

# --- ESTILOS CSS PREMIUM ---
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at 50% -20%, #1e1b4b 0%, #06080f 60%, #030407 100%);
        color: #f1f5f9;
    }

    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.95) !important;
        border-right: 1px solid rgba(99, 102, 241, 0.2) !important;
    }

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

    [data-testid="stForm"], [data-testid="stVerticalBlockBorderWrapper"] > div {
        background: rgba(15, 23, 42, 0.65) !important;
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(99, 102, 241, 0.18) !important;
        border-radius: 16px !important;
        padding: 24px !important;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35) !important;
    }

    [data-testid="stWidgetLabel"] p, label, .stSlider label {
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
    }

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

    .stDownloadButton > button {
        background: rgba(30, 41, 59, 0.85) !important;
        color: #a5b4fc !important;
        border: 1px solid rgba(99, 102, 241, 0.4) !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }

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
        background-color: #0f172a;
    }
    .thumbnail-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        display: block;
        transition: transform 0.3s ease;
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
    }

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
    }
    .metric-value {
        font-size: 1.1rem;
        font-weight: 800;
        color: #f1f5f9;
        margin-top: 2px;
    }

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
        width: 100%;
        text-align: center;
    }
    .btn-yt:hover {
        background-color: #FF0000;
        color: #FFFFFF !important;
    }

    /* Paywall */
    .locked-container {
        position: relative;
        margin-top: 10px;
    }
    .blurred-item {
        filter: blur(8px);
        opacity: 0.45;
        user-select: none;
        pointer-events: none;
    }
    .paywall-overlay {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: linear-gradient(180deg, rgba(6, 8, 15, 0.1) 0%, rgba(6, 8, 15, 0.85) 30%, rgba(6, 8, 15, 0.98) 100%);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 20;
        padding: 40px 20px;
        border-radius: 16px;
    }
    .paywall-card {
        background: rgba(15, 23, 42, 0.95);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(99, 102, 241, 0.4);
        border-radius: 20px;
        padding: 36px 40px;
        text-align: center;
        max-width: 520px;
        box-shadow: 0 20px 50px rgba(0, 0, 0, 0.6);
    }
    .paywall-icon { font-size: 2.5rem; margin-bottom: 12px; }
    .paywall-title { font-size: 1.6rem; font-weight: 800; color: #ffffff; margin-bottom: 10px; }
    .paywall-desc { color: #94a3b8; font-size: 0.95rem; line-height: 1.5; margin-bottom: 24px; }
    .btn-paywall {
        display: inline-block;
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: #ffffff !important;
        font-weight: 800;
        font-size: 1rem;
        padding: 14px 32px;
        border-radius: 10px;
        text-decoration: none;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- BARRA LATERAL: ACCESO Y PROTECCIÓN DE DATOS ---
st.sidebar.title("👤 Acceso de Usuario")

if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""

if "user_plan" not in st.session_state:
    st.session_state["user_plan"] = "free"

with st.sidebar.form("auth_form"):
    email_input = st.text_input(
        "Email de la cuenta",
        value=st.session_state["user_email"],
        placeholder="ejemplo@correo.com",
    )

    # ⚖️ CASILLA DE CUMPLIMIENTO RGPD / PROTECCIÓN DE DATOS
    aceptar_politica = st.checkbox(
        "Acepto la Política de Privacidad y el tratamiento de mi email para la gestión de la cuenta."
    )

    submit_auth = st.form_submit_button(
        "🚀 Iniciar sesión / Registrarse", use_container_width=True
    )

    if submit_auth:
        if not email_input or "@" not in email_input:
            st.error("Por favor, introduce un email válido.")
        elif not aceptar_politica:
            st.warning(
                "⚠️ Debes aceptar la política de privacidad para continuar."
            )
        else:
            plan_detectado = get_or_create_user_profile(email_input)
            st.session_state["user_email"] = email_input.strip().lower()
            st.session_state["user_plan"] = plan_detectado
            st.rerun()

USER_PLAN = st.session_state.get("user_plan", "free")
USER_EMAIL = st.session_state.get("user_email", "")

if USER_EMAIL:
    if USER_PLAN == "pro":
        st.sidebar.success(f"✨ ¡Sesión PRO activa!\n\n**{USER_EMAIL}**")
    else:
        st.sidebar.info(f"ℹ️ Plan Gratuito activo.\n\n**{USER_EMAIL}**")

st.sidebar.markdown("---")
# Enlace visible a pie de la barra lateral
st.sidebar.caption(
    "🔒 Tus datos se tratan conforme al RGPD solo para la gestión de tu acceso a uSmartSearch."
)

# Asignamos la variable global USER_PLAN desde el estado de sesión
USER_PLAN = st.session_state.get("user_plan", "free")
USER_EMAIL = st.session_state.get("user_email", "")

# Feedback en la barra lateral según la sesión del usuario
if USER_EMAIL:
    if USER_PLAN == "pro":
        st.sidebar.success(
            f"✨ ¡Sesión PRO activa!\n\n**{USER_EMAIL}** (Acceso ilimitado)"
        )
    else:
        st.sidebar.info(
            f"ℹ️ Sesión Gratuita activa.\n\n**{USER_EMAIL}** (Muestra limitada a 2 resultados)"
        )

st.sidebar.markdown("---")

# --- 4. GESTIÓN DE BARRA LATERAL ---
st.sidebar.title("⚙️ Configuración")
user_api_keys_input = st.sidebar.text_input(
    "Tu API Key personal (Opcional)",
    type="password",
    help="Puedes introducir una o varias claves separadas por comas.",
)

def parse_api_keys(input_val):
    if not input_val:
        return []
    if isinstance(input_val, list):
        return [str(k).strip() for k in input_val if str(k).strip()]
    keys = re.split(r"[\n,\s]+", str(input_val).strip())
    return [k.strip() for k in keys if k.strip()]

user_keys = parse_api_keys(user_api_keys_input)

# Obtener claves desde secretos (soporta sección [youtube] o raíz)
youtube_secrets = st.secrets.get("youtube", {})
if isinstance(youtube_secrets, dict) and "YOUTUBE_API_KEYS" in youtube_secrets:
    server_keys_raw = youtube_secrets["YOUTUBE_API_KEYS"]
else:
    server_keys_raw = st.secrets.get("YOUTUBE_API_KEYS", [])

server_keys = parse_api_keys(server_keys_raw)

# Lista final priorizando las introducidas por el usuario
ACTIVE_API_KEYS = user_keys if user_keys else server_keys

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
### 💡 ¿Cómo obtener tu propia API Key?
1. Ve a [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un proyecto y activa la **YouTube Data API v3**.
3. Genera una **API Key** en Credenciales y pégala aquí arriba.
"""
)

def parse_duration_to_seconds(duration_str):
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration_str)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


# --- 5. CONSULTA A YOUTUBE API CON CACHÉ DE SUPABASE Y ROTACIÓN DE CLAVES ---
def fetch_youtube_outliers(
    api_keys_tuple, query, order, days_back, max_results, min_views=1000
):
    # Paso A: Intentar leer primero desde el Caché de Supabase
    cached_data = get_cached_search(query)
    if cached_data:
        st.toast("⚡ Resultados cargados instantáneamente desde Caché (Supabase)", icon="🚀")
        return cached_data

    # Paso B: Si no está en Supabase, hacer la petición a la API de YouTube
    api_keys = list(api_keys_tuple)
    if not api_keys:
        raise ValueError("No se proporcionó ninguna API Key válida.")

    key_index = 0
    youtube = build("youtube", "v3", developerKey=api_keys[key_index])

    published_after = (
        datetime.now(timezone.utc) - timedelta(days=days_back)
    ).isoformat()

    def execute_with_retry(request_builder_fn, max_retries=3):
        nonlocal key_index, youtube
        for attempt in range(max_retries):
            try:
                request = request_builder_fn(youtube)
                return request.execute()
            except HttpError as e:
                if e.resp.status in [403, 429]:
                    key_index += 1
                    if key_index < len(api_keys):
                        youtube = build("youtube", "v3", developerKey=api_keys[key_index])
                        time.sleep(0.5)
                        continue
                    else:
                        raise Exception("Se ha agotado la cuota de todas las API Keys disponibles.")
                elif e.resp.status in [500, 502, 503, 504] and attempt < max_retries - 1:
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
        
        def build_search_req(yt_client):
            return yt_client.search().list(
                q=query,
                part="snippet",
                type="video",
                videoDuration="any",
                order=order,
                publishedAfter=published_after,
                maxResults=min(50, remaining),
                pageToken=page_token,
            )

        search_res = execute_with_retry(build_search_req)
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
        batch_ids = ",".join(id_batch)
        def build_video_req(yt_client):
            return yt_client.videos().list(
                part="statistics,contentDetails", id=batch_ids
            )
        v_res = execute_with_retry(build_video_req)

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
        batch_c_ids = ",".join(id_batch)
        def build_channel_req(yt_client):
            return yt_client.channels().list(
                part="statistics", id=batch_c_ids
            )
        c_res = execute_with_retry(build_channel_req)

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
            ratio_val = round(views / subs, 1)
            outliers.append(
                {
                    "titulo": item["snippet"]["title"],
                    "canal": item["snippet"]["channelTitle"],
                    "fecha": pub_date,
                    "thumbnail": thumb_url,
                    "visitas_num": views,
                    "suscriptores_num": subs,
                    "ratio_num": ratio_val,
                    "visitas": f"{views:,}",
                    "suscriptores": f"{subs:,}",
                    "ratio": f"{ratio_val}x",
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                }
            )

    outliers = sorted(outliers, key=lambda x: x["ratio_num"], reverse=True)

    # Paso C: Guardar los resultados en Supabase para futuras consultas
    if outliers:
        try:
            save_search_to_cache(query, outliers)
        except Exception as e:
            st.warning(f"No se pudo guardar en el caché de Supabase: {e}")

    return outliers


def get_card_html(item, is_blurred=False):
    title = "Vídeo Bloqueado - Reservado Plan Pro" if is_blurred else item["titulo"]
    channel = "Canal Oculto" if is_blurred else item["canal"]
    url = "#" if is_blurred else item["url"]
    blur_class = "blurred-item" if is_blurred else ""

    thumb = (
        "https://via.placeholder.com/480x270/0f172a/6366f1?text=Apex+Pro+Only"
        if is_blurred
        else item["thumbnail"]
    )

    return f"""<div class="outlier-card {blur_class}"><div style="display: grid; grid-template-columns: 240px 1fr 180px; gap: 20px; align-items: center;"><div class="thumbnail-container"><a href="{url}" target="_blank"><img src="{thumb}" class="thumbnail-img" alt="Thumbnail"></a></div><div><a href="{url}" target="_blank" class="outlier-title">{title}</a><div class="outlier-meta"><span>📺 {channel}</span><span>📅 {item['fecha']}</span></div><div class="metric-container"><div class="metric-box"><div class="metric-label">Visitas</div><div class="metric-value">{item['visitas']}</div></div><div class="metric-box"><div class="metric-label">Suscriptores</div><div class="metric-value">{item['suscriptores']}</div></div></div></div><div style="display: flex; flex-direction: column; gap: 14px; align-items: stretch; text-align: center;"><div><span class="badge-outlier">🔥 {item['ratio']}</span></div><a href="{url}" target="_blank" class="btn-yt">▶ Ver en YouTube</a></div></div></div>"""


def render_outliers_with_paywall(outliers):
    free_limit = 2
    visible_outliers = outliers[:free_limit]
    locked_outliers = outliers[free_limit:]

    for item in visible_outliers:
        st.markdown(get_card_html(item, is_blurred=False), unsafe_allow_html=True)

    if locked_outliers:
        locked_count = len(locked_outliers)
        preview_locked = locked_outliers[:3]
        locked_html_cards = "".join([get_card_html(item, is_blurred=True) for item in preview_locked])

        paywall_wrapper = f"""<div class="locked-container">{locked_html_cards}<div class="paywall-overlay"><div class="paywall-card"><div class="paywall-icon">🔒</div><div class="paywall-title">Desbloquea {locked_count} Outliers más</div><div class="paywall-desc">Estás viendo una vista previa gratuita. Suscríbete al plan Pro de Apex Intelligence para consultar la lista completa de vídeos viralizados y exportar todos los datos.</div><a href="{PAYMENT_URL}" target="_blank" class="btn-paywall">Obtener Acceso Ilimitado</a></div></div></div>"""
        
        st.markdown(paywall_wrapper, unsafe_allow_html=True)


# --- 6. HEADER ---
st.markdown(
    """
    <div class="app-header">
        <div class="app-badge">⚡ BEST VIDEOS </div>
        <div class="app-title">U Smart Search</div>
        <div class="app-subtitle">Localiza vídeos de alto rendimiento que superan exponencialmente la audiencia base de sus canales.</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --- 7. PANEL DE CONTROL ---
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
        )
    with col_min_views:
        min_views_input = st.number_input(
            "Mínimo de visitas",
            min_value=100,
            value=1000,
            step=500,
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

# --- 8. EJECUCIÓN DE BÚSQUEDA ---
if btn_search:
    if not ACTIVE_API_KEYS:
        st.error(
            "⚠️ No hay API Keys disponibles. Introduce tu clave en la barra lateral o configura YOUTUBE_API_KEYS en Secrets."
        )
    elif not query:
        st.warning("⚠️ Introduce una palabra clave.")
    else:
        with st.spinner("Analizando métricas del canal y vídeos..."):
            try:
                days_back = time_mapping[time_option]
                outliers = fetch_youtube_outliers(
                    tuple(ACTIVE_API_KEYS),
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
                    st.info("No se encontraron outliers con los filtros actuales.")

            except Exception as e:
                st.error(f"Error en la consulta: {e}")

# --- 9. MOSTRAR RESULTADOS Y EXPORTACIÓN ---
# --- RENDERIZADO DE RESULTADOS (PAYWALL) ---
if "outliers_data" in st.session_state:
    outliers = st.session_state["outliers_data"]

    if outliers and len(outliers) > 0:
        st.markdown("<br>", unsafe_allow_html=True)
        col_info, col_export = st.columns([3, 1], vertical_alignment="center")

        with col_info:
            st.markdown(f"### ⚡ {len(outliers)} Outliers detectados")

        with col_export:
            # Si es PRO exporta todo; si es FREE solo la muestra gratuita (2 resultados)
            export_data = outliers if USER_PLAN == "pro" else outliers[:2]
            df_export = pd.DataFrame(export_data)

            column_mapping = {
                "titulo": "Título",
                "canal": "Canal",
                "fecha": "Fecha Publicación",
                "visitas_num": "Visitas",
                "suscriptores_num": "Suscriptores",
                "ratio": "Multiplicador",
                "url": "Enlace",
            }

            valid_cols = [
                col for col in column_mapping.keys() if col in df_export.columns
            ]
            df_csv = df_export[valid_cols].rename(columns=column_mapping)
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

            label_btn = (
                "📥 Exportar Todo a CSV"
                if USER_PLAN == "pro"
                else "📥 Exportar Muestra CSV"
            )
            st.download_button(
                label=label_btn,
                data=csv_data,
                file_name=f"outliers_{clean_query}.csv",
                mime="text/csv",
                use_container_width=True,
                key="btn_download_csv",
            )

        # CONTROL DE ACCESO PRO VS FREE
        if USER_PLAN == "pro":
            # Si el usuario es PRO, muestra TODOS los resultados sin difuminar ni bloquear
            for item in outliers:
                st.markdown(
                    get_card_html(item, is_blurred=False),
                    unsafe_allow_html=True,
                )
        else:
            # Si el usuario es FREE, aplica la vista con Paywall (muestra 2 y bloquea el resto)
            render_outliers_with_paywall(outliers)
