from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOW_THRESHOLD = 3
HIGH_THRESHOLD = 11


def classify_density(count: int) -> str:
    if count < LOW_THRESHOLD:
        return "LOW"
    if count <= HIGH_THRESHOLD:
        return "MEDIUM"
    return "HIGH"


if __name__ == "__main__":
    try:
        from .cv_engine import get_current_count
    except ImportError:
        from cv_engine import get_current_count

    sample_videos: dict[str, Path] = {
        "low_crowd": PROJECT_ROOT / "data" / "sample_videos" / "low_crowd.mp4",
        "high_crowd": PROJECT_ROOT / "data" / "sample_videos" / "high_crowd.mp4",
    }

    for video_label, path in sample_videos.items():
        try:
            count = get_current_count(str(path))
            density_label = classify_density(count)
            print(f"{video_label}: count={count}, density={density_label}")
        except (FileNotFoundError, ValueError) as exc:
            print(f"{video_label}: error={exc}")
