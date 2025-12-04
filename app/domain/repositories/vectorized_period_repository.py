from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable, List

from app.domain.vectorized_period import VectorizedPeriod


class VectorizedPeriodRepository(ABC):
    """
    Хранилище векторизованных периодов по источникам.
    """

    @abstractmethod
    async def add_many(self, periods: Iterable[VectorizedPeriod]) -> None:
        """
        Добавляет несколько периодов. Реализация может делать upsert
        (например, по уникальной паре source_id + start_at + end_at).
        """
        raise NotImplementedError

    @abstractmethod
    async def list_by_source_id(self, source_id: str) -> List[VectorizedPeriod]:
        """
        Возвращает все векторизованные периоды для указанного источника.
        """
        raise NotImplementedError
