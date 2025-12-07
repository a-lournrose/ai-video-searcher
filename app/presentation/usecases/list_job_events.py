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
from app.application.search.search_service import search_by_text


async def _list_job_events_internal(
    db: PostgresDatabase,
    job_id: SearchJobId,
) -> List[Dict[str, Any]]:
    job_repo = SearchJobPostgresRepository(db)
    event_repo = SearchJobEventPostgresRepository(db)

    job = await job_repo.find_by_id(job_id)
    if job is None:
        return []

    # Все события, которые воркер уже сохранил
    events = await event_repo.find_by_job_id(job_id)

    # --- helper-функции -----------------------------------------------------

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

    async def _fetch_at_for_frame(frame_id: str) -> Optional[str]:
        row = await db.fetchrow(
            """
            SELECT at
            FROM frames
            WHERE id = $1
            """,
            frame_id,
        )
        if row is None:
            return None
        return row["at"]

    items: List[Dict[str, Any]] = []

    # -----------------------------------------------------------------------
    # 1) Сценарий OBJECT: есть хотя бы одно событие с object_id != NULL
    # -----------------------------------------------------------------------
    object_events = [e for e in events if e.object_id is not None]

    if object_events:
        by_track: Dict[int, List[Any]] = {}
        single_events: List[Any] = []

        for e in object_events:
            if e.track_id is not None:
                by_track.setdefault(e.track_id, []).append(e)
            else:
                single_events.append(e)

        # Группы по track_id
        for track_id, group in by_track.items():
            # лучший по score объект
            best = max(group, key=lambda ev: ev.score)
            assert best.object_id is not None

            # собираем все at для интервала события
            ats: List[str] = []
            for ev in group:
                assert ev.object_id is not None
                at_ev = await _fetch_at_for_object(ev.object_id)
                if at_ev is not None:
                    ats.append(at_ev)

            if not ats:
                continue

            start_at = min(ats)
            end_at = max(ats)

            # at для превью (лучший объект)
            preview_at = await _fetch_at_for_object(best.object_id)
            if preview_at is None:
                continue

            preview_url = build_snapshot_url(
                source_id=job.source_id,
                at=preview_at,
                object_id=str(best.object_id),
            )

            items.append(
                {
                    "kind": "event",
                    "track_id": track_id,
                    "job_id": str(job_id),
                    "best_score": best.score,
                    "best_object_id": str(best.object_id),
                    "preview_url": preview_url,
                    "start_at": start_at,
                    "end_at": end_at,
                    "at": preview_at,
                }
            )

        # События без track_id — по одному объекту
        for e in single_events:
            assert e.object_id is not None

            at = await _fetch_at_for_object(e.object_id)
            if at is None:
                continue

            preview_url = build_snapshot_url(
                source_id=job.source_id,
                at=at,
                object_id=str(e.object_id),
            )

            items.append(
                {
                    "kind": "event",
                    "track_id": None,
                    "job_id": str(job_id),
                    "best_score": e.score,
                    "best_object_id": str(e.object_id),
                    "preview_url": preview_url,
                    "start_at": at,
                    "end_at": at,
                    "at": at,
                }
            )

        items.sort(key=lambda it: it["best_score"], reverse=True)
        return items

    # -----------------------------------------------------------------------
    # 2) Сценарий FRAME: объектных событий нет → считаем, что поиск по кадрам
    #    и пересчитываем хиты через search_by_text.
    # -----------------------------------------------------------------------

    # Если даже событий нет, возможно, воркер ещё не успел отработать
    # или задача упала — на этот случай просто вернём пустой список.
    # Можно добавить проверку статуса job.status == 'DONE', если нужно.
    if not events:
        return []

    # Пересчитываем хиты только по кадрам
    hits = await search_by_text(
        db=db,
        source_id=job.source_id,
        start_at=job.start_at,
        end_at=job.end_at,
        text=job.text_query,
    )

    frame_hits = [h for h in hits if h.target_type == "frame"]
    if not frame_hits:
        return []

    for hit in frame_hits:
        at = await _fetch_at_for_frame(hit.frame_id)
        if at is None:
            continue

        preview_url = build_snapshot_url(
            source_id=job.source_id,
            at=at,
            object_id=None,
        )

        items.append(
            {
                "kind": "frame",
                "track_id": None,
                "job_id": str(job_id),
                "best_score": hit.final_score,
                "best_object_id": None,
                "preview_url": preview_url,
                "start_at": None,
                "end_at": None,
                "at": at,
            }
        )

    items.sort(key=lambda it: it["best_score"], reverse=True)
    return items


async def list_job_events_usecase(job_id: str) -> List[Dict[str, Any]]:
    """
    Facade-usecase для слоя presentation.
    """
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    try:
        return await _list_job_events_internal(db, SearchJobId(job_id))
    finally:
        await db.close()


# ====== CLI-демо ======

JOB_ID = "aa08b1e4-5af9-47f7-9f4a-4cc4f0cd9cdb"


async def main() -> None:
    items = await list_job_events_usecase(JOB_ID)
    print(json.dumps(items, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())