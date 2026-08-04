import pandas as pd
import requests
import streamlit as st
from googleapiclient.discovery import build

st.set_page_config(
    page_title="YouTube Outlier Finder", page_icon="🎬", layout="wide"
)

# Claves de la API desde Secrets
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


# --- FUNCIÓN CON CACHÉ Y BATCHING (OPTIMIZADA) ---
@st.cache_data(
    ttl=43200, show_spinner=False
)  # Guarda resultados en caché durante 12 horas
def fetch_youtube_outliers(api_key, query, order, max_results):
    youtube = build("youtube", "v3", developerKey=api_key)

    # 1. Búsqueda de vídeos por palabra clave
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

    # Mapear IDs de vídeos y canales
    video_ids = [item["id"]["videoId"] for item in items]
    channel_ids = [item["snippet"]["channelId"] for item in items]

    # 2. Petición EN LOTE para estadísticas de TODOS los vídeos a la vez
    v_res = (
        youtube.videos()
        .list(part="statistics", id=",".join(video_ids))
        .execute()
    )
    views_map = {
        v_item["id"]: int(v_item["statistics"].get("viewCount", 0))
        for v_item in v_res.get("items", [])
    }

    # 3. Petición EN LOTE para estadísticas de TODOS los canales a la vez
    c_res = (
        youtube.channels()
        .list(part="statistics", id=",".join(set(channel_ids)))
        .execute()
    )
    subs_map = {
        c_item["id"]: int(c_item["statistics"].get("subscriberCount", 0))
        for c_item in c_res.get("items", [])
    }

    # 4. Procesar y filtrar los Outliers
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
                    "Título": item["snippet"]["title"],
                    "Canal": item["snippet"]["channelTitle"],
                    "Visitas": f"{views:,}",
                    "Suscriptores": f"{subs:,}",
                    "Multiplicador": f"{ratio}x",
                    "Enlace": f"https://www.youtube.com/watch?v={vid_id}",
                }
            )

    return outliers


# --- INTERFAZ DE USUARIO ---
st.title("🚀 Buscador de Vídeos Virales u Outliers en YouTube")
st.write(
    "Encuentra vídeos que han logrado **más reproducciones que suscriptores** tiene el canal."
)

# --- PANEL LATERAL (PRO ACCESS) ---
with st.sidebar:
    st.header("🔑 Acceso PRO")
    user_license = st.text_input(
        "Introduce tu Clave de Licencia:", type="password"
    )

    is_pro = False
    if user_license:
        with st.spinner("Validando licencia..."):
            is_pro = validate_license_key(user_license)
            if is_pro:
                st.success("✅ Licencia PRO Activa")
            else:
                st.error("❌ Licencia inválida o caducada")
    else:
        st.info("ℹ️ Modo Demo: Muestra solo 1 resultado.")
        st.markdown(
            "👉 [**Consigue tu clave PRO aquí**](https://tu-tienda.lemonsqueezy.com/checkout)"
        )

# --- FORMULARIO DE BÚSQUEDA ---
col1, col2 = st.columns([2, 1])

with col1:
    query = st.text_input(
        "🔍 Introduce el tema o palabra clave a buscar:",
        placeholder="Ej. como cultivar tomates en maceta",
    )

with col2:
    sort_option = st.selectbox(
        "📊 Ordenar búsqueda por:",
        options=["Relevancia", "Más reproducidos", "Más recientes"],
        index=0,
    )

max_results = st.slider(
    "Número de vídeos a inspeccionar:",
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

# --- BOTÓN DE EJECUCIÓN ---
if st.button("Buscar Vídeos Virales", type="primary"):
    if not YOUTUBE_API_KEY:
        st.error(
            "⚠️ Error de configuración: Falta YOUTUBE_API_KEY en los Secrets."
        )
    elif not query:
        st.warning("⚠️ Escribe una palabra clave para buscar.")
    else:
        with st.spinner("Analizando vídeos de YouTube..."):
            try:
                # Si no es PRO, forzamos un análisis pequeño
                search_limit = max_results if is_pro else 10

                # Obtener outliers usando la función optimizada
                outliers = fetch_youtube_outliers(
                    YOUTUBE_API_KEY,
                    query,
                    sort_mapping[sort_option],
                    search_limit,
                )

                # Si no es PRO, recortamos los resultados a 1
                if not is_pro and outliers:
                    outliers = outliers[:1]

                if outliers:
                    if is_pro:
                        st.success(
                            f"¡Se encontraron {len(outliers)} vídeos virales/outliers!"
                        )
                    else:
                        st.warning(
                            "🔒 Modo Demo: Se muestra solo 1 resultado. Introduce tu clave PRO para ver todos."
                        )

                    df = pd.DataFrame(outliers)
                    st.dataframe(
                        df,
                        column_config={
                            "Enlace": st.column_config.LinkColumn("Ver en YT")
                        },
                        use_container_width=True,
                    )
                else:
                    st.info(
                        "No se encontraron vídeos que superen en visitas al número de suscriptores para esta búsqueda."
                    )

            except Exception as e:
                st.error(f"Error al consultar la API de YouTube: {e}")
