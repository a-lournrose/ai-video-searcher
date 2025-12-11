from __future__ import annotations

import asyncio
from typing import List, Dict, Optional, Callable, Awaitable
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
from app.application.video.range_diff import compute_missing_ranges

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

ProgressCallback = Callable[[float], Awaitable[None]]


async def process_video_fragment_usecase(
    source_id: str,
    source_type_id: int,
    ranges: List[Dict[str, str]],
    progress_cb: Optional[ProgressCallback] = None,
) -> None:
    """
    Основной юзкейс обработки видеофрагмента:
    - гарантируем наличие source в БД;
    - смотрим, какие интервалы уже векторизованы;
    - считаем недостающие интервалы;
    - строим URL видео по общему интервалу недостающих кусочков;
    - запускаем пайплайн process_video;
    - ТОЛЬКО ПОСЛЕ УСПЕШНОГО ЗАВЕРШЕНИЯ пайплайна сохраняем VectorizedPeriod
      для недостающих интервалов.

    Если все запрошенные диапазоны уже покрыты, ничего не делаем.

    Если в процессе обработки возникает ошибка, новые записи в vectorized_periods
    не создаются.
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
                source_type_id=source_type_id,
            )
            await source_repo.create(new_source)
            print(
                f"[sources] created source_id={source_id} "
                f"(source_type_id={source_type_id})",
            )
        else:
            print(f"[sources] source_id={source_id} already exists")

        # 2. Узнаем, какие периоды уже векторизованы
        existing_periods = await periods_repo.list_for_source(source_id)

        # 3. Считаем недостающие диапазоны
        missing_ranges = compute_missing_ranges(
            requested=ranges,
            existing_periods=existing_periods,
        )

        if not missing_ranges:
            print(
                f"[vectorized_periods] nothing to vectorize for source_id={source_id}, "
                "all requested ranges already covered",
            )
            return

        # 4. Строим общий интервал для недостающих диапазонов и URL видео
        missing_sorted = sorted(
            missing_ranges,
            key=lambda x: x["start_at"],
        )
        overall_start = missing_sorted[0]["start_at"]
        overall_end = missing_sorted[-1]["end_at"]

        url = await build_video_url(
            db=db,
            source_id=source_id,
            start_at=overall_start,
            end_at=overall_end,
        )

        # 5. Запускаем пайплайн обработки.
        # Если здесь произойдёт исключение, VectorizedPeriod мы НЕ создаём.
        try:
            await process_video(
                video_source=url,
                source_id=source_id,
                ranges=ranges,
                progress_cb=progress_cb,
            )
        except Exception as exc:
            # Логируем и пробрасываем выше — период векторизованным не считаем
            print(
                f"[vectorization] process_video failed for source_id={source_id}: {exc}",
            )
            raise

        # 6. Если пайплайн успешно завершился, сохраняем недостающие периоды
        periods = [
            VectorizedPeriod(
                id=VectorizedPeriodId(uuid4()),
                source_id=source_id,
                start_at=item["start_at"],
                end_at=item["end_at"],
            )
            for item in missing_ranges
        ]

        await periods_repo.add_many(periods)
        print(
            f"[vectorized_periods] saved {len(periods)} NEW periods "
            f"for source_id={source_id}",
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
        source_type_id=1,  # тестовый тип источника для локального запуска
        ranges=_DEFAULT_RANGES,
    )


if __name__ == "__main__":
    asyncio.run(_main_cli())