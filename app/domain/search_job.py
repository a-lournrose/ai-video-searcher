from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .value_objects import SearchJobId


@dataclass(frozen=True)
class SearchJob:
    """
    Хранит задачу поиска, которую ставит пользователь.
    """

    id: SearchJobId
    title: str
    text_query: str

    source_id: str
    start_at: str
    end_at: str

    progress: float
    status: str                   # PENDING / RUNNING / DONE / FAILED
    error: Optional[str]          # текст ошибки если FAILED
