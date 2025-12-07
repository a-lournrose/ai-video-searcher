from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List, Optional

from app.domain.value_objects import SearchJobId, ObjectId
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.search_job_postgres_repository import (
    SearchJobPostgresRepository,
)
from app.infrastructure.repositories.search_job_event_postgres_repository import (
    SearchJobEventPostgresRepository,
)
from app.application.video.source_url_builder import build_snapshot_url


async def _list_event_frames_internal(
    db: PostgresDatabase,
    job_id: SearchJobId,
    track_id: int,
) -> List[Dict[str, Any]]:
    """
    Возвращает все объекты/кадры внутри одного события (одного трека)
    для конкретной задачи поиска.
    """
    job_repo = SearchJobPostgresRepository(db)
    event_repo = SearchJobEventPostgresRepository(db)

    job = await job_repo.find_by_id(job_id)
    if job is None:
        return []

    events = await event_repo.find_by_job_id(job_id)

    filtered = [
        e
        for e in events
        if e.track_id == track_id and e.object_id is not None
    ]
    if not filtered:
        return []

    async def _fetch_at_for_object(obj_id: ObjectId) -> Optional[str]:
        row = await db.fetchrow(
            """
            SELECT f.at
            FROM objects o
            JOIN frames f ON o.frame_id = f.id
            WHERE o.id = $1
            """,
            obj_id,
        )
        if row is None:
            return None
        return row["at"]

    items: List[Dict[str, Any]] = []

    for e in filtered:
        assert e.object_id is not None

        at = await _fetch_at_for_object(e.object_id)
        if at is None:
            continue

        url = build_snapshot_url(
            source_id=job.source_id,
            at=at,
            object_id=str(e.object_id),
        )

        items.append(
            {
                "event_id": str(e.id),
                "job_id": str(job_id),
                "track_id": track_id,
                "object_id": str(e.object_id),
                "score": e.score,
                "at": at,
                "url": url,
            }
        )

    items.sort(key=lambda it: it["at"])
    return items


async def list_event_frames_usecase(
    job_id: str,
    track_id: int,
) -> List[Dict[str, Any]]:
    """
    Facade-usecase для получения кадров внутри события.
    """
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    try:
        return await _list_event_frames_internal(
            db=db,
            job_id=SearchJobId(job_id),
            track_id=track_id,
        )
    finally:
        await db.close()


# ====== CLI-демо ======

JOB_ID = "aa08b1e4-5af9-47f7-9f4a-4cc4f0cd9cdb"
TRACK_ID = 1


async def main() -> None:
    frames = await list_event_frames_usecase(JOB_ID, TRACK_ID)
    print(json.dumps(frames, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())