from __future__ import annotations

from typing import Optional

from asyncpg import Record

from app.domain.source import Source
from app.domain.value_objects import SourceRowId
from app.domain.repositories.source_repository import SourceRepository
from app.infrastructure.db.postgres import PostgresDatabase


class SourcePostgresRepository(SourceRepository):
    def __init__(self, db: PostgresDatabase) -> None:
        self._db = db

    async def create(self, source: Source) -> None:
        """
        Inserts new source row.
        """
        sql = """
        INSERT INTO sources (id, source_id)
        VALUES ($1, $2);
        """
        await self._db.execute(sql, source.id, source.source_id)

    async def find_by_id(self, row_id: SourceRowId) -> Optional[Source]:
        sql = """
        SELECT id, source_id
        FROM sources
        WHERE id = $1;
        """
        row = await self._db.fetchrow(sql, row_id)
        if row is None:
            return None

        return self._map(row)

    async def find_by_source_id(self, source_id: str) -> Optional[Source]:
        """
        Search by external user-facing source_id.
        """
        sql = """
        SELECT id, source_id
        FROM sources
        WHERE source_id = $1;
        """
        row = await self._db.fetchrow(sql, source_id)
        if row is None:
            return None

        return self._map(row)

    async def find_all(self) -> List[Source]:
        """
        Returns all sources.
        """
        sql = """
              SELECT id, source_id
              FROM sources
              ORDER BY source_id; \
              """
        rows = await self._db.fetch(sql)
        return [self._map(row) for row in rows]

    @staticmethod
    def _map(row: Record) -> Source:
        return Source(
            id=SourceRowId(row["id"]),
            source_id=row["source_id"],
        )
