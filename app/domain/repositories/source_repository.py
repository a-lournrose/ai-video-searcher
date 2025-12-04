from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.source import Source
from app.domain.value_objects import SourceRowId


class SourceRepository(ABC):
    """
    Хранилище известных источников.
    """

    @abstractmethod
    async def create(self, source: Source) -> None:
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, row_id: SourceRowId) -> Optional[Source]:
        raise NotImplementedError

    @abstractmethod
    async def find_by_source_id(self, source_id: str) -> Optional[Source]:
        raise NotImplementedError

    @abstractmethod
    async def find_all(self) -> List[Source]:
        """
        Возвращает список всех источников.
        """
        raise NotImplementedError