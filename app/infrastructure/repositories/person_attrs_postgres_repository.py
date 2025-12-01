from __future__ import annotations

from typing import Optional

from asyncpg import Record

from app.domain.attributes import PersonAttributes
from app.domain.value_objects import PersonAttrsId, ObjectId
from app.domain.repositories.person_attrs_repository import PersonAttributesRepository
from app.infrastructure.db.postgres import PostgresDatabase


class PersonAttributesPostgresRepository(PersonAttributesRepository):
    def __init__(self, db: PostgresDatabase) -> None:
        self._db = db

    async def create(self, attrs: PersonAttributes) -> None:
        sql = """
        INSERT INTO person_attrs (id, object_id, upper_color_hsv, lower_color_hsv)
        VALUES ($1, $2, $3, $4);
        """

        await self._db.execute(
            sql,
            attrs.id,
            attrs.object_id,
            attrs.upper_color_hsv,
            attrs.lower_color_hsv,
        )

    async def find_by_id(self, attrs_id: PersonAttrsId) -> Optional[PersonAttributes]:
        sql = """
        SELECT id, object_id, upper_color_hsv, lower_color_hsv
        FROM person_attrs
        WHERE id = $1;
        """

        row = await self._db.fetchrow(sql, attrs_id)
        if row is None:
            return None

        return self._map_row_to_person_attrs(row)

    @staticmethod
    def _map_row_to_person_attrs(row: Record) -> PersonAttributes:
        return PersonAttributes(
            id=PersonAttrsId(row["id"]),
            object_id=ObjectId(row["object_id"]),
            upper_color_hsv=row["upper_color_hsv"],
            lower_color_hsv=row["lower_color_hsv"],
        )