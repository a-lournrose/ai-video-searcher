from __future__ import annotations

from typing import Optional

import cv2

from app.application.video.frame_snapshot import (
    extract_frame_by_timestamp,
    draw_bbox_on_frame,
)
from app.application.video.source_url_builder import build_video_url
from app.domain.object import BBox
from app.infrastructure.db.postgres import PostgresDatabase


class SnapshotNotFoundError(Exception):
    pass


class SnapshotGenerationError(Exception):
    pass


async def get_snapshot_jpeg(
    db: PostgresDatabase,
    *,
    source_id: str,
    at: str,
    object_id: Optional[str] = None,
) -> bytes:
    """
    Основная бизнес-логика получения снимка кадра.

    1. Находит кадр по (source_id, at) в таблице frames.
    2. Если передан object_id — находит bbox в таблице objects.
    3. Строит video_url через build_video_url.
    4. Достаёт кадр по timestamp_sec и рисует bbox.
    5. Кодирует изображение в JPEG и возвращает bytes.
    """

    # 1. Ищем кадр
    frame_row = await db.fetchrow(
        """
        SELECT id, timestamp_sec
        FROM frames
        WHERE source_id = $1 AND at = $2
        LIMIT 1
        """,
        source_id,
        at,
    )
    if frame_row is None:
        raise SnapshotNotFoundError("Frame not found")

    frame_id = frame_row["id"]
    timestamp_sec = float(frame_row["timestamp_sec"])

    # 2. Ищем bbox (если указан object_id)
    bbox: Optional[BBox] = None

    if object_id is not None:
        object_row = await db.fetchrow(
            """
            SELECT bbox_x, bbox_y, bbox_width, bbox_height
            FROM objects
            WHERE id = $1
            """,
            object_id,
        )
        if object_row is not None:
            bbox = BBox(
                x=object_row["bbox_x"],
                y=object_row["bbox_y"],
                width=object_row["bbox_width"],
                height=object_row["bbox_height"],
            )

    # 3. Строим URL видеопотока
    # Сейчас start_at/end_at нам особо не нужны — можно подставить at.
    video_url = await build_video_url(
        db=db,
        source_id=source_id,
        start_at=at,
        end_at=at,
    )

    # 4. Достаём кадр и рисуем bbox
    frame = extract_frame_by_timestamp(
        timestamp_sec=timestamp_sec,
        video_source=video_url,
    )
    framed = draw_bbox_on_frame(frame, bbox)

    # 5. Кодируем в JPEG
    ok, buffer = cv2.imencode(".jpg", framed)
    if not ok:
        raise SnapshotGenerationError("Failed to encode image to JPEG")

    return buffer.tobytes()
