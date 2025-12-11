from __future__ import annotations

import asyncio
from typing import Dict, List
from uuid import uuid4

from app.domain.vectorization_job import VectorizationJob
from app.domain.value_objects import VectorizationJobId
from app.domain.repositories.vectorization_job_repository import (
    VectorizationJobRepository,
)

from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.vectorization_job_postgres_repository import (
    VectorizationJobPostgresRepository,
)

from app.presentation.usecases.process_video_fragment import (
    process_video_fragment_usecase,
)


async def _run_vectorization_job(job_id: VectorizationJobId) -> None:
    """
    Внутренний воркер для выполнения задачи векторизации.
    """
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    repo = VectorizationJobPostgresRepository(db)

    try:
        job = await repo.find_by_id(job_id)
        if job is None:
            return

        await repo.update_status(job_id, "RUNNING", None)
        await repo.update_progress(job_id, 1.0)

        async def _progress_cb(frac: float) -> None:
            """
            frac: 0.0 .. 1.0 от process_video.
            Маппим в 10..100 для задачи (1% уже поставлен перед запуском).
            """
            progress = 10.0 + 90.0 * max(0.0, min(1.0, frac))
            await repo.update_progress(job_id, progress)

        # Запускаем usecase с прогресс-колбэком:
        await process_video_fragment_usecase(
            source_id=job.source_id,
            source_type_id=job.source_type_id,
            ranges=job.ranges,
            progress_cb=_progress_cb,
        )

        # На всякий случай дожимаем до 100%
        await repo.update_progress(job_id, 100.0)
        await repo.update_status(job_id, "DONE", None)

    except Exception as exc:
        await repo.update_status(job_id, "FAILED", str(exc))
        raise
    finally:
        await db.close()


async def create_vectorization_job(
    source_id: str,
    source_type_id: int,
    ranges: List[Dict[str, str]],
    repo: VectorizationJobRepository,
) -> VectorizationJobId:
    """
    Регистрирует задачу в БД + запускает воркер в фоне.
    """
    job_id = VectorizationJobId(str(uuid4()))

    job = VectorizationJob(
        id=job_id,
        source_id=source_id,
        source_type_id=source_type_id,
        ranges=ranges,
        status="PENDING",
        progress=0.0,
        error=None,
    )
    await repo.create(job)

    asyncio.create_task(_run_vectorization_job(job_id))

    return job_id
