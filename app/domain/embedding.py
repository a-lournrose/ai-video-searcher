from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .value_objects import EmbeddingId, FrameId, ObjectId, EmbeddingEntityType


@dataclass(frozen=True)
class Embedding:
    id: EmbeddingId
    entity_type: EmbeddingEntityType
    frame_id: Optional[FrameId]
    object_id: Optional[ObjectId]
    vector: List[float]
