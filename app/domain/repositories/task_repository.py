from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from app.domain.task import Task
from app.domain.value_objects import TaskId


class TaskRepository(ABC):
    """
    Абстракция над хранилищем задач.
    """

    @abstractmethod
    async def create(self, task: Task) -> None:
        """
        Persist new task entity.
        """
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, task_id: TaskId) -> Optional[Task]:
        """
        Return task entity by id or None if not found.
        """
        raise NotImplementedError
