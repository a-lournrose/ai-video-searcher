from __future__ import annotations

from typing import Optional

from asyncpg import Record

from app.domain.frame import Frame
from app.domain.value_objects import FrameId
from app.domain.repositories.frame_repository import FrameRepository
from app.infrastructure.db.postgres import PostgresDatabase


class FramePostgresRepository(FrameRepository):
    def __init__(self, db: PostgresDatabase) -> None:
        self._db = db

    async def create(self, frame: Frame) -> None:
        sql = """
        INSERT INTO frames (id, timestamp_sec)
        VALUES ($1, $2);
        """

        await self._db.execute(sql, frame.id, frame.timestamp_sec)

    async def find_by_id(self, frame_id: FrameId) -> Optional[Frame]:
        sql = """
        SELECT id, timestamp_sec
        FROM frames
        WHERE id = $1;
        """

        row = await self._db.fetchrow(sql, frame_id)
        if row is None:
            return None

        return self._map_row_to_frame(row)

    @staticmethod
    def _map_row_to_frame(row: Record) -> Frame:
        return Frame(
            id=FrameId(row["id"]),
            timestamp_sec=float(row["timestamp_sec"]),
        )
