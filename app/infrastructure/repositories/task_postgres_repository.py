from __future__ import annotations

from typing import Optional

from asyncpg import Record

from app.domain.task import Task
from app.domain.value_objects import TaskId
from app.domain.repositories.task_repository import TaskRepository
from app.infrastructure.db.postgres import PostgresDatabase


class TaskPostgresRepository(TaskRepository):
    """
    PostgreSQL-based implementation of TaskRepository.
    """

    def __init__(self, db: PostgresDatabase) -> None:
        self._db = db

    async def create(self, task: Task) -> None:
        """
        Inserts a new task entity to database.
        """
        sql = """
        INSERT INTO tasks (id, name, source_id, start_at, end_at)
        VALUES ($1, $2, $3, $4, $5);
        """
        await self._db.execute(
            sql,
            task.id,
            task.name,
            task.source_id,
            task.start_at,
            task.end_at,
        )

    async def find_by_id(self, task_id: TaskId) -> Optional[Task]:
        """
        Returns task entity by id.
        """
        sql = """
        SELECT id, name, source_id, start_at, end_at
        FROM tasks
        WHERE id = $1;
        """
        row = await self._db.fetchrow(sql, task_id)
        if row is None:
            return None

        return self._map_row_to_task(row)

    @staticmethod
    def _map_row_to_task(row: Record) -> Task:
        """
        Maps DB row to Task domain model.
        """
        return Task(
            id=TaskId(row["id"]),
            name=row["name"],
            source_id=row["source_id"],
            start_at=row["start_at"],
            end_at=row["end_at"],
        )