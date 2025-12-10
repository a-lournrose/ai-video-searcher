from __future__ import annotations

import asyncio

from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env


_TRUNCATE_SQL = """
TRUNCATE TABLE
    transport_attrs,
    person_attrs,
    embeddings,
    objects,
    frames,
    sources,
    vectorized_periods,
    search_jobs,
    search_job_events,
    vectorization_jobs
RESTART IDENTITY CASCADE;
"""


async def reset_domain_data() -> None:
    """
    Полностью очищает доменные таблицы.

    Важно:
      - НЕ трогаем schema_migrations, чтобы миграции оставались применёнными.
      - Используем TRUNCATE ... CASCADE, чтобы не париться с порядком FK.
    """
    config = load_config_from_env()
    db = PostgresDatabase(config)
    await db.connect()

    try:
        print("=== Resetting domain data in database ===")
        await db.execute(_TRUNCATE_SQL)
        print("=== Reset DONE ===")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(reset_domain_data())