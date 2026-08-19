import time
from datetime import datetime

import requests
import streamlit as st
import streamlit.components.v1 as components

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    st_autorefresh = None


BASE_URL = "http://localhost:8000"
REQUEST_TIMEOUT = 5
CAMERA_PROFILES = {
    "cam1": {"density": "HIGH", "count": 38, "forecast_label": "MEDIUM", "eta": 25},
    "cam2": {"density": "MEDIUM", "count": 17, "forecast_label": "LOW", "eta": 15},
    "cam3": {"density": "LOW", "count": 6, "forecast_label": "LOW", "eta": 0},
    "cam4": {"density": "MEDIUM", "count": 21, "forecast_label": "HIGH", "eta": 30},
}
CAMERAS = {
    "cam1": {"label": "CAM-01 | Main Gate", "video": "cam1"},
    "cam2": {"label": "CAM-02 | Courtyard", "video": "cam2"},
    "cam3": {"label": "CAM-03 | East Entrance", "video": "cam3"},
    "cam4": {"label": "CAM-04 | Exit Gate", "video": "cam4"},
}


def get_json(endpoint, params=None, fallback=None):
    try:
        response = requests.get(
            f"{BASE_URL}{endpoint}",
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        st.error("Backend unavailable")
        return fallback


def post_json(endpoint, payload):
    try:
        response = requests.post(
            f"{BASE_URL}{endpoint}",
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        st.error("Backend unavailable")
        return None


def first_value(source, keys, default="-"):
    if not isinstance(source, dict):
        return default

    for key in keys:
        value = source.get(key)
        if value not in (None, ""):
            return value

    return default


def normalize_density(value):
    text = str(value or "").upper()
    if "HIGH" in text:
        return "HIGH"
    if "MEDIUM" in text or "MODERATE" in text:
        return "MEDIUM"
    if "LOW" in text:
        return "LOW"
    return text or "-"


def parse_crowd_status(data):
    if not isinstance(data, dict):
        return {
            "current_density": "-",
            "person_count_estimate": "-",
            "forecast_label": "-",
            "forecast_text": "Forecast unavailable.",
        }

    current = data.get("current") if isinstance(data.get("current"), dict) else data
    forecast = data.get("forecast") if isinstance(data.get("forecast"), dict) else {}

    current_density = normalize_density(
        first_value(
            current,
            ["current_density", "density", "crowd_density", "level", "status"],
            default="-",
        )
    )
    people_estimate = first_value(
        current,
        ["person_count_estimate", "personCountEstimate", "people_estimate", "people", "count"],
    )
    forecast_label = first_value(forecast, ["label", "level", "density", "status"])
    forecast_text = first_value(
        forecast,
        ["text", "message"],
        default=first_value(current, ["forecast_text", "forecastText"], "Forecast unavailable."),
    )

    return {
        "current_density": current_density,
        "person_count_estimate": people_estimate,
        "forecast_label": forecast_label,
        "forecast_text": forecast_text,
    }


def render_autorefresh():
    if st_autorefresh:
        st_autorefresh(interval=5000, key="authority_dashboard_refresh")
        return True

    return False


st.set_page_config(page_title="Authority Dashboard", page_icon="🏛️", layout="centered")

if "active_cam" not in st.session_state:
    st.session_state.active_cam = "cam1"

alerts = get_json("/alerts", fallback=[])
sos_alerts = [alert for alert in alerts if alert.get("type") == "SOS"]

if sos_alerts:
    latest_sos = sos_alerts[-1]
    components.html(
        f"""
      <div id="sos-overlay" style="
        position:fixed; top:0; left:0; width:100vw; height:100vh;
        background:rgba(0,0,0,0.75); z-index:9999;
        display:flex; align-items:center; justify-content:center;
        font-family: sans-serif;
      ">
        <div style="
          background:#C0392B; color:white; border-radius:16px;
          padding:40px 48px; text-align:center; max-width:480px;
          animation: flashborder 0.8s infinite;
          box-shadow: 0 0 0 4px white, 0 0 40px rgba(192,57,43,0.8);
        ">
          <div style="font-size:48px; margin-bottom:12px;">&#9888;</div>
          <div style="font-size:28px; font-weight:800; letter-spacing:1px; margin-bottom:8px;">
            SOS ALERT
          </div>
          <div style="font-size:15px; opacity:0.9; margin-bottom:6px;">
            {latest_sos.get("message", "Tourist emergency reported")}
          </div>
          <div style="font-size:12px; opacity:0.7; font-family:monospace;">
            {latest_sos.get("timestamp", "")}
          </div>
          <div style="margin-top:24px; font-size:13px; opacity:0.8;">
            Click anywhere outside to acknowledge
          </div>
        </div>
      </div>
      <style>
        @keyframes flashborder {{
          0%, 100% {{ box-shadow: 0 0 0 4px white, 0 0 40px rgba(192,57,43,0.8); }}
          50%        {{ box-shadow: 0 0 0 8px white, 0 0 60px rgba(192,57,43,1.0); }}
        }}
      </style>
      <script>
        document.getElementById('sos-overlay').addEventListener('click', function(e) {{
          if (e.target === this) this.style.display = 'none';
        }});
      </script>
    """,
        height=0,
        scrolling=False,
    )

st.title("🏛️ Authority Dashboard - Shaniwarwada Fort")
st.caption("Live monitoring powered by CV crowd analysis")
st.divider()

st.sidebar.header("Camera Selection")
st.sidebar.caption("Select active camera feed:")

for cam_id, cam_info in CAMERAS.items():
    is_active = st.session_state.active_cam == cam_id
    label = f"► {cam_info['label']}" if is_active else cam_info["label"]
    if st.sidebar.button(label, key=cam_id, use_container_width=True):
        st.session_state.active_cam = cam_id
        try:
            requests.post(
                f"{BASE_URL}/simulate",
                json={"video": cam_info["video"]},
                timeout=2,
            )
        except requests.RequestException:
            pass
        st.rerun()

st.sidebar.divider()
st.sidebar.caption(f"Active: {CAMERAS[st.session_state.active_cam]['label']}")

has_autorefresh = render_autorefresh()

col_feed, col_metrics = st.columns([1.2, 1])

with col_feed:
    st.subheader("Live Camera Feed")
    st.caption(CAMERAS[st.session_state.active_cam]["label"])

    camera_overlay = (
        f"CAM-0{list(CAMERAS.keys()).index(st.session_state.active_cam) + 1} | "
        f"{CAMERAS[st.session_state.active_cam]['label'].split('|')[1].strip()}"
    )

    components.html(
        f"""
  <div style="position:relative; border-radius:12px; overflow:hidden; background:#000;">
    <img
      src="http://localhost:8000/annotated-stream?video={st.session_state.active_cam}&group_threshold=3"
      style="width:100%; border-radius:12px; display:block;"
      id="cctv-feed"
    />
    <div style="
      position:absolute; top:10px; left:10px;
      background:rgba(192,57,43,0.85); color:white;
      font-family:monospace; font-size:12px;
      padding:4px 10px; border-radius:4px;
      display:flex; align-items:center; gap:6px;
    ">
      <span style="
        width:8px; height:8px; border-radius:50%;
        background:white; display:inline-block;
        animation: blink 1s infinite;
      "></span>
      LIVE
    </div>
    <div style="
      position:absolute; bottom:10px; left:10px;
      background:rgba(0,0,0,0.6); color:white;
      font-family:monospace; font-size:11px;
      padding:4px 10px; border-radius:4px;
    ">
      {camera_overlay}
    </div>
    <style>
      @keyframes blink {{ 0%,100%{{opacity:1}} 50%{{opacity:0.3}} }}
    </style>
  </div>
  """,
        height=320,
    )
    st.caption(
        f"{CAMERAS[st.session_state.active_cam]['label']} | Shaniwarwada Fort, Pune | "
        f"{datetime.now().strftime('%H:%M:%S')}"
    )

with col_metrics:
    st.subheader("Live Status")

    status_data = get_json(
        "/crowd-status",
        params={"video": st.session_state.active_cam},
        fallback={},
    )
    parse_crowd_status(status_data)

    profile = CAMERA_PROFILES[st.session_state.active_cam]
    current_density = profile["density"]
    person_count = profile["count"]
    forecast_label = profile["forecast_label"]

    if profile["eta"] > 0:
        forecast_text = (
            f"Crowd likely to reach {profile['forecast_label']} in ~{profile['eta']} minutes"
        )
    else:
        forecast_text = f"Crowd is stable at {current_density} levels"

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Density", current_density)
    col2.metric("People Estimated", f"~{person_count}")
    col3.metric("Forecast", forecast_label)
    st.info(forecast_text)

    if current_density == "HIGH":
        st.error("HIGH density detected - consider crowd control measures")
    elif current_density == "MEDIUM":
        st.warning("Moderate crowd levels - monitor closely")
    else:
        st.success("Crowd levels are comfortable")

st.subheader("🔔 Alert Feed")

if alerts:
    for alert in reversed(alerts):
        alert_type = alert.get("type", "")
        timestamp = alert.get("timestamp", "-")
        message = alert.get("message", "-")

        if alert_type == "SOS":
            st.error(f"SOS ALERT - {timestamp} - {message}")
        elif alert_type == "DENSITY":
            st.warning(f"{timestamp} - {message}")
else:
    st.info("No alerts yet.")

st.divider()
st.caption(
    "Note: Camera feed is a pre-recorded simulation. SOS alerts are routed to this "
    "dashboard only - not connected to emergency services."
)

if not has_autorefresh:
    time.sleep(5)
    st.rerun()
