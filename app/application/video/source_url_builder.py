from __future__ import annotations


def build_video_url(
    source_id: str,
    start_at: str,
    end_at: str,
) -> str:
    """
    Конструирует URL видеопотока для заданного source_id и временного интервала.

    Пока реализация захардкожена и не использует параметры.
    В будущем здесь можно:
      - ходить в БД за конкретным HLS-плейлистом,
      - вызывать внешний сервис,
      - подставлять разные base-url для prod/dev и т.д.
    """
    return "http://localhost:8000/media/f98fdb80731a4da185035b60c222f818/index.m3u8"

def build_snapshot_url(
    source_id: str,
    at: str,
    object_id: str | None,
) -> str:
    """
    Конструирует URL HTTP-эндпоинта для получения кадра с (или без) bbox.
    """
    base = "http://localhost:8001/snapshot"
    if object_id is None:
        return f"{base}?source_id={source_id}&at={at}"
    return f"{base}?source_id={source_id}&at={at}&object_id={object_id}"