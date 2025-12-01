from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional, Callable, Awaitable

import asyncpg
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    database: str
    user: str
    password: str


def load_config_from_env() -> PostgresConfig:
    """
    Загружает конфиг PostgreSQL из переменных окружения.
    Верхние слои про это не знают — они просто получают уже готовый Database.
    """
    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "5433"))
    database = os.getenv("DB_NAME", "video_search")
    user = os.getenv("DB_USER", "app_user")
    password = os.getenv("DB_PASSWORD", "app_password")

    return PostgresConfig(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
    )


class PostgresDatabase:
    """
    Инфраструктурный класс работы с PostgreSQL через пул соединений.

    Важный момент для архитектуры:
    - Верхние слои (репозитории, use-case'ы) в будущем будут зависеть не от asyncpg,
      а от более абстрактного протокола / интерфейса.
    - Этот класс — конкретная реализация под PostgreSQL, локализованная в инфраструктуре.
    """

    def __init__(self, config: PostgresConfig) -> None:
        self._config = config
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        if self._pool is not None:
            return

        self._pool = await asyncpg.create_pool(
            host=self._config.host,
            port=self._config.port,
            database=self._config.database,
            user=self._config.user,
            password=self._config.password,
            min_size=1,
            max_size=10,
        )

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def execute(self, query: str, *args: Any) -> str:
        """
        Выполнить запрос без возвращаемых строк (INSERT/UPDATE/DELETE/...).
        Возвращает статусную строку PostgreSQL.
        """
        if self._pool is None:
            raise RuntimeError("PostgresDatabase is not connected")

        async with self._pool.acquire() as connection:
            return await connection.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        """
        Выполнить SELECT и вернуть все строки.
        """
        if self._pool is None:
            raise RuntimeError("PostgresDatabase is not connected")

        async with self._pool.acquire() as connection:
            rows = await connection.fetch(query, *args)
            return list(rows)

    async def fetchrow(self, query: str, *args: Any) -> Optional[asyncpg.Record]:
        """
        Выполнить SELECT и вернуть одну строку (или None).
        """
        if self._pool is None:
            raise RuntimeError("PostgresDatabase is not connected")

        async with self._pool.acquire() as connection:
            row = await connection.fetchrow(query, *args)
            return row

    async def with_connection(
        self,
        func: Callable[[asyncpg.Connection], Awaitable[Any]],
    ) -> Any:
        """
        Универсальный helper: даёт "сырое" соединение в функцию.
        Может пригодиться для транзакций или специфичных фич PostgreSQL.
        """
        if self._pool is None:
            raise RuntimeError("PostgresDatabase is not connected")

        async with self._pool.acquire() as connection:
            return await func(connection)