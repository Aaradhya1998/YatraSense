from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "data" / "historical_pattern.csv"
DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def expected_density_for(day_of_week: str, hour: int) -> str:
    is_weekend = day_of_week in {"Sat", "Sun"}

    if is_weekend:
        if 10 <= hour <= 13 or 17 <= hour <= 19:
            return "HIGH"
        if 8 <= hour <= 20:
            return "MEDIUM"
        return "LOW"

    if 6 <= hour <= 10:
        return "LOW"
    if 17 <= hour <= 19:
        return "MEDIUM" if day_of_week in {"Mon", "Tue", "Wed", "Thu"} else "HIGH"
    if 11 <= hour <= 16:
        return "MEDIUM"
    return "LOW"


def generate_historical_pattern() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as csv_file:
        csv_file.write("# Synthetic illustrative data for demo only; not real monument footfall.\n")

        writer = csv.DictWriter(
            csv_file,
            fieldnames=("day_of_week", "hour", "expected_density"),
        )
        writer.writeheader()

        for day in DAYS:
            for hour in range(24):
                writer.writerow(
                    {
                        "day_of_week": day,
                        "hour": hour,
                        "expected_density": expected_density_for(day, hour),
                    }
                )


if __name__ == "__main__":
    generate_historical_pattern()
    print(f"Generated {OUTPUT_PATH}")
