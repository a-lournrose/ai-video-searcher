from __future__ import annotations

from dataclasses import dataclass

from .value_objects import TransportAttrsId, PersonAttrsId, ObjectId


@dataclass(frozen=True)
class TransportAttributes:
    id: TransportAttrsId
    object_id: ObjectId
    color_hsv: str
    license_plate: str | None


@dataclass(frozen=True)
class PersonAttributes:
    id: PersonAttrsId
    object_id: ObjectId
    upper_color_hsv: str | None
    lower_color_hsv: str | None
