from __future__ import annotations

from typing import List, Optional

from app.domain.vectorization_job import VectorizationJob
from app.domain.value_objects import VectorizationJobId


class VectorizationJobRepository:
    async def create(
        self,
        job: VectorizationJob,
    ) -> None:
        """
        Регистрирует новую задачу в БД.
        """
        raise NotImplementedError

    async def find_by_id(
        self,
        job_id: VectorizationJobId,
    ) -> Optional[VectorizationJob]:
        """
        Возвращает задачу по id или None.
        """
        raise NotImplementedError

    async def list_all(self) -> List[VectorizationJob]:
        """
        Возвращает все задачи (для дебага / админки).
        """
        raise NotImplementedError

    async def update_status(
        self,
        job_id: VectorizationJobId,
        status: str,
        error: Optional[str],
    ) -> None:
        """
        Обновляет статус и опционально текст ошибки.
        """
        raise NotImplementedError

    async def update_progress(
        self,
        job_id: VectorizationJobId,
        progress: float,
    ) -> None:
        """
        Обновляет прогресс (0..100).
        """
        raise NotImplementedError
