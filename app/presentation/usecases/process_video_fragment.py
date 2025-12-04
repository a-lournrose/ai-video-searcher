from __future__ import annotations

import asyncio
from uuid import uuid4

from app.application.video.processor import process_video
from app.domain.vectorized_period import VectorizedPeriod
from app.domain.value_objects import VectorizedPeriodId
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.vectorized_period_postgres_repository import (
    VectorizedPeriodPostgresRepository,
)

url = "http://localhost:8000/media/5be64b77856745c4a332192147ed0eea/index.m3u8"

ranges = [
    {
        "start_at": "2025-01-01T10:00:00",
        "end_at":   "2025-01-01T10:00:08",
    },
    {
        "start_at": "2025-01-01T10:00:12",
        "end_at":   "2025-01-01T10:00:24",
    },
    {
        "start_at": "2025-01-01T10:00:25",
        "end_at":   "2025-01-01T10:00:35",
    },
]

source_id = "test-source-id-1"


async def main() -> None:
    config = load_config_from_env()
    db = PostgresDatabase(config)
    await db.connect()

    try:
        periods_repo = VectorizedPeriodPostgresRepository(db)

        periods = [
            VectorizedPeriod(
                id=VectorizedPeriodId(uuid4()),
                source_id=source_id,
                start_at=item["start_at"],
                end_at=item["end_at"],
            )
            for item in ranges
        ]

        await periods_repo.add_many(periods)
        print(f"[vectorized_periods] saved {len(periods)} periods for source_id={source_id}")

        await process_video(
            video_source=url,
            source_id=source_id,
            ranges=ranges,
        )

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
