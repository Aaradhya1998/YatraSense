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
DEFAULT_CLUSTER_DISTANCE_PIXELS = 150
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


def _read_representative_frame(video_path: Path) -> object:
    if not video_path.exists():
        raise CVPipelineError(f"Sample video file not found: {video_path}")
    if not video_path.is_file():
        raise CVPipelineError(f"Sample video path is not a file: {video_path}")

    try:
        capture = cv2.VideoCapture(str(video_path))
    except cv2.error as exc:
        raise CVPipelineError(f"Unable to initialize video capture for: {video_path}") from exc

    if not capture.isOpened():
        raise CVPipelineError(f"Unable to open sample video file: {video_path}")

    try:
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if frame_count > 1:
            capture.set(cv2.CAP_PROP_POS_FRAMES, max(1, frame_count // 2))
        else:
            capture.set(cv2.CAP_PROP_POS_MSEC, 1000)

        success, frame = capture.read()
        if not success or frame is None:
            raise CVPipelineError(f"Unable to read representative frame from: {video_path}")
        return frame
    except cv2.error as exc:
        raise CVPipelineError(f"Unable to read representative frame from: {video_path}") from exc
    finally:
        capture.release()


def _detect_person_boxes(frame: object, model: YOLO, confidence: float) -> list[tuple[int, int, int, int]]:
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
        return []

    return [
        tuple(round(value) for value in box)
        for box in results[0].boxes.xyxy.cpu().tolist()
    ]


def _find_person_clusters(
    boxes: list[tuple[int, int, int, int]],
    distance_pixels: int = DEFAULT_CLUSTER_DISTANCE_PIXELS,
) -> list[list[int]]:
    parent = list(range(len(boxes)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    centers = [((x1 + x2) / 2, (y1 + y2) / 2) for x1, y1, x2, y2 in boxes]
    max_distance_squared = distance_pixels * distance_pixels

    for left_index, (left_x, left_y) in enumerate(centers):
        for right_index in range(left_index + 1, len(centers)):
            right_x, right_y = centers[right_index]
            distance_squared = ((left_x - right_x) ** 2) + ((left_y - right_y) ** 2)
            if distance_squared <= max_distance_squared:
                union(left_index, right_index)

    clusters_by_root: dict[int, list[int]] = {}
    for index in range(len(boxes)):
        clusters_by_root.setdefault(find(index), []).append(index)

    return list(clusters_by_root.values())


def _draw_person_annotations(
    frame: object,
    boxes: list[tuple[int, int, int, int]],
    group_threshold: int,
) -> object:
    for x1, y1, x2, y2 in boxes:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)

    for cluster in _find_person_clusters(boxes):
        if len(cluster) <= group_threshold:
            continue

        cluster_boxes = [boxes[index] for index in cluster]
        x1 = min(box[0] for box in cluster_boxes)
        y1 = min(box[1] for box in cluster_boxes)
        x2 = max(box[2] for box in cluster_boxes)
        y2 = max(box[3] for box in cluster_boxes)

        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
        label = f"Group: {len(cluster)}"
        label_y = max(20, y1 - 8)
        cv2.putText(
            frame,
            label,
            (x1, label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    return frame


def get_annotated_frame(video_path: str, group_threshold: int = 5) -> bytes:
    _validate_positive_number(group_threshold, "group_threshold")

    frame = _read_representative_frame(Path(video_path))
    model = _get_model()
    boxes = _detect_person_boxes(frame, model, DEFAULT_CONFIDENCE)
    _draw_person_annotations(frame, boxes, group_threshold)

    success, encoded_frame = cv2.imencode(".png", frame)
    if not success:
        raise CVPipelineError("Unable to encode annotated frame as PNG")

    return encoded_frame.tobytes()


def stream_annotated_frames(
    video_path: str,
    group_threshold: int = 5,
    frame_skip: int = 1,
) -> Iterable[bytes]:
    _validate_positive_number(group_threshold, "group_threshold")
    _validate_positive_number(frame_skip, "frame_skip")

    path = Path(video_path)
    if not path.exists():
        raise CVPipelineError(f"Sample video file not found: {path}")
    if not path.is_file():
        raise CVPipelineError(f"Sample video path is not a file: {path}")

    model = _get_model()

    try:
        capture = cv2.VideoCapture(str(path))
    except cv2.error as exc:
        raise CVPipelineError(f"Unable to initialize video capture for: {path}") from exc

    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not capture.isOpened():
        raise CVPipelineError(f"Unable to open sample video file: {path}")

    frame_index = 0
    last_boxes: list[tuple[int, int, int, int]] = []
    consecutive_read_failures = 0

    try:
        while True:
            try:
                success, frame = capture.read()
            except cv2.error as exc:
                raise CVPipelineError(f"Unable to read frame from sample video: {path}") from exc

            if not success or frame is None:
                consecutive_read_failures += 1
                if consecutive_read_failures > 1:
                    raise CVPipelineError(f"No readable frames found in sample video: {path}")

                capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                frame_index = 0
                last_boxes = []
                continue

            consecutive_read_failures = 0

            if frame_index % frame_skip == 0:
                last_boxes = _detect_person_boxes(frame, model, DEFAULT_CONFIDENCE)

            _draw_person_annotations(frame, last_boxes, group_threshold)

            success, encoded_frame = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 60],
            )
            if not success:
                raise CVPipelineError("Unable to encode annotated frame as JPEG")

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + encoded_frame.tobytes()
                + b"\r\n"
            )
            frame_index += 1
    finally:
        capture.release()


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
