from __future__ import annotations

from typing import Iterable, List

from asyncpg import Record

from app.domain.vectorized_period import VectorizedPeriod
from app.domain.value_objects import VectorizedPeriodId
from app.domain.repositories.vectorized_period_repository import VectorizedPeriodRepository
from app.infrastructure.db.postgres import PostgresDatabase


class VectorizedPeriodPostgresRepository(VectorizedPeriodRepository):
    """
    PostgreSQL-реализация репозитория векторизованных периодов.
    """

    def __init__(self, db: PostgresDatabase) -> None:
        self._db = db

    async def add_many(self, periods: Iterable[VectorizedPeriod]) -> None:
        """
        Добавляет несколько периодов.

        Для простоты используем INSERT ... ON CONFLICT DO NOTHING
        по уникальной паре (source_id, start_at, end_at).
        """
        sql = """
        INSERT INTO vectorized_periods (id, source_id, start_at, end_at)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (source_id, start_at, end_at) DO NOTHING;
        """

        for period in periods:
            await self._db.execute(
                sql,
                period.id,
                period.source_id,
                period.start_at,
                period.end_at,
            )

    async def list_by_source_id(self, source_id: str) -> List[VectorizedPeriod]:
        sql = """
        SELECT id, source_id, start_at, end_at
        FROM vectorized_periods
        WHERE source_id = $1
        ORDER BY start_at;
        """
        rows = await self._db.fetch(sql, source_id)
        return [self._map_row(row) for row in rows]

    async def list_for_source(self, source_id: str) -> List[VectorizedPeriod]:
        """
        Возвращает все интервалы векторизации для конкретного источника,
        отсортированные по start_at.
        """
        sql = """
        SELECT id, source_id, start_at, end_at
        FROM vectorized_periods
        WHERE source_id = $1
        ORDER BY start_at
        """
        rows = await self._db.fetch(sql, source_id)
        return [self._map_row(row) for row in rows]

    @staticmethod
    def _map_row(row: Record) -> VectorizedPeriod:
        return VectorizedPeriod(
            id=VectorizedPeriodId(row["id"]),
            source_id=row["source_id"],
            start_at=row["start_at"],
            end_at=row["end_at"],
        )
