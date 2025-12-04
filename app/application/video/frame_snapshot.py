from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

from app.config import VIDEO_SOURCE
from app.domain.object import BBox

VideoSource = Union[str, Path]


def _normalize_source(source: VideoSource | None) -> str:
    """
    Приводит источник видео к строке для cv2.VideoCapture.
    Если source не передан, используется глобальный VIDEO_SOURCE.
    """
    if source is None:
        source = VIDEO_SOURCE
    return str(source)


def extract_frame_by_timestamp(
    timestamp_sec: float,
    video_source: VideoSource | None = None,
) -> np.ndarray:
    """
    Достаёт кадр из видео по timestamp_sec (в секундах).

    video_source:
      - None  -> берём значение из app.config.VIDEO_SOURCE
      - str   -> URL (HLS m3u8, RTSP, локальный путь) или путь-строка
      - Path  -> локальный путь к файлу

    Возвращает BGR-изображение (как в OpenCV).
    """
    src = _normalize_source(video_source)

    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {src}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            raise RuntimeError("Cannot read FPS from video source")

        # Индекс кадра, ближайший к timestamp_sec
        frame_index = int(round(timestamp_sec * fps))
        if frame_index < 0:
            frame_index = 0

        # Для сетевых источников (HLS/RTSP) seek может работать не идеально,
        # но это нормальное поведение для VideoCapture.
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)

        ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError(
                f"Cannot read frame at index {frame_index} (t={timestamp_sec:.3f}s)"
            )

        return frame

    finally:
        cap.release()


def draw_bbox_on_frame(
    frame_bgr: np.ndarray,
    bbox: Optional[BBox],
) -> np.ndarray:
    """
    Рисует прямоугольник по bbox на копии кадра.
    Если bbox is None — возвращает копию без изменений.
    """
    out = frame_bgr.copy()

    if bbox is None:
        return out

    x1 = int(bbox.x)
    y1 = int(bbox.y)
    x2 = int(bbox.x + bbox.width)
    y2 = int(bbox.y + bbox.height)

    # Красная рамка толщиной 2 пикселя (BGR: красный)
    cv2.rectangle(out, (x1, y1), (x2, y2), (0, 0, 255), 2)

    return out


def save_frame_with_optional_bbox(
    timestamp_sec: float,
    out_path: Path,
    bbox: Optional[BBox] = None,
    video_source: VideoSource | None = None,
) -> None:
    """
    Достаёт кадр по timestamp_sec, рисует рамку (если bbox не None)
    и сохраняет в out_path (JPG/PNG — по расширению файла).

    video_source — см. extract_frame_by_timestamp.
    """
    frame = extract_frame_by_timestamp(timestamp_sec, video_source=video_source)
    frame_drawn = draw_bbox_on_frame(frame, bbox)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if not cv2.imwrite(str(out_path), frame_drawn):
        raise RuntimeError(f"Failed to write image to {out_path}")
