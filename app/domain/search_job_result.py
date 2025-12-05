from __future__ import annotations

from dataclasses import dataclass

from app.domain.value_objects import (
    SearchJobResultId,
    SearchJobId,
    FrameId,
    ObjectId,
)


@dataclass(frozen=True)
class SearchJobResult:
    id: SearchJobResultId
    job_id: SearchJobId

    frame_id: FrameId
    object_id: ObjectId | None

    rank: int

    final_score: float
    clip_score: float
    color_score: float
    plate_score: float
