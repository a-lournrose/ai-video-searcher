from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Set

from .postgres import PostgresDatabase, load_config_from_env


MIGRATIONS_DIR = Path(__file__).parent / "migrations"


async def _ensure_migrations_table(db: PostgresDatabase) -> None:
    """
    Создаёт служебную таблицу для учёта применённых миграций.
    Хранит только номер версии (001, 002, ...).
    """
    sql = """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version    TEXT PRIMARY KEY,
        applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    await db.execute(sql)


async def _get_applied_versions(db: PostgresDatabase) -> Set[str]:
    """
    Возвращает множество уже применённых версий миграций.
    """
    rows = await db.fetch("SELECT version FROM schema_migrations;")
    return {row["version"] for row in rows}


async def _apply_migration(db: PostgresDatabase, version: str, sql: str) -> None:
    """
    Применяет одну миграцию в транзакции и записывает её версию в schema_migrations.
    """
    async def _run(conn) -> None:
        # Важно выполнять миграцию в транзакции,
        # чтобы при ошибке схема не осталась в полубитом состоянии.
        async with conn.transaction():
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO schema_migrations (version) VALUES ($1);",
                version,
            )

    await db.with_connection(_run)


async def run_migrations() -> None:
    """
    Находит все *.sql в папке migrations, упорядочивает по имени,
    применяет те, что ещё не применены.
    """
    config = load_config_from_env()
    db = PostgresDatabase(config)

    await db.connect()
    try:
        await _ensure_migrations_table(db)
        applied_versions = await _get_applied_versions(db)

        if not MIGRATIONS_DIR.exists():
            raise RuntimeError(f"Migrations directory does not exist: {MIGRATIONS_DIR}")

        migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

        for path in migration_files:
            # Ожидаем формат имени: 001_create_users.sql -> version = "001"
            name = path.stem  # "001_create_users"
            version = name.split("_", 1)[0]

            if version in applied_versions:
                continue

            sql = path.read_text(encoding="utf-8")
            print(f"Applying migration {version} from {path.name} ...")
            await _apply_migration(db, version, sql)
            print(f"Migration {version} applied.")

        if not migration_files:
            print("No migration files found.")
        else:
            print("Migrations completed.")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(run_migrations())