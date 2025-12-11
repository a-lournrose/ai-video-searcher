from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from app.domain.value_objects import VectorizationJobId


@dataclass(frozen=True)
class VectorizationJob:
    id: VectorizationJobId
    source_id: str
    source_type_id: int
    ranges: List[Dict[str, str]]
    status: str
    progress: float
    error: str | None
