from __future__ import annotations

from dataclasses import dataclass

from .value_objects import ObjectId, FrameId, ObjectType


@dataclass(frozen=True)
class BBox:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class Object:
    id: ObjectId
    frame_id: FrameId
    type: ObjectType
    bbox: BBox
