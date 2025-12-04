from __future__ import annotations

from dataclasses import dataclass

from .value_objects import VectorizedPeriodId


@dataclass(frozen=True)
class VectorizedPeriod:
    """
    Векторизованный фрагмент видео для конкретного источника.

    start_at / end_at — ISO-строки (одна временная шкала).
    """
    id: VectorizedPeriodId
    source_id: str
    start_at: str
    end_at: str
