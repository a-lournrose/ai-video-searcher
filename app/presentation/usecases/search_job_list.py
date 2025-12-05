from __future__ import annotations

import asyncio
from typing import List

from app.domain.search_job import SearchJob
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.search_job_postgres_repository import SearchJobPostgresRepository


async def list_search_jobs_usecase() -> List[SearchJob]:
    """
    Возвращает список всех задач поиска.
    Подходит для вызова из REST и других сервисов.
    """
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    try:
        repo = SearchJobPostgresRepository(db)
        return await repo.find_all()
    finally:
        await db.close()


async def _main_cli() -> None:
    """
    CLI-запуск — просто выводит список задач в консоль.
    """
    jobs = await list_search_jobs_usecase()

    print("\n=== ACTIVE SEARCH JOBS ===\n")
    for j in jobs:
        print(
            f"{j.id}  |  {j.status:>7}  |  {j.progress:5.1f}%  |  "
            f"{j.text_query}  |  {j.source_id}  |  "
            f"{j.start_at} → {j.end_at}"
        )


if __name__ == "__main__":
    asyncio.run(_main_cli())