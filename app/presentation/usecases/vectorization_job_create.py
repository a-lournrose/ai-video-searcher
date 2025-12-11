from __future__ import annotations

from typing import Dict, List

from app.domain.value_objects import VectorizationJobId
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.vectorization_job_postgres_repository import (
    VectorizationJobPostgresRepository,
)
from app.application.vectorization.vectorization_job_runner import (
    create_vectorization_job,
)


async def create_vectorization_job_usecase(
    source_id: str,
    source_type_id: int,
    ranges: List[Dict[str, str]],
) -> VectorizationJobId:
    """
    Facade-юзкейс для создания задачи векторизации.
    Поднимает соединение с БД, создаёт репозиторий и ставит задачу в очередь.
    """
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    try:
        repo = VectorizationJobPostgresRepository(db)
        job_id = await create_vectorization_job(
            source_id=source_id,
            source_type_id=source_type_id,
            ranges=ranges,
            repo=repo,
        )
        return job_id
    finally:
        await db.close()
