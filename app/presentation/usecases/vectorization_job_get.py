from __future__ import annotations

from typing import Optional

from app.domain.vectorization_job import VectorizationJob
from app.domain.value_objects import VectorizationJobId
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.vectorization_job_postgres_repository import (
    VectorizationJobPostgresRepository,
)


async def get_vectorization_job_usecase(
    job_id: str,
) -> Optional[VectorizationJob]:
    """
    Возвращает одну задачу векторизации по id или None.
    """
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    try:
        repo = VectorizationJobPostgresRepository(db)
        return await repo.find_by_id(VectorizationJobId(job_id))
    finally:
        await db.close()
