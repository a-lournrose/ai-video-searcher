from __future__ import annotations

import base64
import os
import subprocess
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
    Приводит источник видео к строке, приемлемой для cv2/ffmpeg.

    Поддерживает:
      - Path
      - локальные файлы
      - http(s) ссылки (включая .m3u8)
      - rtsp
    """
    if isinstance(source, Path):
        return str(source)
    return source


def _build_basic_auth_header() -> str | None:
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


def _iter_frames_via_ffmpeg_http(
    src: str,
    target_fps: float,
) -> Iterator[RawFrame]:
    """
    Читает HTTP(S)/HLS (m3u8) поток через системный ffmpeg и
    отдаёт кадры как RawFrame.

    Авторизация:
      - заголовок Authorization: Basic ... передаётся явно через -headers
      - URL берётся как есть (без user:pass@host), такой же, как в curl.
    """
    auth_header = _build_basic_auth_header()

    # 1) Получаем ширину/высоту через ffprobe
    probe_cmd: list[str] = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=s=x:p=0",
    ]

    if auth_header is not None:
        probe_cmd += ["-headers", auth_header]

    probe_cmd.append(src)

    try:
        probe_result = subprocess.run(
            probe_cmd,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ffprobe не найден в PATH. Установи ffmpeg (ffprobe) "
            "или добавь его в PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(
            f"Не удалось получить параметры видео через ffprobe: {exc.stderr}"
        ) from exc

    stdout = probe_result.stdout
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]

    if not lines:
        raise RuntimeError(
            f"ffprobe вернул пустой вывод для определения размера кадра. "
            f"stdout={stdout!r}"
        )

    # Берём первую валидную строку, даже если их несколько (как у тебя: 640x360, 640x360)
    line = lines[0]

    if "x" not in line:
        raise RuntimeError(
            f"ffprobe вернул некорректную строку размера кадра: {line!r}, "
            f"stdout={stdout!r}"
        )

    try:
        width_str, height_str = line.split("x", 1)
        width = int(width_str)
        height = int(height_str)
    except ValueError as exc:
        raise RuntimeError(
            f"Не удалось распарсить размер кадра из строки: {line!r}, "
            f"stdout={stdout!r}"
        ) from exc

    frame_size = width * height * 3  # bgr24: 3 байта на пиксель

    # 2) Стартуем ffmpeg, который будет гнать сырые кадры в stdout
    ffmpeg_cmd: list[str] = [
        "ffmpeg",
        "-loglevel",
        "error",
    ]

    if auth_header is not None:
        ffmpeg_cmd += ["-headers", auth_header]

    ffmpeg_cmd += [
        "-i",
        src,
        "-an",
        "-vf",
        f"fps={target_fps}",
        "-f",
        "image2pipe",
        "-pix_fmt",
        "bgr24",
        "-vcodec",
        "rawvideo",
        "-",
    ]

    try:
        process = subprocess.Popen(
            ffmpeg_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=frame_size,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "ffmpeg не найден в PATH. Установи ffmpeg или добавь его в PATH."
        ) from exc

    index = 0
    try:
        if process.stdout is None:
            raise RuntimeError("Не удалось открыть stdout ffmpeg.")

        while True:
            raw = process.stdout.read(frame_size)
            if not raw or len(raw) < frame_size:
                break

            frame = np.frombuffer(raw, dtype=np.uint8)
            frame = frame.reshape((height, width, 3))

            timestamp_sec = index / float(target_fps)

            yield RawFrame(
                index=index,
                timestamp_sec=timestamp_sec,
                image=frame,
            )
            index += 1

    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        return_code = process.returncode
        if return_code not in (0, None):
            stderr = (
                process.stderr.read().decode("utf-8", errors="replace")
                if process.stderr
                else ""
            )
            raise RuntimeError(
                f"ffmpeg завершился с кодом {return_code}. "
                f"Детали: {stderr}"
            )


def _iter_frames_via_opencv(
    src: str,
    target_fps: float,
) -> Iterator[RawFrame]:
    """
    Классический путь через cv2.VideoCapture — для локальных файлов и rtsp.
    """
    cap = cv2.VideoCapture(src, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video source: {src}")

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)

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

            if src_index % step == 0:
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


def iter_video_frames(
    video_source: VideoSource,
    target_fps: float,
) -> Iterator[RawFrame]:
    """
    Универсальный итератор кадров.

    - Для HTTP(S) / HLS (m3u8 и т.п.) — используем внешний ffmpeg/ffprobe
      с явным заголовком Authorization: Basic ...
    - Для локальных файлов / rtsp — используем OpenCV VideoCapture.
    """
    src = _normalize_source(video_source)

    if isinstance(src, str) and src.startswith(("http://", "https://")):
        yield from _iter_frames_via_ffmpeg_http(src, target_fps)
    else:
        yield from _iter_frames_via_opencv(src, target_fps)


def iter_default_video_frames() -> Iterator[RawFrame]:
    return iter_video_frames(VIDEO_SOURCE, TARGET_FPS)