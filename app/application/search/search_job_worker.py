from __future__ import annotations
import asyncio
import time

from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.search_job_postgres_repository import SearchJobPostgresRepository
from app.application.search.search_job_runner import _run_job


async def main() -> None:
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    repo = SearchJobPostgresRepository(db)

    print("=== Search Job Worker started ===")

    while True:
        jobs = await repo.find_all()

        for job in jobs:
            if job.status == "PENDING":
                print(f"[WORKER] start job {job.id}")
                asyncio.create_task(
                    _run_job(
                        job_id=job.id,
                        text_query=job.text_query,
                        source_id=job.source_id,
                        start_at=job.start_at,
                        end_at=job.end_at,
                    )
                )

        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
