from __future__ import annotations

import json
from typing import List, Optional, Dict

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
            source_type_id,
            source_name,
            ranges,
            status,
            progress,
            error
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """
        await self._db.execute(
            sql,
            job.id,
            job.source_id,
            job.source_type_id,
            job.source_name,
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
        SELECT
            id,
            source_id,
            source_type_id,
            source_name,
            ranges,
            status,
            progress,
            error
        FROM vectorization_jobs
        WHERE id = $1;
        """
        row = await self._db.fetchrow(sql, str(job_id))
        if row is None:
            return None

        return self._map(row)

    async def list_all(self) -> List[VectorizationJob]:
        sql = """
        SELECT
            id,
            source_id,
            source_type_id,
            source_name,
            ranges,
            status,
            progress,
            error
        FROM vectorization_jobs
        ORDER BY id DESC;
        """
        rows = await self._db.fetch(sql)
        return [self._map(row) for row in rows]

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
    def _parse_ranges(raw: object) -> List[Dict[str, str]]:
        """
        Приводим значение из БД к List[Dict[str, str]].
        """
        if raw is None:
            return []

        if isinstance(raw, str):
            try:
                data = json.loads(raw)
            except Exception:
                return []
            if isinstance(data, list):
                return data
            return []

        if isinstance(raw, list):
            return raw

        return []

    @staticmethod
    def _map(row: Record) -> VectorizationJob:
        return VectorizationJob(
            id=VectorizationJobId(row["id"]),
            source_id=row["source_id"],
            source_type_id=row["source_type_id"],
            source_name=row["source_name"],
            ranges=VectorizationJobPostgresRepository._parse_ranges(row["ranges"]),
            status=row["status"],
            progress=row["progress"],
            error=row["error"],
        )
