from __future__ import annotations

from app.domain.search_job_result import SearchJobResult
from app.domain.value_objects import SearchJobId


class SearchJobResultRepository:
    async def create_many(
            self,
            results: list[SearchJobResult],
    ) -> None:
        ...

    async def find_by_job_id(
            self,
            job_id: SearchJobId,
    ) -> list[SearchJobResult]:
        ...
