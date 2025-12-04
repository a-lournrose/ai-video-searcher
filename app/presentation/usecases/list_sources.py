from __future__ import annotations

import asyncio
from typing import List

from app.domain.source import Source
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.source_postgres_repository import SourcePostgresRepository


async def get_all_sources() -> List[Source]:
    """
    Возвращает список всех источников, для которых есть векторизованные периоды
    (по факту — просто всё содержимое таблицы sources).
    """
    config = load_config_from_env()
    db = PostgresDatabase(config)
    await db.connect()

    try:
        repo = SourcePostgresRepository(db)
        return await repo.find_all()
    finally:
        await db.close()


async def main() -> None:
    sources = await get_all_sources()

    print("=== Sources ===")
    for src in sources:
        print(f"id={src.id}  source_id={src.source_id}")


if __name__ == "__main__":
    asyncio.run(main())
