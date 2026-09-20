import json
from datetime import datetime, timedelta
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHECKINS_FILE = PROJECT_ROOT / "data" / "gps_checkins.json"
RADIUS_METERS = 100  # count phones within 100m
WINDOW_MINUTES = 15  # only count last 15 minutes


def load_checkins():
    if not CHECKINS_FILE.exists():
        return []

    try:
        with CHECKINS_FILE.open(encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_checkins(checkins):
    CHECKINS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with CHECKINS_FILE.open("w", encoding="utf-8") as f:
        json.dump(checkins, f)


def haversine_distance(lat1, lng1, lat2, lng2):
    # Returns distance in meters between two GPS coordinates.
    earth_radius = 6371000
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius * c


def add_checkin(lat: float, lng: float, place_id: str = "unknown"):
    checkins = load_checkins()
    checkins.append(
        {
            "lat": lat,
            "lng": lng,
            "place_id": place_id,
            "timestamp": datetime.now().isoformat(),
        }
    )
    # Keep only last 1000 checkins to prevent file bloat.
    checkins = checkins[-1000:]
    save_checkins(checkins)


def get_gps_density(lat: float, lng: float):
    checkins = load_checkins()
    now = datetime.now()
    cutoff = now - timedelta(minutes=WINDOW_MINUTES)

    nearby_count = 0
    for checkin in checkins:
        try:
            checkin_time = datetime.fromisoformat(checkin["timestamp"])
            if checkin_time < cutoff:
                continue

            distance = haversine_distance(lat, lng, checkin["lat"], checkin["lng"])
            if distance <= RADIUS_METERS:
                nearby_count += 1
        except (KeyError, TypeError, ValueError):
            continue

    if nearby_count < 3:
        level = "LOW"
    elif nearby_count <= 10:
        level = "MEDIUM"
    else:
        level = "HIGH"

    return {
        "gps_crowd_count": nearby_count,
        "density_level": level,
        "radius_meters": RADIUS_METERS,
        "window_minutes": WINDOW_MINUTES,
        "mode": "GPS_CLUSTERING",
        "note": "Estimated from tourist device locations - no camera required",
    }
