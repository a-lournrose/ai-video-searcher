from __future__ import annotations

from dataclasses import dataclass

from .value_objects import FrameId


@dataclass(frozen=True)
class Frame:
    id: FrameId
    timestamp_sec: float
    source_id: str
    at: str
