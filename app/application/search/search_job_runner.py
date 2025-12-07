from __future__ import annotations

import asyncio
from uuid import uuid4

from app.application.search.search_service import search_by_text

from app.domain.search_job import SearchJob
from app.domain.value_objects import SearchJobId
from app.domain.repositories.search_job_repository import SearchJobRepository

from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.search_job_postgres_repository import (
    SearchJobPostgresRepository,
)

from app.domain.search_job_event import SearchJobEvent
from app.domain.value_objects import SearchJobResultId, ObjectId
from app.infrastructure.repositories.search_job_event_postgres_repository import (
    SearchJobEventPostgresRepository,
)


async def _run_job(job_id: SearchJobId) -> None:
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    job_repo = SearchJobPostgresRepository(db)
    event_repo = SearchJobEventPostgresRepository(db)

    try:
        job = await job_repo.find_by_id(job_id)
        if job is None:
            return

        await job_repo.update_status(job_id, "RUNNING", None)
        await job_repo.update_progress(job_id, 1.0)

        # 1. Поиск
        hits = await search_by_text(
            db=db,
            text=job.text_query,
            source_id=job.source_id,
            start_at=job.start_at,
            end_at=job.end_at,
        )

        await job_repo.update_progress(job_id, 20.0)

        # 2. Сохранение событий поиска
        events: list[SearchJobEvent] = []
        for hit in hits:
            # Ожидается, что hit содержит:
            #   - hit.track_id: Optional[int]
            #   - hit.object_id: Optional[UUID / ObjectId-like]
            #   - hit.final_score: float
            events.append(
                SearchJobEvent(
                    id=SearchJobResultId(uuid4()),
                    job_id=job_id,
                    track_id=getattr(hit, "track_id", None),
                    object_id=ObjectId(hit.object_id) if hit.object_id is not None else None,
                    score=hit.final_score,
                )
            )

        await event_repo.create_many(events)

        await job_repo.update_progress(job_id, 100.0)
        await job_repo.update_status(job_id, "DONE", None)

    except Exception as exc:
        await job_repo.update_status(job_id, "FAILED", str(exc))
        raise
    finally:
        await db.close()


async def create_job(
    repo: SearchJobRepository,
    db: PostgresDatabase,
    *,
    title: str,
    text_query: str,
    source_id: str,
    start_at: str,
    end_at: str,
) -> SearchJobId:
    """
    Регистрирует задачу в БД и запускает воркер в фоне.
    """
    job_id = SearchJobId(str(uuid4()))

    job = SearchJob(
        id=job_id,
        title=title,
        text_query=text_query,
        source_id=source_id,
        start_at=start_at,
        end_at=end_at,
        progress=0.0,
        status="PENDING",
        error=None,
    )
    await repo.create(job)

    asyncio.create_task(_run_job(job_id))

    return job_id