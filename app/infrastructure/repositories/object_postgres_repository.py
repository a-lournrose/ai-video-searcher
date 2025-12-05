from __future__ import annotations

from typing import Optional

from asyncpg import Record

from app.domain.object import Object, BBox
from app.domain.value_objects import ObjectId, FrameId, ObjectType
from app.domain.repositories.object_repository import ObjectRepository
from app.infrastructure.db.postgres import PostgresDatabase


class ObjectPostgresRepository(ObjectRepository):
    """
    Реализация ObjectRepository поверх PostgreSQL (таблица objects).
    """

    def __init__(self, db: PostgresDatabase) -> None:
        self._db = db

    async def create(self, obj: Object) -> None:
        """
        Вставляет новый объект в таблицу objects.
        """
        sql = """
        INSERT INTO objects (
            id,
            frame_id,
            type,
            bbox_x,
            bbox_y,
            bbox_width,
            bbox_height,
            track_id
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8);
        """

        await self._db.execute(
            sql,
            obj.id,
            obj.frame_id,
            obj.type.value,        # 'PERSON' / 'TRANSPORT'
            obj.bbox.x,
            obj.bbox.y,
            obj.bbox.width,
            obj.bbox.height,
            obj.track_id,          # может быть None
        )

    async def find_by_id(self, object_id: ObjectId) -> Optional[Object]:
        """
        Находит объект по id или возвращает None.
        """
        sql = """
        SELECT
            id,
            frame_id,
            type,
            bbox_x,
            bbox_y,
            bbox_width,
            bbox_height,
            track_id
        FROM objects
        WHERE id = $1;
        """

        row = await self._db.fetchrow(sql, object_id)
        if row is None:
            return None

        return self._map_row_to_object(row)

    @staticmethod
    def _map_row_to_object(row: Record) -> Object:
        """
        Маппинг строки из БД в доменную модель Object.
        """
        bbox = BBox(
            x=int(row["bbox_x"]),
            y=int(row["bbox_y"]),
            width=int(row["bbox_width"]),
            height=int(row["bbox_height"]),
        )

        track_id_raw = row["track_id"]
        track_id: Optional[int] = int(track_id_raw) if track_id_raw is not None else None

        return Object(
            id=ObjectId(row["id"]),
            frame_id=FrameId(row["frame_id"]),
            type=ObjectType(row["type"]),
            bbox=bbox,
            track_id=track_id,
        )