from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List

from app.domain.value_objects import SearchJobId
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.search_job_postgres_repository import (
    SearchJobPostgresRepository,
)
from app.infrastructure.repositories.search_job_result_postgres_repository import (
    SearchJobResultPostgresRepository,
)
from app.application.video.source_url_builder import build_snapshot_url


JOB_ID = "aa08b1e4-5af9-47f7-9f4a-4cc4f0cd9cdb"


async def main() -> None:
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    try:
        job_repo = SearchJobPostgresRepository(db)
        result_repo = SearchJobResultPostgresRepository(db)

        job_id = SearchJobId(JOB_ID)

        job = await job_repo.find_by_id(job_id)
        if job is None:
            print(f"Search job not found: {JOB_ID}")
            return

        results = await result_repo.find_by_job_id(job_id)

        items: List[Dict[str, Any]] = []

        for res in results:
            # берём at из frames
            row = await db.fetchrow(
                """
                SELECT at
                FROM frames
                WHERE id = $1
                """,
                res.frame_id,
            )
            if row is None:
                continue

            at: str = row["at"]
            object_id_str = str(res.object_id) if res.object_id is not None else None

            url = build_snapshot_url(
                source_id=job.source_id,
                at=at,
                object_id=object_id_str,
            )

            items.append(
                {
                    "id": str(res.id),
                    "rank": res.rank,
                    "url": url,
                    "frame_id": str(res.frame_id),
                    "object_id": object_id_str,
                    "at": at,
                    "final_score": res.final_score,
                    "clip_score": res.clip_score,
                    "color_score": res.color_score,
                    "plate_score": res.plate_score,
                }
            )

        print(json.dumps(items, ensure_ascii=False, indent=2))

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
