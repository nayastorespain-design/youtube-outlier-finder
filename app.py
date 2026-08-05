import time
import json
import base64
from datetime import datetime, timezone, timedelta
import isodate
import pandas as pd
import streamlit as st
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ==========================================
# ⚙️ PAGE CONFIGURATION & LAYOUT
# ==========================================
st.set_page_config(
    page_title="Apex Outliers | Enterprise SaaS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 🎨 CUSTOM SAAS / LINEAR-STYLE CSS
# ==========================================
st.markdown("""
<style>
    /* Dark / SaaS Linear Aesthetic */
    :root {
        --bg-color: #0d0f12;
        --card-bg: #16191e;
        --card-border: #262a33;
        --accent-purple: #6366f1;
        --accent-blue: #3b82f6;
        --text-primary: #f3f4f6;
        --text-secondary: #9ca3af;
        --success-green: #10b981;
        --warning-amber: #f59e0b;
    }

    /* Streamlit Global Overrides */
    .stApp {
        background-color: #0b0d10;
        color: #e5e7eb;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    /* Sidebar Customization */
    section[data-testid="stSidebar"] {
        background-color: #111318 !important;
        border-right: 1px solid #1f232b;
    }
    
    /* Metric Cards & Outlier Containers */
    .apex-card {
        background-color: #161920;
        border: 1px solid #242933;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 20px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .apex-card:hover {
        border-color: #4f46e5;
        transform: translateY(-2px);
    }

    .badge-ratio {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        color: #ffffff;
        font-weight: 700;
        font-size: 0.85rem;
        padding: 4px 10px;
        border-radius: 6px;
        display: inline-block;
    }

    .badge-metrics {
        color: #9ca3af;
        font-size: 0.8rem;
        font-weight: 500;
    }

    .stat-box {
        background: #1a1d24;
        border: 1px solid #2b303c;
        border-radius: 8px;
        padding: 12px 16px;
        text-align: center;
    }
    
    .stat-val {
        font-size: 1.4rem;
        font-weight: 700;
        color: #f9fafb;
    }
    
    .stat-lbl {
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #6b7280;
    }

    /* Form & Input Enhancements */
    div[data-baseweb="input"] {
        background-color: #191c23 !important;
        border-color: #2a2f3d !important;
        color: #ffffff !important;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #4f46e5 0%, #3b82f6 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 6px;
        padding: 0.6rem 1.2rem;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        opacity: 0.95;
        box-shadow: 0 4px 14px rgba(79, 70, 229, 0.4);
    }
    
    /* High contrast text */
    h1, h2, h3, h4 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔑 API KEYS & POOL SETUP
# ==========================================
SYSTEM_API_KEYS = [
    st.secrets.get("YOUTUBE_API_KEY_1", ""),
    st.secrets.get("YOUTUBE_API_KEY_2", ""),
    st.secrets.get("YOUTUBE_API_KEY_3", ""),
    st.secrets.get("YOUTUBE_API_KEY_4", ""),
    st.secrets.get("YOUTUBE_API_KEY_5", ""),
]

# ==========================================
# 🛠️ HELPER & PARSING FUNCTIONS
# ==========================================
def parse_duration_to_seconds(duration_raw: str) -> int:
    """Parses ISO 8601 duration format into total seconds."""
    try:
        duration = isodate.parse_duration(duration_raw)
        return int(duration.total_seconds())
    except Exception:
        return 0

def format_number(num: int) -> str:
    """Formats large numbers into readable K/M strings."""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)

def is_quota_error(error: Exception) -> bool:
    """Determines whether an exception is caused by YouTube Data API quota exhaustion."""
    if isinstance(error, HttpError):
        if error.resp.status in [403, 429]:
            err_str = str(error).lower()
            if "quotaexceeded" in err_str or "ratelimitexceeded" in err_str or "keyinvalid" not in err_str:
                return True
    return False

# ==========================================
# 🔄 CORE ENGINE: ROTATING BACKEND SEARCH
# ==========================================
@st.cache_data(ttl=3600*6, show_spinner=False)
def fetch_youtube_outliers(
    keys_pool: list,
    query: str,
    order: str,
    days_back: int,
    min_views: int = 1000,
    min_ratio: float = 1.0,
    max_pages: int = 5,
    min_duration_sec: int = 60
):
    """
    Executes a multi-page deep scan for YouTube video outliers.
    Includes failover key rotation upon hitting quota limits.
    """
    valid_keys = [k.strip() for k in keys_pool if k and k.strip()]
    if not valid_keys:
        raise ValueError("No API Keys configured. Please supply a valid Google API Key.")

    current_key_idx = 0

    def get_service():
        nonlocal current_key_idx
        return build("youtube", "v3", developerKey=valid_keys[current_key_idx])

    def execute_with_failover(request_builder_fn):
        nonlocal current_key_idx
        while current_key_idx < len(valid_keys):
            try:
                service = get_service()
                req = request_builder_fn(service)
                return req.execute()
            except Exception as e:
                if is_quota_error(e):
                    current_key_idx += 1
                    if current_key_idx >= len(valid_keys):
                        raise RuntimeError("❌ All available API keys have exhausted their daily quota.")
                    st.toast(f"🔄 Quota reached on Key #{current_key_idx}. Rotating to Key #{current_key_idx+1}...", icon="⚡")
                else:
                    raise e

    published_after = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()

    def chunk_list(lst, size=50):
        for i in range(0, len(lst), size):
            yield lst[i : i + size]

    all_raw_items = []
    page_token = None
    page_count = 0

    # Step 1: Paginated Search Scanning
    while True:
        def build_search_req(service):
            return service.search().list(
                q=query,
                part="snippet",
                type="video",
                videoDuration="any",
                order=order,
                publishedAfter=published_after,
                maxResults=50,
                pageToken=page_token
            )

        search_res = execute_with_failover(build_search_req)
        items = search_res.get("items", [])
        if not items:
            break

        all_raw_items.extend(items)
        page_token = search_res.get("nextPageToken")
        page_count += 1

        if not page_token or page_count >= max_pages:
            break

    if not all_raw_items:
        return []

    video_ids = [item["id"]["videoId"] for item in all_raw_items if "id" in item and "videoId" in item["id"]]
    channel_ids = list(set(item["snippet"]["channelId"] for item in all_raw_items if "snippet" in item))

    # Step 2: Batch Fetch Video Metadata & Statistics (up to 50 per batch)
    video_details = {}
    for id_batch in chunk_list(video_ids, 50):
        def build_video_req(service):
            return service.videos().list(
                part="statistics,contentDetails",
                id=",".join(id_batch)
            )
        v_res = execute_with_failover(build_video_req)
        for v_item in v_res.get("items", []):
            v_id = v_item["id"]
            views = int(v_item["statistics"].get("viewCount", 0))
            duration_raw = v_item.get("contentDetails", {}).get("duration", "PT0S")
            seconds = parse_duration_to_seconds(duration_raw)
            video_details[v_id] = {"views": views, "seconds": seconds}

    # Step 3: Batch Fetch Channel Statistics
    subs_map = {}
    for id_batch in chunk_list(channel_ids, 50):
        def build_channel_req(service):
            return service.channels().list(
                part="statistics",
                id=",".join(id_batch)
            )
        c_res = execute_with_failover(build_channel_req)
        for c_item in c_res.get("items", []):
            subs_map[c_item["id"]] = int(c_item["statistics"].get("subscriberCount", 0))

    # Step 4: Process Outliers
    outliers = []
    for item in all_raw_items:
        vid_id = item["id"]["videoId"]
        chan_id = item["snippet"]["channelId"]

        v_info = video_details.get(vid_id, {"views": 0, "seconds": 0})
        views = v_info["views"]
        duration_sec = v_info["seconds"]
        subs = subs_map.get(chan_id, 0)

        # Exclude Shorts if configured
        if duration_sec <= min_duration_sec:
            continue

        if subs > 0 and views >= min_views:
            ratio_val = views / subs
            if ratio_val >= min_ratio:
                pub_raw = item["snippet"]["publishedAt"]
                pub_date = datetime.fromisoformat(pub_raw.replace("Z", "+00:00")).strftime("%b %d, %Y")

                thumbnails = item["snippet"].get("thumbnails", {})
                thumb_url = (
                    thumbnails.get("high", {}).get("url") or
                    thumbnails.get("medium", {}).get("url") or
                    thumbnails.get("default", {}).get("url", "")
                )

                outliers.append({
                    "id": vid_id,
                    "titulo": item["snippet"]["title"],
                    "canal": item["snippet"]["channelTitle"],
                    "fecha": pub_date,
                    "thumbnail": thumb_url,
                    "visitas_num": views,
                    "suscriptores_num": subs,
                    "visitas": f"{views:,}",
                    "suscriptores": f"{subs:,}",
                    "duracion_sec": duration_sec,
                    "duracion_min": f"{duration_sec // 60}m {duration_sec % 60}s",
                    "ratio_num": round(ratio_val, 2),
                    "ratio": f"{round(ratio_val, 2)}x",
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                    "channel_url": f"https://www.youtube.com/channel/{chan_id}"
                })

    outliers.sort(key=lambda x: x["ratio_num"], reverse=True)
    return outliers

# ==========================================
# 🖥️ APPLICATION HEADER & SIDEBAR
# ==========================================
st.markdown("<h1>⚡ Apex Outliers <span style='font-size:0.5em; color:#6366f1; vertical-align:middle;'>Enterprise</span></h1>", unsafe_allow_html=True)
st.caption("Advanced YouTube Outlier Detection Engine & Content Opportunity Analyzer")

st.sidebar.markdown("### 🔑 API Key Management")

tier = st.sidebar.radio("Subscription Tier:", ["Enterprise Pool", "Pro Custom Key"], index=1)
user_key = ""

if tier == "Pro Custom Key":
    user_key = st.sidebar.text_input(
        "Enter your YouTube API Key:",
        type="password",
        help="Use your private Google Cloud API key for unshared quota allocation."
    )
    if user_key:
        st.sidebar.success("Custom Key Active (Primary Priority)")

# Assemble Keys Pool based on hierarchy
if user_key.strip():
    active_keys_pool = [user_key.strip()] + [k for k in SYSTEM_API_KEYS if k]
else:
    active_keys_pool = [k for k in SYSTEM_API_KEYS if k]

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ Search Parameters")

query_input = st.sidebar.text_input("Niche / Keyword:", value="home automation setup")
order_input = st.sidebar.selectbox("Sort Search By:", ["relevance", "date", "viewCount"], index=0)
days_input = st.sidebar.slider("Uploaded within (Days):", 7, 365, 90)

st.sidebar.markdown("### 🎯 Outlier Filters")
min_views_input = st.sidebar.number_input("Minimum Views:", value=2000, step=1000)
min_ratio_input = st.sidebar.slider("Min Outlier Ratio (Views/Subs):", 0.5, 20.0, 1.5, step=0.1)
max_pages_input = st.sidebar.slider("Deep Scan Depth (Pages):", 1, 15, 6, help="Each page fetches 50 raw video results.")
exclude_shorts = st.sidebar.checkbox("Exclude YouTube Shorts (<=60s)", value=True)

# ==========================================
# 🚀 EXECUTION & RESULTS PRESENTATION
# ==========================================
min_duration = 60 if exclude_shorts else 0

if st.sidebar.button("🔎 Run Outlier Analysis", type="primary", use_container_width=True):
    if not active_keys_pool:
        st.error("No API Keys configured. Please supply an API key in the sidebar.")
    else:
        with st.spinner(f"Scanning up to {max_pages_input * 50} YouTube videos for high-performing outliers..."):
            try:
                data = fetch_youtube_outliers(
                    keys_pool=active_keys_pool,
                    query=query_input,
                    order=order_input,
                    days_back=days_input,
                    min_views=min_views_input,
                    min_ratio=min_ratio_input,
                    max_pages=max_pages_input,
                    min_duration_sec=min_duration
                )
                
                st.session_state["outlier_data"] = data
                st.session_state["search_performed"] = True
            except Exception as e:
                st.error(f"Analysis Error: {e}")

if st.session_state.get("search_performed", False):
    data = st.session_state.get("outlier_data", [])
    
    if data:
        df = pd.DataFrame(data)
        
        # Stat KPI Summary Header
        st.markdown("---")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        
        with kpi1:
            st.markdown(f"<div class='stat-box'><div class='stat-val'>{len(data)}</div><div class='stat-lbl'>Outliers Found</div></div>", unsafe_allow_html=True)
        with kpi2:
            max_ratio = df["ratio_num"].max()
            st.markdown(f"<div class='stat-box'><div class='stat-val'>{max_ratio}x</div><div class='stat-lbl'>Peak Outlier Ratio</div></div>", unsafe_allow_html=True)
        with kpi3:
            avg_views = format_number(int(df["visitas_num"].mean()))
            st.markdown(f"<div class='stat-box'><div class='stat-val'>{avg_views}</div><div class='stat-lbl'>Avg Outlier Views</div></div>", unsafe_allow_html=True)
        with kpi4:
            avg_subs = format_number(int(df["suscriptores_num"].mean()))
            st.markdown(f"<div class='stat-box'><div class='stat-val'>{avg_subs}</div><div class='stat-lbl'>Avg Channel Subs</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Tabs for Layout (Grid View vs Data Table View vs Export)
        tab_grid, tab_table, tab_export = st.tabs(["🖼️ Visual Cards", "📊 Analytics Table", "📥 Export Data"])
        
        with tab_grid:
            cols_per_row = 3
            for i in range(0, len(data), cols_per_row):
                cols = st.columns(cols_per_row)
                for j, col in enumerate(cols):
                    if i + j < len(data):
                        item = data[i + j]
                        with col:
                            st.markdown(f"""
                            <div class="apex-card">
                                <img src="{item['thumbnail']}" style="width:100%; border-radius:6px; margin-bottom:12px;">
                                <div class="badge-ratio" style="margin-bottom:8px;">🔥 Outlier Ratio: {item['ratio']}</div>
                                <h4 style="font-size:1rem; margin-top:4px; margin-bottom:8px; line-height:1.3;"><a href="{item['url']}" target="_blank" style="color:#ffffff; text-decoration:none;">{item['titulo']}</a></h4>
                                <div class="badge-metrics">
                                    📺 <b><a href="{item['channel_url']}" target="_blank" style="color:#9ca3af;">{item['canal']}</a></b><br>
                                    👁️ <b>Visitas:</b> {item['visitas']} &nbsp;|&nbsp; 👥 <b>Subs:</b> {item['suscriptores']}<br>
                                    ⏱️ <b>Duración:</b> {item['duracion_min']} &nbsp;|&nbsp; 📅 <b>Publicado:</b> {item['fecha']}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

        with tab_table:
            st.markdown("#### High-Contrast Outlier Dataset")
            display_df = df[["titulo", "canal", "ratio", "visitas", "suscriptores", "duracion_min", "fecha", "url"]].copy()
            display_df.columns = ["Title", "Channel", "Outlier Ratio", "Views", "Subscribers", "Duration", "Published Date", "Video URL"]
            st.dataframe(
                display_df,
                use_container_width=True,
                column_config={
                    "Video URL": st.column_config.LinkColumn("Watch Video"),
                }
            )

        with tab_export:
            st.markdown("#### Export Outlier Data")
            st.write("Download the complete analysis dataset for offline evaluation or spreadsheet integration.")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                csv_bytes = df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📄 Download CSV Report",
                    data=csv_bytes,
                    file_name=f"apex_outliers_{query_input.replace(' ', '_')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with c2:
                json_bytes = df.to_json(orient="records", indent=2).encode('utf-8')
                st.download_button(
                    label="🌐 Download JSON Dataset",
                    data=json_bytes,
                    file_name=f"apex_outliers_{query_input.replace(' ', '_')}.json",
                    mime="application/json",
                    use_container_width=True
                )
            with c3:
                excel_df = df.drop(columns=["thumbnail"])
                output = pd.ExcelWriter("outliers_report.xlsx", engine='openpyxl')
                excel_df.to_excel(output, index=False, sheet_name='Outliers')
                output.close()
                with open("outliers_report.xlsx", "rb") as f:
                    st.download_button(
                        label="📊 Download Excel Sheet",
                        data=f.read(),
                        file_name=f"apex_outliers_{query_input.replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
    else:
        st.info("No videos matched all specified outlier criteria. Try lowering the ratio threshold or expanding the publication timeframe.")
