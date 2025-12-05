from __future__ import annotations

from asyncpg import Record

from app.domain.repositories.search_job_result_repository import (
    SearchJobResultRepository,
)
from app.domain.search_job_result import SearchJobResult
from app.domain.value_objects import (
    SearchJobResultId,
    SearchJobId,
    FrameId,
    ObjectId,
)
from app.infrastructure.db.postgres import PostgresDatabase


class SearchJobResultPostgresRepository(SearchJobResultRepository):
    def __init__(self, db: PostgresDatabase) -> None:
        self._db = db

    async def create_many(
            self,
            results: list[SearchJobResult],
    ) -> None:
        if not results:
            return

        sql = """
              INSERT INTO search_job_results (id,
                                              job_id,
                                              frame_id,
                                              object_id,
                                              rank,
                                              final_score,
                                              clip_score,
                                              color_score,
                                              plate_score)
              VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) \
              """

        for r in results:
            await self._db.execute(
                sql,
                r.id,
                r.job_id,
                r.frame_id,
                r.object_id,
                r.rank,
                r.final_score,
                r.clip_score,
                r.color_score,
                r.plate_score,
            )

    async def find_by_job_id(
            self,
            job_id: SearchJobId,
    ) -> list[SearchJobResult]:
        sql = """
              SELECT id,
                     job_id,
                     frame_id,
                     object_id,
                     rank,
                     final_score,
                     clip_score,
                     color_score,
                     plate_score
              FROM search_job_results
              WHERE job_id = $1
              ORDER BY rank ASC \
              """
        rows = await self._db.fetch(sql, job_id)
        return [self._map_row(row) for row in rows]

    @staticmethod
    def _map_row(row: Record) -> SearchJobResult:
        return SearchJobResult(
            id=SearchJobResultId(row["id"]),
            job_id=SearchJobId(row["job_id"]),
            frame_id=FrameId(row["frame_id"]),
            object_id=ObjectId(row["object_id"]) if row["object_id"] is not None else None,
            rank=int(row["rank"]),
            final_score=float(row["final_score"]),
            clip_score=float(row["clip_score"]),
            color_score=float(row["color_score"]),
            plate_score=float(row["plate_score"]),
        )
