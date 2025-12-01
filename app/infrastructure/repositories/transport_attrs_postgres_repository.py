from __future__ import annotations

from typing import Optional

from asyncpg import Record

from app.domain.attributes import TransportAttributes
from app.domain.value_objects import TransportAttrsId, ObjectId
from app.domain.repositories.transport_attrs_repository import TransportAttributesRepository
from app.infrastructure.db.postgres import PostgresDatabase


class TransportAttributesPostgresRepository(TransportAttributesRepository):
    def __init__(self, db: PostgresDatabase) -> None:
        self._db = db

    async def create(self, attrs: TransportAttributes) -> None:
        sql = """
        INSERT INTO transport_attrs (id, object_id, color_hsv, license_plate)
        VALUES ($1, $2, $3, $4);
        """

        await self._db.execute(
            sql,
            attrs.id,
            attrs.object_id,
            attrs.color_hsv,
            attrs.license_plate,
        )

    async def find_by_id(self, attrs_id: TransportAttrsId) -> Optional[TransportAttributes]:
        sql = """
        SELECT id, object_id, color_hsv, license_plate
        FROM transport_attrs
        WHERE id = $1;
        """

        row = await self._db.fetchrow(sql, attrs_id)
        if row is None:
            return None

        return self._map_row_to_transport_attrs(row)

    @staticmethod
    def _map_row_to_transport_attrs(row: Record) -> TransportAttributes:
        return TransportAttributes(
            id=TransportAttrsId(row["id"]),
            object_id=ObjectId(row["object_id"]),
            color_hsv=row["color_hsv"],
            license_plate=row["license_plate"],
        )