from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Union

import cv2
import numpy as np

from app.config import VIDEO_SOURCE, TARGET_FPS


VideoSource = Union[str, Path]


@dataclass(frozen=True)
class RawFrame:
    index: int
    timestamp_sec: float
    image: np.ndarray


def _normalize_source(source: VideoSource) -> str:
    """
    Приводит источник видео к строке, приемлемой для cv2.VideoCapture.
    Поддерживает:
      - Path
      - локальные файлы
      - http(s) ссылки (включая .m3u8)
      - rtsp
    """
    if isinstance(source, Path):
        return str(source)
    return source


def iter_video_frames(
    video_source: VideoSource,
    target_fps: float,
) -> Iterator[RawFrame]:
    """
    Чистая функция: на вход источник видео и целевой FPS,
    на выход — поток RawFrame.

    Работает и с локальными файлами, и с URL (m3u8 / ts / HLS).
    """
    src = _normalize_source(video_source)

    cap = cv2.VideoCapture(src)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {src}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)

        # Для HLS fps часто возвращается как 0 — это нормально.
        # Тогда мы не можем рассчитывать правильный timestamp.
        # Поэтому выбираем безопасный вариант: читаем кадры как есть.
        if fps is None or fps <= 0:
            fps = None
            step = 1
        else:
            step = max(1, int(round(fps / target_fps)))

        src_index = 0
        out_index = 0

        while True:
            ok, frame = cap.read()
            if not ok:
                break

            # для m3u8 кадров бывает много, но fps неизвестно
            if src_index % step == 0:
                # timestamp для файлов — реальный
                # timestamp для HLS (fps неизвестно) — равен индексу
                timestamp = (src_index / fps) if fps else float(src_index)

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
    return iter_video_frames(VIDEO_SOURCE, TARGET_FPS)