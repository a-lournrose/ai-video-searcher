from __future__ import annotations
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from app.domain.search_job import SearchJob
from app.domain.value_objects import SearchJobId
from app.domain.repositories.search_job_repository import SearchJobRepository
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.search_job_postgres_repository import SearchJobPostgresRepository
from app.application.search.search_service import search_by_text


async def create_job(
    repo: SearchJobRepository,
    db,
    *,
    title: str,
    text_query: str,
    source_id: str,
    start_at: str,
    end_at: str,
) -> SearchJobId:

    job_id = SearchJobId(uuid4())

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

    # ← запускаем worker в фоне
    asyncio.create_task(
        _run_job(job_id, text_query, source_id, start_at, end_at)
    )

    return job_id



async def _run_job(job_id, text_query, source_id, start_at, end_at):
    """
    Worker запускается автоматом при create_job
    без отдельного процесса.
    """

    db = PostgresDatabase(load_config_from_env())
    await db.connect()
    repo = SearchJobPostgresRepository(db)

    try:
        await repo.update_status(job_id, "RUNNING", None)
        await repo.update_progress(job_id, 10.0)

        # 1) Поиск
        hits = await search_by_text(
            db=db,
            source_id=source_id,
            start_at=start_at,
            end_at=end_at,
            text=text_query,
        )

        await repo.update_progress(job_id, 70.0)

        # 2) Сохранение результатов
        out = Path("storage/search_results")
        out.mkdir(parents=True, exist_ok=True)

        file_path = out / f"{job_id}.json"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([h.__dict__ for h in hits], f, indent=4, ensure_ascii=False)

        await repo.update_progress(job_id, 100.0)
        await repo.update_status(job_id, "DONE", None)

        print(f"\n✔ Результаты сохранены → {file_path}\n")

    except Exception as exc:
        await repo.update_status(job_id, "FAILED", str(exc))

    finally:
        await db.close()
