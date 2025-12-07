from __future__ import annotations

from typing import List, Optional

from asyncpg import Record

from app.domain.repositories.search_job_event_repository import (
    SearchJobEventRepository,
)
from app.domain.search_job_event import SearchJobEvent
from app.domain.value_objects import (
    SearchJobResultId,
    SearchJobId,
    ObjectId,
)
from app.infrastructure.db.postgres import PostgresDatabase


class SearchJobEventPostgresRepository(SearchJobEventRepository):
    def __init__(self, db: PostgresDatabase) -> None:
        self._db = db

    async def create_many(self, events: List[SearchJobEvent]) -> None:
        if not events:
            return

        sql = """
            INSERT INTO search_job_events (id, job_id, track_id, object_id, score)
            VALUES ($1, $2, $3, $4, $5)
        """

        for event in events:
            await self._db.execute(
                sql,
                event.id,
                event.job_id,
                event.track_id,
                event.object_id,
                event.score,
            )

    async def find_by_job_id(self, job_id: SearchJobId) -> List[SearchJobEvent]:
        sql = """
            SELECT id,
                   job_id,
                   track_id,
                   object_id,
                   score
            FROM search_job_events
            WHERE job_id = $1
            ORDER BY score DESC
        """

        rows = await self._db.fetch(sql, job_id)
        return [self._map_row(row) for row in rows]

    @staticmethod
    def _map_row(row: Record) -> SearchJobEvent:
        track_id_raw: Optional[int] = row["track_id"]
        object_id_raw: Optional[str] = row["object_id"]

        return SearchJobEvent(
            id=SearchJobResultId(row["id"]),
            job_id=SearchJobId(row["job_id"]),
            track_id=track_id_raw,
            object_id=ObjectId(object_id_raw) if object_id_raw is not None else None,
            score=float(row["score"]),
        )