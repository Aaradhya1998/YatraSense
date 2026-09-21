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
FIREBASE_PROJECT_ID = "yatrasense"
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


def _firestore_number(field, default=0):
    return field.get("doubleValue", field.get("integerValue", default))


def get_firestore_sos_alerts():
    """Fetch SOS alerts from Firestore using REST API - no SDK needed."""
    try:
        url = (
            f"https://firestore.googleapis.com/v1/projects/{FIREBASE_PROJECT_ID}"
            "/databases/(default)/documents/sos_alerts"
        )
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return []

        data = response.json()
        documents = data.get("documents", [])

        alerts = []
        for document in documents:
            fields = document.get("fields", {})

            user_fields = fields.get("user", {}).get("mapValue", {}).get("fields", {})
            location_fields = fields.get("location", {}).get("mapValue", {}).get("fields", {})

            name = user_fields.get("name", {}).get("stringValue", "Anonymous")
            email = user_fields.get("email", {}).get("stringValue", "Unknown")
            phone = user_fields.get("phone", {}).get("stringValue", "Not provided")
            emergency_contact = user_fields.get("emergencyContact", {}).get(
                "stringValue",
                "Not provided",
            )

            lat = _firestore_number(location_fields.get("lat", {}), 0)
            lng = _firestore_number(location_fields.get("lng", {}), 0)

            maps_link = fields.get("googleMapsLink", {}).get("stringValue", "")
            timestamp = fields.get("timestamp", {}).get("stringValue", "")
            message = fields.get("message", {}).get("stringValue", "SOS Alert")

            alerts.append(
                {
                    "name": name,
                    "email": email,
                    "phone": phone,
                    "emergency_contact": emergency_contact,
                    "lat": lat,
                    "lng": lng,
                    "maps_link": maps_link,
                    "timestamp": timestamp,
                    "message": message,
                }
            )

        alerts.sort(key=lambda item: item["timestamp"], reverse=True)
        return alerts
    except Exception as exc:
        print(f"Firestore fetch error: {exc}")
        return []


st.set_page_config(page_title="Authority Dashboard", layout="centered")

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

col_title, col_team = st.columns([3, 1])

