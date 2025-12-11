from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .value_objects import SearchJobId


@dataclass(frozen=True)
class SearchJob:
    id: SearchJobId
    title: str
    text_query: str
    source_id: str
    source_type_id: int
    source_name: str
    start_at: str
    end_at: str
    status: str
    progress: float
    error: Optional[str]
