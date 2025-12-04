from __future__ import annotations
import asyncio

from app.application.search.search_job_runner import create_job
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.search_job_postgres_repository import SearchJobPostgresRepository


async def main() -> None:
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    repo = SearchJobPostgresRepository(db)

    job_id = await create_job(
        repo,
        db,
        title="Поиск тестовый",
        text_query="черная машина",
        source_id="test-source-id-1",
        start_at="2025-01-01T10:00:00",
        end_at="2025-01-01T10:00:30",
    )

    print(f"Задача создана → {job_id}")
    print("Ожидаю завершения фонового воркера...\n")

    # ← вот это держит loop живым
    while True:
        job = await repo.find_by_id(job_id)
        if job and job.status in ("DONE", "FAILED"):
            print(f"Статус задачи: {job.status}, прогресс: {job.progress}%")
            break
        await asyncio.sleep(1)

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())