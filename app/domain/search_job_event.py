from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.domain.value_objects import (
    SearchJobResultId,
    SearchJobId,
    ObjectId,
)


@dataclass(frozen=True)
class SearchJobEvent:
    id: SearchJobResultId
    job_id: SearchJobId
    track_id: Optional[int]
    object_id: Optional[ObjectId]
    score: float