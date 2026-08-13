from __future__ import annotations

from datetime import datetime


HIGH_DENSITY = "HIGH"
DENSITY_ALERT_TYPE = "DENSITY"
SOS_ALERT_TYPE = "SOS"

current_density_state: str | None = None
previous_density_state: str | None = None
alert_events: list[dict[str, str]] = []


def check_and_get_alert(current_density: str) -> dict[str, str] | None:
    global current_density_state, previous_density_state

    normalized_density = current_density.upper()
    previous_density_state = current_density_state
    current_density_state = normalized_density

    if previous_density_state == HIGH_DENSITY or current_density_state != HIGH_DENSITY:
        return None

    alert = {
        "timestamp": datetime.now().replace(microsecond=0).isoformat(),
        "message": "Density crossed into HIGH",
        "type": DENSITY_ALERT_TYPE,
        "density_at_trigger": current_density_state,
    }
    alert_events.append(alert)
    return alert


def trigger_sos_alert(message: str) -> dict[str, str]:
    alert = {
        "timestamp": datetime.now().replace(microsecond=0).isoformat(),
        "message": message,
        "type": SOS_ALERT_TYPE,
    }
    alert_events.append(alert)
    return alert


def get_alert_events() -> list[dict[str, str]]:
    return alert_events
