from __future__ import annotations

import asyncio

from app.application.search.search_job_runner import create_job
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.search_job_postgres_repository import SearchJobPostgresRepository


async def create_search_job_usecase(
    title: str,
    text_query: str,
    source_id: str,
    start_at: str,
    end_at: str,
) -> str:
    """
    Создаёт задачу поиска и возвращает search_job_id.
    Используется REST API или другими сервисами.

    Само ожидание завершения задачи не входит в usecase — только запуск.
    """
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    try:
        repo = SearchJobPostgresRepository(db)

        job_id = await create_job(
            repo=repo,
            db=db,  # воркер читает job_results — БД передаётся корректно
            title=title,
            text_query=text_query,
            source_id=source_id,
            start_at=start_at,
            end_at=end_at,
        )

        return str(job_id)
    finally:
        await db.close()


async def wait_for_job_cli(job_id: str) -> None:
    """
    CLI-режим: ожидает завершения задачи и печатает изменения статуса.
    Используется только при запуске файла вручную.
    """
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    try:
        repo = SearchJobPostgresRepository(db)
        print(f"Задача создана → {job_id}")
        print("Ожидаю завершения фонового воркера...\n")

        while True:
            job = await repo.find_by_id(job_id)
            if job and job.status in ("DONE", "FAILED"):
                print(f"Статус задачи: {job.status}, прогресс: {job.progress}%")
                break
            await asyncio.sleep(1)
    finally:
        await db.close()


async def _main_cli() -> None:
    """
    Пример запуска через python -m ...
    Создаёт джобу и ждёт выполнения.
    """
    job_id = await create_search_job_usecase(
        title="Поиск тестовый",
        text_query="черная машина",
        source_id="test-source-id-1",
        start_at="2025-01-01T10:00:00",
        end_at="2025-01-01T10:00:30",
    )
    await wait_for_job_cli(job_id)


if __name__ == "__main__":
    asyncio.run(_main_cli())