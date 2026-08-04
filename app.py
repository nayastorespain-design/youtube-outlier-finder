import pandas as pd
import streamlit as st
from googleapiclient.discovery import build

st.set_page_config(
    page_title="YouTube Outlier Finder", page_icon="🎬", layout="wide"
)

st.title("🚀 Buscador de Vídeos Virales u Outliers en YouTube")
st.write(
    "Encuentra vídeos que han logrado **más reproducciones que suscriptores** tiene el canal."
)

# Obtener la API Key desde los Secrets de Streamlit (Oculta al usuario)
api_key = st.secrets.get("YOUTUBE_API_KEY")

# --- Formulario / Controles de entrada ---
col1, col2 = st.columns([2, 1])

with col1:
    query = st.text_input(
        "🔍 Introduce el tema o palabra clave a buscar:",
        placeholder="Ej. como cultivar tomates en maceta",
    )

with col2:
    # Filtro de ordenación para la API de YouTube
    sort_option = st.selectbox(
        "📊 Ordenar búsqueda inicial por:",
        options=["Relevancia", "Más reproducidos", "Más recientes"],
        index=0,
        help="Si ordenas por 'Más reproducidos', aumentarás la probabilidad de encontrar vídeos con muchas visitas en canales pequeños.",
    )

max_results = st.slider(
    "Número de vídeos a inspeccionar:",
    min_value=10,
    max_value=50,
    value=30,
    step=5,
)

# Mapeo de la opción seleccionada al parámetro que exige la API de YouTube
sort_mapping = {
    "Relevancia": "relevance",
    "Más reproducidos": "viewCount",
    "Más recientes": "date",
}

if st.button("Buscar Vídeos Virales", type="primary"):
    if not api_key:
        st.error(
            "⚠️ Error de configuración: No se ha encontrado la API Key en el servidor (secrets.toml)."
        )
    elif not query:
        st.warning("⚠️ Escribe una palabra clave para buscar.")
    else:
        with st.spinner("Analizando vídeos de YouTube..."):
            try:
                youtube = build("youtube", "v3", developerKey=api_key)

                # Llamada a la API aplicando el parámetro 'order' según la selección del usuario
                search_response = (
                    youtube.search()
                    .list(
                        q=query,
                        part="snippet",
                        type="video",
                        order=sort_mapping[sort_option],
                        maxResults=max_results,
                    )
                    .execute()
                )

                outliers = []

                for item in search_response.get("items", []):
                    video_id = item["id"]["videoId"]
                    channel_id = item["snippet"]["channelId"]
                    title = item["snippet"]["title"]
                    channel_title = item["snippet"]["channelTitle"]

                    # Estadísticas del vídeo (visitas)
                    v_res = (
                        youtube.videos()
                        .list(part="statistics", id=video_id)
                        .execute()
                    )
                    views = int(
                        v_res["items"][0]["statistics"].get("viewCount", 0)
                    )

                    # Estadísticas del canal (suscriptores)
                    c_res = (
                        youtube.channels()
                        .list(part="statistics", id=channel_id)
                        .execute()
                    )
                    subs = int(
                        c_res["items"][0]["statistics"].get(
                            "subscriberCount", 0
                        )
                    )

                    # Condición de Outlier: Visitas mayores que suscriptores
                    if views > subs and subs > 0:
                        ratio = round(views / subs, 1)
                        outliers.append(
                            {
                                "Título": title,
                                "Canal": channel_title,
                                "Visitas": f"{views:,}",
                                "Suscriptores": f"{subs:,}",
                                "Multiplicador": f"{ratio}x",
                                "Enlace": f"https://www.youtube.com/watch?v={video_id}",
                            }
                        )

                if outliers:
                    st.success(
                        f"¡Se encontraron {len(outliers)} vídeos virales/outliers!"
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
