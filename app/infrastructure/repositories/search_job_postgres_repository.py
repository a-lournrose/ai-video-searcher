from __future__ import annotations

from typing import List, Optional
from asyncpg import Record

from app.domain.search_job import SearchJob
from app.domain.value_objects import SearchJobId
from app.domain.repositories.search_job_repository import SearchJobRepository
from app.infrastructure.db.postgres import PostgresDatabase


class SearchJobPostgresRepository(SearchJobRepository):
    def __init__(self, db: PostgresDatabase) -> None:
        self._db = db

    async def create(self, job: SearchJob) -> None:
        sql = """
        INSERT INTO search_jobs (id, title, text_query, source_id, start_at, end_at, progress, status, error)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        """
        await self._db.execute(sql,
            job.id, job.title, job.text_query,
            job.source_id, job.start_at, job.end_at,
            job.progress, job.status, job.error
        )

    async def update_progress(self, job_id: SearchJobId, value: float) -> None:
        await self._db.execute(
            "UPDATE search_jobs SET progress=$1 WHERE id=$2",
            value, job_id
        )

    async def update_status(self, job_id: SearchJobId, status: str, error: Optional[str]) -> None:
        await self._db.execute(
            "UPDATE search_jobs SET status=$1,error=$2 WHERE id=$3",
            status, error, job_id
        )

    async def find_all(self) -> List[SearchJob]:
        sql = """
              SELECT j.id, \
                     j.title, \
                     j.text_query, \
                     j.source_id, \
                     j.start_at, \
                     j.end_at, \
                     j.status, \
                     j.progress, \
                     j.error, \
                     s.source_type_id, \
                     s.name AS source_name
              FROM search_jobs AS j
                       LEFT JOIN sources AS s
                                 ON s.source_id = j.source_id
              ORDER BY j.id DESC; \
              """
        rows = await self._db.fetch(sql)
        return [self._map(row) for row in rows]

    async def find_by_id(self, job_id: SearchJobId) -> Optional[SearchJob]:
        sql = """
              SELECT j.id,
                     j.title,
                     j.text_query,
                     j.source_id,
                     j.start_at,
                     j.end_at,
                     j.status,
                     j.progress,
                     j.error,
                     s.source_type_id,
                     s.name AS source_name
              FROM search_jobs AS j
                       LEFT JOIN sources AS s
                                 ON s.source_id = j.source_id
              WHERE j.id = $1 LIMIT 1
              """
        row = await self._db.fetchrow(sql, job_id)
        return None if row is None else self._map(row)

    @staticmethod
    def _map(row: Record) -> SearchJob:
        return SearchJob(
            id=SearchJobId(row["id"]),
            title=row["title"],
            text_query=row["text_query"],
            source_id=row["source_id"],
            source_type_id=row["source_type_id"],
            source_name=row["source_name"],
            start_at=row["start_at"],
            end_at=row["end_at"],
            status=row["status"],
            progress=row["progress"],
            error=row["error"],
        )
