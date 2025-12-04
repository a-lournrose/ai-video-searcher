from __future__ import annotations
import asyncio

from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.search_job_postgres_repository import SearchJobPostgresRepository


async def main() -> None:
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    repo = SearchJobPostgresRepository(db)
    jobs = await repo.find_all()

    print("\n=== ACTIVE SEARCH JOBS ===\n")
    for j in jobs:
        print(
            f"{j.id}  |  {j.status:>7}  |  {j.progress:5.1f}%  |  "
            f"{j.text_query}  |  {j.source_id}  |  "
            f"{j.start_at} → {j.end_at}"
        )

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