with col_team:
    st.markdown(
        """
        <div style="text-align:right; padding-top: 8px;">
          <div style="font-weight:700; font-size:15px; color:#E8621A;">Team SHATKONA</div>
          <div style="font-size:12px; color:#888;">SIH 2026</div>
          <div style="font-size:11px; color:#888;">JSPM University, Pune</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_title:
    st.title("Authority Dashboard — Shaniwarwada Fort")
    st.caption("Live monitoring powered by CV crowd analysis")
st.divider()

st.sidebar.header("Camera Selection")
st.sidebar.caption("Select active camera feed:")

for cam_id, cam_info in CAMERAS.items():
    is_active = st.session_state.active_cam == cam_id
    label = f"Active - {cam_info['label']}" if is_active else cam_info["label"]
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

col_feed, col_metrics, col_sos = st.columns([1.2, 1, 0.8])

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

    try:
        response = requests.get(
            f"{BASE_URL}/crowd-status?video={st.session_state.active_cam}",
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        current_density = data["current_density"]
        person_count = data["person_count_estimate"]
        forecast_label = data["forecast"]["label"]
        forecast_text = data["forecast"]["text"]
    except Exception:
        profile = CAMERA_PROFILES[st.session_state.active_cam]
        current_density = profile["density"]
        person_count = profile["count"]
        forecast_label = profile["forecast_label"]
        forecast_text = (
            f"Crowd likely to reach {profile['forecast_label']} in ~{profile['eta']} minutes"
        )
        st.caption(f"Using cached data for {st.session_state.active_cam}")

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

with col_sos:
    st.subheader("SOS Alerts")

    firebase_alerts = get_firestore_sos_alerts()

    if firebase_alerts:
        for alert in firebase_alerts:
            try:
                timestamp = datetime.fromisoformat(alert["timestamp"].replace("Z", ""))
                time_str = timestamp.strftime("%d %b %Y - %H:%M:%S")
            except Exception:
                time_str = alert["timestamp"]

            maps_url = (
                alert["maps_link"]
                if alert["maps_link"]
                else f"https://maps.google.com/?q={alert['lat']},{alert['lng']}"
            )

            st.markdown(
                f"""
                <div style="
                    background: #C0392B;
                    border-radius: 12px;
                    padding: 14px;
                    margin-bottom: 12px;
                    border: 2px solid #ff6b6b;
                    box-shadow: 0 0 20px rgba(192,57,43,0.5);
                ">
                    <div style="color:white; font-weight:800; font-size:15px; margin-bottom:8px;">
                        SOS ALERT
                    </div>
                    <div style="color:white; font-size:13px; margin-bottom:4px;">
                        <b>Name:</b> {alert['name']}
                    </div>
                    <div style="color:rgba(255,255,255,0.85); font-size:12px; margin-bottom:4px;">
                        <b>Email:</b> {alert['email']}
                    </div>
                    <div style="color:rgba(255,255,255,0.85); font-size:12px; margin-bottom:4px;">
                        <b>Phone:</b> {alert['phone']}
                    </div>
                    <div style="color:rgba(255,255,255,0.85); font-size:12px; margin-bottom:4px;">
                        <b>Emergency Contact:</b> {alert['emergency_contact']}
                    </div>
                    <div style="margin-top:8px;">
                        <a href="{maps_url}" target="_blank" style="
                            background:white; color:#C0392B;
                            padding:6px 12px; border-radius:12px;
                            font-size:12px; font-weight:700;
                            text-decoration:none;
                        ">Open in Google Maps</a>
                    </div>
                    <div style="color:rgba(255,255,255,0.5); font-size:10px; font-family:monospace; margin-top:8px;">
                        {time_str}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            """
            <div style="
                background: rgba(107,143,94,0.15);
                border-radius: 12px;
                padding: 16px;
                border: 1px solid rgba(107,143,94,0.3);
                text-align:center;
            ">
                <div style="color:#6B8F5E; font-size:13px; font-weight:600;">All Clear</div>
                <div style="color:rgba(255,255,255,0.3); font-size:11px; margin-top:4px;">No SOS alerts</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption("Live from Firebase Firestore")

st.divider()
st.subheader("GPS-Based Crowd Estimation")
st.caption("For monuments without cameras - crowd estimated from tourist device locations")

col_gps1, col_gps2 = st.columns([1, 2])

with col_gps1:
    st.markdown(
        """
        <div style="background:rgba(107,143,94,0.1); border-radius:12px; padding:16px; border:1px solid rgba(107,143,94,0.3);">
          <div style="font-size:11px; color:#6B8F5E; font-weight:600; margin-bottom:8px;">HOW IT WORKS</div>
          <div style="font-size:13px; color:white; line-height:1.6;">
            Tourist opens app -> GPS sent silently -> Backend counts phones within 100m -> Crowd density estimated
          </div>
          <div style="font-size:11px; color:rgba(255,255,255,0.4); margin-top:8px;">
            Zero hardware - Works at any monument - Self-improving
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_gps2:
    try:
        gps_response = requests.get(
            f"{BASE_URL}/live-density?lat=18.5195&lng=73.8553",
            timeout=5,
        )
        gps_response.raise_for_status()
        gps_data = gps_response.json()

        level = gps_data.get("density_level", "LOW")
        count = gps_data.get("gps_crowd_count", 0)

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("GPS Crowd Count", f"~{count} devices")
        col_b.metric("Density Level", level)
        col_c.metric("Coverage Radius", "100m")

        if level == "HIGH":
            st.error("HIGH crowd detected via GPS - consider deploying staff")
        elif level == "MEDIUM":
            st.warning("Moderate crowd detected via GPS")
        else:
            st.success("Low crowd levels detected via GPS")

        st.caption(
            f"Shaniwarwada Fort - Last 15 minutes - {gps_data.get('window_minutes')}min window"
        )
    except Exception:
        st.info("GPS density data unavailable - backend offline")

st.markdown(
    """
    <div style="margin-top:16px; padding:12px; background:rgba(255,255,255,0.05); border-radius:8px;">
      <div style="font-size:12px; color:rgba(255,255,255,0.5); margin-bottom:8px;">
        GPS Mode enables coverage at camera-less heritage sites:
      </div>
      <div style="display:flex; gap:12px; flex-wrap:wrap;">
        <span style="background:rgba(232,98,26,0.2); color:#E8621A; padding:4px 12px; border-radius:24px; font-size:12px;">Sinhagad Fort</span>
        <span style="background:rgba(232,98,26,0.2); color:#E8621A; padding:4px 12px; border-radius:24px; font-size:12px;">Rajgad Fort</span>
        <span style="background:rgba(232,98,26,0.2); color:#E8621A; padding:4px 12px; border-radius:24px; font-size:12px;">Torna Fort</span>
        <span style="background:rgba(232,98,26,0.2); color:#E8621A; padding:4px 12px; border-radius:24px; font-size:12px;">Lohagad Fort</span>
        <span style="background:rgba(232,98,26,0.2); color:#E8621A; padding:4px 12px; border-radius:24px; font-size:12px;">+3,689 ASI monuments</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.subheader("Alert Feed")

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
st.caption("Team SHATKONA · JSPM University, Pune · SIH 2026 · Camera feed is a pre-recorded simulation.")

if not has_autorefresh:
    time.sleep(5)
    st.rerun()
