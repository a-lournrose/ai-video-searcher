from __future__ import annotations

from dataclasses import dataclass

from .value_objects import SourceRowId


@dataclass(frozen=True)
class Source:
    """
    Хранит источник, для которого запускалась обработка.
    source_id       — внешний id (url камеры / логическое имя / uuid потока)
    id              — uuid строки таблицы
    source_type_id  — тип источника (например, камера / архив / др.)
    """
    id: SourceRowId
    source_id: str
    source_type_id: int
