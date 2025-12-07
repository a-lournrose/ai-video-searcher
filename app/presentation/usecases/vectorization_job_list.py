from __future__ import annotations

from typing import List

from app.domain.vectorization_job import VectorizationJob
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.vectorization_job_postgres_repository import (
    VectorizationJobPostgresRepository,
)


async def list_vectorization_jobs_usecase() -> List[VectorizationJob]:
    """
    Возвращает все задачи векторизации (для UI/админки).
    """
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    try:
        repo = VectorizationJobPostgresRepository(db)
        return await repo.list_all()
    finally:
        await db.close()
