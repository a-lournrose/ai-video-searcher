from __future__ import annotations

from typing import Optional, Protocol

from app.domain.attributes import TransportAttributes
from app.domain.value_objects import TransportAttrsId


class TransportAttributesRepository(Protocol):

    async def create(self, attrs: TransportAttributes) -> None:
        ...

    async def find_by_id(self, attrs_id: TransportAttrsId) -> Optional[TransportAttributes]:
        ...
