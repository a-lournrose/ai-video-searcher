from __future__ import annotations

from typing import Optional, Protocol

from app.domain.attributes import PersonAttributes
from app.domain.value_objects import PersonAttrsId


class PersonAttributesRepository(Protocol):

    async def create(self, attrs: PersonAttributes) -> None:
        ...

    async def find_by_id(self, attrs_id: PersonAttrsId) -> Optional[PersonAttributes]:
        ...