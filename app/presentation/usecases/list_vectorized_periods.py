from __future__ import annotations

import asyncio
from typing import List

from app.domain.vectorized_period import VectorizedPeriod
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.vectorized_period_postgres_repository import (
    VectorizedPeriodPostgresRepository,
)


async def list_vectorized_periods_for_source_usecase(
    source_id: str,
) -> List[VectorizedPeriod]:
    """
    Возвращает список векторизованных периодов для заданного source_id.

    Подходит для вызова как из HTTP-эндпоинта, так и из CLI.
    """
    config = load_config_from_env()
    db = PostgresDatabase(config)
    await db.connect()

    try:
        repo = VectorizedPeriodPostgresRepository(db)
        return await repo.list_by_source_id(source_id)
    finally:
        await db.close()


async def _main_cli() -> None:
    """
    Режим запуска как скрипта.
    Использует тестовый source_id для локальной проверки.
    """
    source_id = "test-source-id-1"

    periods = await list_vectorized_periods_for_source_usecase(source_id)

    print(f"=== Vectorized periods for source_id={source_id} ===")
    if not periods:
        print("No periods found.")
        return

    for idx, p in enumerate(periods, start=1):
        print(f"{idx:02d}. {p.start_at} .. {p.end_at}")


if __name__ == "__main__":
    asyncio.run(_main_cli())
