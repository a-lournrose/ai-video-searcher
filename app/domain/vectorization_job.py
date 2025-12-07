from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from app.domain.value_objects import VectorizationJobId


@dataclass(frozen=True)
class VectorizationJob:
    """
    Задача на векторизацию видеофрагмента.

    ranges:
        список интервалов в ISO-строках вида:
        [{ "start_at": "...", "end_at": "..." }, ...]
    """
    id: VectorizationJobId
    source_id: str
    ranges: List[Dict[str, str]]
    status: str
    progress: float
    error: Optional[str]
