from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from app.domain.search_job_event import SearchJobEvent
from app.domain.value_objects import SearchJobId


class SearchJobEventRepository(ABC):
    @abstractmethod
    async def create_many(self, events: List[SearchJobEvent]) -> None:
        """
        Сохранить пачку событий для одной задачи поиска.
        Реализация должна быть идемпотентной по id (если нужно).
        """
        raise NotImplementedError

    @abstractmethod
    async def find_by_job_id(self, job_id: SearchJobId) -> List[SearchJobEvent]:
        """
        Вернуть все события по job_id, отсортированные по score по убыванию.
        Группировка по track_id и дальнейшая агрегация делается выше по слою.
        """
        raise NotImplementedError
