from __future__ import annotations

import asyncio
from typing import List

from app.domain.source import Source
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.source_postgres_repository import SourcePostgresRepository


async def list_sources_usecase() -> List[Source]:
    """
    Возвращает список всех источников.
    Подходит для вызова как из HTTP-эндпоинта, так и из CLI.
    """
    config = load_config_from_env()
    db = PostgresDatabase(config)
    await db.connect()

    try:
        repo = SourcePostgresRepository(db)
        return await repo.find_all()
    finally:
        await db.close()


async def _main_cli() -> None:
    """
    CLI-режим — используется только при запуске файла как скрипта.
    """
    sources = await list_sources_usecase()

    print("=== Sources ===")
    for src in sources:
        print(f"id={src.id}  source_id={src.source_id}")


if __name__ == "__main__":
    asyncio.run(_main_cli())