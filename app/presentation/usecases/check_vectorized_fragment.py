from __future__ import annotations

from typing import Dict, List

from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.vectorized_period_postgres_repository import (
    VectorizedPeriodPostgresRepository,
)
from app.application.video.range_diff import compute_missing_ranges


async def check_vectorized_fragment_usecase(
    source_id: str,
    start_at: str,
    end_at: str,
) -> Dict[str, object]:
    """
    Проверяет, покрыт ли заданный интервал векторами.

    Возвращает dict вида:
    {
      "status": "FULLY_VECTORIZED" | "PARTIALLY_VECTORIZED" | "NOT_VECTORIZED",
      "missing_ranges": [ {start_at, end_at}, ... ]  # при partial / not
    }
    """
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    try:
        periods_repo = VectorizedPeriodPostgresRepository(db)
        existing_periods = await periods_repo.list_for_source(source_id)

        requested = [
            {
                "start_at": start_at,
                "end_at": end_at,
            }
        ]

        missing = compute_missing_ranges(requested, existing_periods)

        if not existing_periods:
            # ничего не векторизовано вообще
            return {
                "status": "NOT_VECTORIZED",
                "missing_ranges": requested,
            }

        if not missing:
            return {
                "status": "FULLY_VECTORIZED",
                "missing_ranges": [],
            }

        # проверяем, нет ли пересечения вообще
        # если missing == requested -> вообще не покрыто
        if len(missing) == 1 and (
            missing[0]["start_at"] == start_at
            and missing[0]["end_at"] == end_at
        ):
            status = "NOT_VECTORIZED"
        else:
            status = "PARTIALLY_VECTORIZED"

        return {
            "status": status,
            "missing_ranges": missing,
        }
    finally:
        await db.close()
