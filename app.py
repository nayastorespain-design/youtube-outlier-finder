import pandas as pd
import streamlit as st
from googleapiclient.discovery import build

st.set_page_config(
    page_title="YouTube Outlier Finder", page_icon="🎬", layout="wide"
)

st.title("🚀 Buscador de Vídeos Virales u Outliers en YouTube")
st.write(
    "Encuentra vídeos que han logrado **más reproducciones que suscriptores** tiene el canal que los subió."
)

st.sidebar.header("⚙️ Configuración")
api_key_input = st.sidebar.text_input(
    "Ingresa tu YouTube API Key:",
    type="password",
    help="Pega aquí la clave que obtuviste en Google Cloud",
)

query = st.text_input(
    "🔍 Introduce el tema o palabra clave a buscar:",
    placeholder="Ej. como cultivar tomates en maceta",
)
max_results = st.slider(
    "Número de vídeos a inspeccionar:",
    min_value=10,
    max_value=50,
    value=20,
    step=5,
)

if st.button("Buscar Vídeos Virales", type="primary"):
    if not api_key_input:
        st.error(
            "⚠️ Por favor, introduce tu API Key en la barra lateral izquierda."
        )
    elif not query:
        st.warning("⚠️ Escribe una palabra clave para buscar.")
    else:
        with st.spinner("Analizando vídeos de YouTube..."):
            try:
                youtube = build("youtube", "v3", developerKey=api_key_input)

                search_response = (
                    youtube.search()
                    .list(
                        q=query,
                        part="snippet",
                        type="video",
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

                    v_res = (
                        youtube.videos()
                        .list(part="statistics", id=video_id)
                        .execute()
                    )
                    views = int(
                        v_res["items"][0]["statistics"].get("viewCount", 0)
                    )

                    c_res = (
                        youtube.channels()
                        .list(part="statistics", id=channel_id)
                        .execute()
                    )
                    subs = int(
                        c_res["items"][0]["statistics"].get(
                            "subscriberCount", 0)
                    )

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
                        "No se encontraron vídeos que superen en visitas al número de suscriptores en este grupo de resultados."
                    )

            except Exception as e:
                st.error(f"Error al consultar la API de YouTube: {e}")
