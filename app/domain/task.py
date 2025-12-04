from __future__ import annotations

from dataclasses import dataclass

from .value_objects import TaskId


@dataclass(frozen=True)
class Task:
    """
    Сущность задачи по обработке источника (видеофрагмента).

    name      — человекочитаемое название задачи
    source_id — идентификатор источника (камера / поток / логический id)
    start_at  — начало периода (ISO-строка)
    end_at    — конец периода (ISO-строка)
    """
    id: TaskId
    name: str
    source_id: str
    start_at: str
    end_at: str