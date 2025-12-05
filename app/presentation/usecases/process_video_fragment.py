from __future__ import annotations

import asyncio
from typing import List, Dict
from uuid import uuid4

from app.application.video.source_url_builder import build_video_url
from app.application.video.processor import process_video

from app.domain.vectorized_period import VectorizedPeriod
from app.domain.source import Source
from app.domain.value_objects import VectorizedPeriodId, SourceRowId

from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.vectorized_period_postgres_repository import (
    VectorizedPeriodPostgresRepository,
)
from app.infrastructure.repositories.source_postgres_repository import (
    SourcePostgresRepository,
)


# Временные тестовые данные для локального запуска через __main__
_DEFAULT_RANGES: List[Dict[str, str]] = [
    {
        "start_at": "2025-01-01T10:00:00",
        "end_at": "2025-01-01T10:00:08",
    },
    {
        "start_at": "2025-01-01T10:00:12",
        "end_at": "2025-01-01T10:00:24",
    },
    {
        "start_at": "2025-01-01T10:00:25",
        "end_at": "2025-01-01T10:00:35",
    },
]

_DEFAULT_SOURCE_ID = "test-source-id-1"


async def process_video_fragment_usecase(
    source_id: str,
    ranges: List[Dict[str, str]],
) -> None:
    """
    Основной юзкейс обработки видеофрагмента:
    - гарантируем наличие source в БД;
    - сохраняем интервалы векторизации;
    - строим URL видео по общему интервалу;
    - запускаем пайплайн process_video.

    Эту функцию удобно вызывать как из CLI (__main__), так и из HTTP-роутера.
    """
    config = load_config_from_env()
    db = PostgresDatabase(config)
    await db.connect()

    try:
        source_repo = SourcePostgresRepository(db)
        periods_repo = VectorizedPeriodPostgresRepository(db)

        # 1. Убедиться, что источник есть в таблице sources
        existing_source = await source_repo.find_by_source_id(source_id)
        if existing_source is None:
            new_source = Source(
                id=SourceRowId(uuid4()),
                source_id=source_id,
            )
            await source_repo.create(new_source)
            print(f"[sources] created source_id={source_id}")
        else:
            print(f"[sources] source_id={source_id} already exists")

        # 2. Сохранить векторизованные интервалы
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
        print(
            f"[vectorized_periods] saved {len(periods)} periods "
            f"for source_id={source_id}",
        )

        # 3. Построить URL видео и прогнать пайплайн
        url = build_video_url(
            source_id=source_id,
            start_at=ranges[0]["start_at"],
            end_at=ranges[-1]["end_at"],
        )

        await process_video(
            video_source=url,
            source_id=source_id,
            ranges=ranges,
        )
    finally:
        await db.close()


async def _main_cli() -> None:
    """
    Вспомогательная функция для запуска файла как скрипта:
    использует тестовые константы _DEFAULT_SOURCE_ID и _DEFAULT_RANGES.
    """
    await process_video_fragment_usecase(
        source_id=_DEFAULT_SOURCE_ID,
        ranges=_DEFAULT_RANGES,
    )


if __name__ == "__main__":
    asyncio.run(_main_cli())