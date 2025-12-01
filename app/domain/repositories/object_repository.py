from __future__ import annotations

from typing import Optional, Protocol

from app.domain.object import Object
from app.domain.value_objects import ObjectId


class ObjectRepository(Protocol):

    async def create(self, obj: Object) -> None:
        ...

    async def find_by_id(self, object_id: ObjectId) -> Optional[Object]:
        ...