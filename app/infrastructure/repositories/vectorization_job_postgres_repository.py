from __future__ import annotations

import json
from typing import List, Optional

from asyncpg import Record

from app.domain.repositories.vectorization_job_repository import (
    VectorizationJobRepository,
)
from app.domain.vectorization_job import VectorizationJob
from app.domain.value_objects import VectorizationJobId
from app.infrastructure.db.postgres import PostgresDatabase


class VectorizationJobPostgresRepository(VectorizationJobRepository):
    def __init__(self, db: PostgresDatabase) -> None:
        self._db = db

    async def create(
        self,
        job: VectorizationJob,
    ) -> None:
        sql = """
        INSERT INTO vectorization_jobs (
            id,
            source_id,
            ranges,
            status,
            progress,
            error
        )
        VALUES ($1, $2, $3, $4, $5, $6)
        """
        await self._db.execute(
            sql,
            job.id,
            job.source_id,
            json.dumps(job.ranges),
            job.status,
            job.progress,
            job.error,
        )

    async def find_by_id(
        self,
        job_id: VectorizationJobId,
    ) -> Optional[VectorizationJob]:
        sql = """
        SELECT id, source_id, ranges, status, progress, error
        FROM vectorization_jobs
        WHERE id = $1
        """
        row = await self._db.fetchrow(sql, job_id)
        if row is None:
            return None

        return self._map_row(row)

    async def list_all(self) -> List[VectorizationJob]:
        sql = """
        SELECT id, source_id, ranges, status, progress, error
        FROM vectorization_jobs
        ORDER BY created_at DESC
        """
        rows = await self._db.fetch(sql)
        return [self._map_row(r) for r in rows]

    async def update_status(
        self,
        job_id: VectorizationJobId,
        status: str,
        error: Optional[str],
    ) -> None:
        sql = """
        UPDATE vectorization_jobs
        SET status = $2,
            error = $3,
            updated_at = NOW()
        WHERE id = $1
        """
        await self._db.execute(
            sql,
            job_id,
            status,
            error,
        )

    async def update_progress(
        self,
        job_id: VectorizationJobId,
        progress: float,
    ) -> None:
        sql = """
        UPDATE vectorization_jobs
        SET progress = $2,
            updated_at = NOW()
        WHERE id = $1
        """
        await self._db.execute(
            sql,
            job_id,
            progress,
        )

    @staticmethod
    def _map_row(row: Record) -> VectorizationJob:
        ranges_raw = row["ranges"]
        if isinstance(ranges_raw, str):
            ranges = json.loads(ranges_raw)
        else:
            ranges = ranges_raw

        return VectorizationJob(
            id=VectorizationJobId(str(row["id"])),
            source_id=row["source_id"],
            ranges=ranges,
            status=row["status"],
            progress=float(row["progress"]),
            error=row["error"],
        )
