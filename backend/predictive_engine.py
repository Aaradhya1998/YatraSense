from __future__ import annotations

import csv
from pathlib import Path

try:
    from .density_classifier import classify_density
except ImportError:
    from density_classifier import classify_density


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_PATTERN_PATH = PROJECT_ROOT / "data" / "historical_pattern.csv"
VALID_DAYS = {"Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"}
DENSITY_TO_SCORE = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
DEFAULT_HISTORICAL_DENSITY = "MEDIUM"


def _load_historical_pattern(path: Path = HISTORICAL_PATTERN_PATH) -> dict[tuple[str, int], str]:
    if not path.exists():
        raise FileNotFoundError(f"Historical pattern file not found: {path}")

    with path.open(newline="", encoding="utf-8") as csv_file:
        rows = (line for line in csv_file if not line.lstrip().startswith("#"))
        reader = csv.DictReader(rows)
        pattern: dict[tuple[str, int], str] = {}

        for row in reader:
            day = row["day_of_week"]
            hour = int(row["hour"])
            density = row["expected_density"]
            pattern[(day, hour)] = density

    return pattern


def _expected_density_for(day_of_week: str, hour: int) -> str:
    if day_of_week not in VALID_DAYS:
        raise ValueError(f"day_of_week must be one of {sorted(VALID_DAYS)}")
    if not 0 <= hour <= 23:
        raise ValueError("hour must be between 0 and 23")

    pattern = _load_historical_pattern()
    return pattern.get((day_of_week, hour), DEFAULT_HISTORICAL_DENSITY)


def _calculate_trend_slope(recent_counts: list[int]) -> float:
    if not recent_counts:
        raise ValueError("recent_counts must contain at least one count")
    if len(recent_counts) == 1:
        return 0.0

    recent_density_levels = [
        DENSITY_TO_SCORE[classify_density(count)]
        for count in recent_counts
    ]
    return (recent_density_levels[-1] - recent_density_levels[0]) / len(recent_density_levels)


def _score_to_density_label(forecast_score: float) -> str:
    if forecast_score < 0.5:
        return "LOW"
    if forecast_score < 1.0:
        return "MEDIUM"
    return "HIGH"


def get_forecast(recent_counts: list[int], day_of_week: str, hour: int) -> dict[str, int | str]:
    trend_slope = _calculate_trend_slope(recent_counts)
    expected_density = _expected_density_for(day_of_week, hour)
    historical_component = DENSITY_TO_SCORE[expected_density]

    forecast_score = (0.6 * trend_slope) + (0.4 * historical_component)
    label = _score_to_density_label(forecast_score)
    eta_minutes = 20

    return {
        "label": label,
        "text": f"Likely to reach {label} in ~{eta_minutes} minutes",
        "eta_minutes": eta_minutes,
    }
