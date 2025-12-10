from __future__ import annotations

import os
from typing import Optional

from app.infrastructure.db.postgres import PostgresDatabase
from app.infrastructure.repositories.source_postgres_repository import (
    SourcePostgresRepository,
)

MEDIA_BASE_URL = os.getenv("MEDIA_BASE_URL", "http://localhost:8000")
SNAPSHOT_BASE_URL = os.getenv("SNAPSHOT_BASE_URL", "http://localhost:8001")


async def build_video_url(
    db: PostgresDatabase,
    *,
    source_id: str,
    start_at: str,
    end_at: str,
) -> str:
    """
    Формирует реальный M3U8 URL.
    Логика полностью повторяет фронтовую buildPeriodVideoUrl.
    """

    repo = SourcePostgresRepository(db)
    source = await repo.find_by_source_id(source_id)

    if source is None:
        # fallback, если в БД нет записи
        source_type_id = 1
    else:
        source_type_id = source.source_type_id

    # WHERE-условие как во фронтовом коде
    where = f"NOT(('{start_at}' > datetimeStop) OR ('{end_at}' < datetimeStart))"

    # timestamp для bypass cache
    ts = int(__import__("time").time() * 1000)

    return (
        f"{MEDIA_BASE_URL}/object/{source_type_id}/{source_id}/m3u8/"
        f"?where={where}&limit=40001&key={ts}"
    )


def build_snapshot_url(
    source_id: str,
    at: str,
    object_id: Optional[str],
) -> str:
    """
    Конструирует URL HTTP-эндпоинта для получения кадра с (или без) bbox.
    """
    base = f"{SNAPSHOT_BASE_URL}/snapshot"
    if object_id is None:
        return f"{base}?source_id={source_id}&at={at}"
    return f"{base}?source_id={source_id}&at={at}&object_id={object_id}"