from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import cv2
import numpy as np

from app.config import VIDEO_PATH, TARGET_FPS


@dataclass(frozen=True)
class RawFrame:
    """
    "Сырой" кадр из видео.

    index:
        Порядковый номер выбранного кадра после даунсэмплинга.
    timestamp_sec:
        Время в секундах от начала видео (по исходному FPS).
    image:
        Кадр в формате BGR (как даёт OpenCV).
    """
    index: int
    timestamp_sec: float
    image: np.ndarray


def iter_video_frames(
    video_path: Path,
    target_fps: float,
) -> Iterator[RawFrame]:
    """
    Чистая функция: на вход путь к видео и нужный FPS,
    на выход — поток RawFrame.

    Никаких репозиториев и БД.
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps is None or fps <= 0:
            raise RuntimeError(f"Cannot read FPS for: {video_path}")

        step = max(1, int(round(fps / target_fps)))

        src_index = 0
        out_index = 0

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            if src_index % step == 0:
                timestamp = src_index / fps
                yield RawFrame(
                    index=out_index,
                    timestamp_sec=timestamp,
                    image=frame,
                )
                out_index += 1

            src_index += 1

    finally:
        cap.release()


def iter_default_video_frames() -> Iterator[RawFrame]:
    return iter_video_frames(VIDEO_PATH, TARGET_FPS)