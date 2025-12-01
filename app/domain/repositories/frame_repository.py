from __future__ import annotations

from typing import Protocol, Optional

from app.domain.frame import Frame
from app.domain.value_objects import FrameId


class FrameRepository(Protocol):
    async def create(self, frame: Frame) -> None:
        ...

    async def find_by_id(self, frame_id: FrameId) -> Optional[Frame]:
        ...
