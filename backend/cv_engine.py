from __future__ import annotations

import os
from collections import deque
from pathlib import Path
from typing import Deque, Iterable

import cv2
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATHS = (
    PROJECT_ROOT / "backend" / "models" / "yolov8n.pt",
    PROJECT_ROOT / "yolov8n.pt",
)
DEFAULT_CONFIDENCE = float(os.getenv("CV_CONFIDENCE_THRESHOLD", "0.4"))
DEFAULT_ROLLING_WINDOW = int(os.getenv("CV_ROLLING_WINDOW", "5"))
DEFAULT_SAMPLE_INTERVAL_SECONDS = float(os.getenv("CV_SAMPLE_INTERVAL_SECONDS", "1.0"))
DEFAULT_MAX_SAMPLED_FRAMES = int(os.getenv("CV_MAX_SAMPLED_FRAMES", "12"))
PERSON_CLASS_ID = 0

_model: YOLO | None = None


class CVPipelineError(RuntimeError):
    pass


def _resolve_model_path() -> str:
    configured_path = os.getenv("YOLO_MODEL_PATH")
    if configured_path:
        return configured_path

    for path in DEFAULT_MODEL_PATHS:
        if path.exists() and path.stat().st_size > 0:
            return str(path)

    return "yolov8n.pt"


def _get_model() -> YOLO:
    global _model
    if _model is None:
        try:
            _model = YOLO(_resolve_model_path())
        except Exception as exc:
            raise CVPipelineError(f"Unable to load YOLO model: {exc}") from exc
    return _model


def load_model() -> YOLO:
    return _get_model()


def _validate_positive_number(value: float | int, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0")


def _sample_frames(
    video_path: Path,
    interval_seconds: float,
    max_frames: int | None,
) -> Iterable[tuple[float, object]]:
    _validate_positive_number(interval_seconds, "interval_seconds")
    if max_frames is not None:
        _validate_positive_number(max_frames, "max_frames")

    try:
        capture = cv2.VideoCapture(str(video_path))
    except cv2.error as exc:
        raise CVPipelineError(f"Unable to initialize video capture for: {video_path}") from exc

    if not capture.isOpened():
        raise CVPipelineError(f"Unable to open sample video file: {video_path}")

    try:
        fps = capture.get(cv2.CAP_PROP_FPS)
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        duration_seconds = frame_count / fps if fps and fps > 0 else 0

        timestamp_seconds = 0.0
        sampled_frames = 0
        while True:
            try:
                capture.set(cv2.CAP_PROP_POS_MSEC, timestamp_seconds * 1000)
                success, frame = capture.read()
            except cv2.error as exc:
                raise CVPipelineError(f"Unable to read frame from sample video: {video_path}") from exc

            if not success:
                break

            yield timestamp_seconds, frame
            sampled_frames += 1
            if max_frames is not None and sampled_frames >= max_frames:
                break

            timestamp_seconds += interval_seconds

            if duration_seconds and timestamp_seconds > duration_seconds:
                break
    finally:
        capture.release()


def _count_people_in_frame(frame: object, confidence: float, model: YOLO) -> int:
    try:
        results = model.predict(
            source=frame,
            classes=[PERSON_CLASS_ID],
            conf=confidence,
            verbose=False,
        )
    except Exception as exc:
        raise CVPipelineError(f"Person detection failed: {exc}") from exc

    if not results or results[0].boxes is None:
        return 0

    return len(results[0].boxes)


def get_sampled_counts(
    video_path: str,
    *,
    sample_interval_seconds: float = DEFAULT_SAMPLE_INTERVAL_SECONDS,
    max_sampled_frames: int | None = DEFAULT_MAX_SAMPLED_FRAMES,
    confidence: float = DEFAULT_CONFIDENCE,
) -> list[int]:
    path = Path(video_path)
    if not path.exists():
        raise CVPipelineError(f"Sample video file not found: {path}")
    if not path.is_file():
        raise CVPipelineError(f"Sample video path is not a file: {path}")

    model = _get_model()
    counts = [
        _count_people_in_frame(frame, confidence, model)
        for _, frame in _sample_frames(path, sample_interval_seconds, max_sampled_frames)
    ]
    if not counts:
        raise CVPipelineError(f"No readable frames found in sample video: {path}")
    return counts


def smooth_counts(counts: Iterable[int], rolling_window: int = DEFAULT_ROLLING_WINDOW) -> int:
    _validate_positive_number(rolling_window, "rolling_window")

    recent_counts: Deque[int] = deque(maxlen=rolling_window)
    smoothed_count = 0

    for count in counts:
        recent_counts.append(count)
        smoothed_count = round(sum(recent_counts) / len(recent_counts))

    return smoothed_count


def get_current_count(
    video_path: str,
    *,
    rolling_window: int = DEFAULT_ROLLING_WINDOW,
    sample_interval_seconds: float = DEFAULT_SAMPLE_INTERVAL_SECONDS,
    max_sampled_frames: int | None = DEFAULT_MAX_SAMPLED_FRAMES,
    confidence: float = DEFAULT_CONFIDENCE,
) -> int:
    counts = get_sampled_counts(
        video_path,
        sample_interval_seconds=sample_interval_seconds,
        max_sampled_frames=max_sampled_frames,
        confidence=confidence,
    )
    return smooth_counts(counts, rolling_window=rolling_window)


if __name__ == "__main__":
    sample_videos = {
        "low_crowd": PROJECT_ROOT / "data" / "sample_videos" / "low_crowd.mp4",
        "high_crowd": PROJECT_ROOT / "data" / "sample_videos" / "high_crowd.mp4",
    }

    for label, path in sample_videos.items():
        try:
            counts = get_sampled_counts(str(path))
            smoothed_count = smooth_counts(counts)
            print(f"{label}: smoothed_count={smoothed_count}, sampled_counts={counts}")
        except (FileNotFoundError, ValueError) as exc:
            print(f"{label}: error={exc}")
