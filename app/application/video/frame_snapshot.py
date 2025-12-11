from __future__ import annotations

import base64
import os
import subprocess
from pathlib import Path
from typing import Optional, Union

import cv2
import numpy as np

from app.config import VIDEO_SOURCE
from app.domain.object import BBox


VideoSource = Union[str, Path]


def _normalize_source(source: VideoSource | None) -> str:
    """
    Приводит источник видео к строке для cv2/ffmpeg.
    Если source не передан, используется глобальный VIDEO_SOURCE.
    """
    if source is None:
        source = VIDEO_SOURCE
    return str(source)


def _build_basic_auth_header() -> Optional[str]:
    """
    Строит HTTP-заголовок Authorization: Basic ...
    из MEDIA_BASIC_USER / MEDIA_BASIC_PASSWORD.

    Если переменные окружения не заданы — возвращает None.
    """
    user = os.getenv("MEDIA_BASIC_USER")
    password = os.getenv("MEDIA_BASIC_PASSWORD")

    if not user or not password:
        return None

    raw = f"{user}:{password}".encode("utf-8")
    token = base64.b64encode(raw).decode("ascii")
    return f"Authorization: Basic {token}"


def _extract_http_frame_by_timestamp_ffmpeg(
    src: str,
    timestamp_sec: float,
) -> np.ndarray:
    """
    Достаёт один кадр из HTTP(S)/HLS-источника с помощью ffmpeg.

    Логика:
      ffmpeg [-headers "Authorization: Basic ..."] -ss <t> -i <url>
             -frames:v 1 -f image2pipe -vcodec png -

    На stdout получаем PNG-кадр, который декодируем через cv2.imdecode.
    """
    auth_header = _build_basic_auth_header()

    cmd: list[str] = [
        "ffmpeg",
        "-loglevel",
        "error",
    ]

    if auth_header is not None:
        cmd += ["-headers", auth_header]

    cmd += [
        "-ss",
        f"{timestamp_sec:.3f}",
        "-i",
        src,
        "-frames:v",
        "1",
        "-f",
        "image2pipe",
        "-vcodec",
        "png",  # один PNG-кадр в stdout
        "-",
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ffmpeg не найден в PATH. Установи ffmpeg или добавь его в PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"ffmpeg не смог вытащить кадр t={timestamp_sec:.3f}s: {exc.stderr}"
        ) from exc

    data = result.stdout
    if not data:
        raise RuntimeError(
            f"ffmpeg вернул пустой stdout при извлечении кадра t={timestamp_sec:.3f}s"
        )

    img_array = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    if frame is None:
        raise RuntimeError(
            f"Не удалось декодировать кадр из потока ffmpeg для t={timestamp_sec:.3f}s"
        )

    return frame


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

    HTTP(S) / HLS (.m3u8):
      - используем ffmpeg + Basic Auth (MEDIA_BASIC_USER / MEDIA_BASIC_PASSWORD)

    Локальные файлы / RTSP:
      - используем cv2.VideoCapture + seek по кадрам.

    Возвращает BGR-изображение (как в OpenCV).
    """
    src = _normalize_source(video_source)

    # HTTP(S) — работаем через ffmpeg с заголовком Authorization: Basic ...
    if src.startswith(("http://", "https://")):
        return _extract_http_frame_by_timestamp_ffmpeg(src, timestamp_sec)

    # Остальные источники — локальные файлы, rtsp, и т.п.
    cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {src}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps is None or fps <= 0:
            raise RuntimeError("Cannot read FPS from video source")

        # Индекс кадра, ближайший к timestamp_sec
        frame_index = int(round(timestamp_sec * fps))
        if frame_index < 0:
            frame_index = 0

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