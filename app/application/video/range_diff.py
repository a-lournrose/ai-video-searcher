from datetime import datetime
from typing import Dict, List

from app.domain.vectorized_period import VectorizedPeriod


def compute_missing_ranges(
    requested: List[Dict[str, str]],
    existing_periods: List[VectorizedPeriod],
) -> List[Dict[str, str]]:
    """
    На вход:
      requested: [{ "start_at": iso, "end_at": iso }, ...]
      existing_periods: уже сохранённые VectorizedPeriod для source_id.

    На выход:
      список диапазонов в том же формате, для которых НЕТ векторов.
    """
    if not requested:
        return []

    # Преобразуем existing_periods в список (start, end) в datetime
    existing_ranges = [
        (
            datetime.fromisoformat(p.start_at),
            datetime.fromisoformat(p.end_at),
        )
        for p in existing_periods
    ]
    existing_ranges.sort(key=lambda r: r[0])

    missing: List[Dict[str, str]] = []

    for item in requested:
        req_start = datetime.fromisoformat(item["start_at"])
        req_end = datetime.fromisoformat(item["end_at"])

        if req_end <= req_start:
            continue

        current_start = req_start

        # Вычитаем из [req_start, req_end) все пересекающиеся existing_ranges
        for ex_start, ex_end in existing_ranges:
            if ex_end <= current_start:
                # существующий интервал полностью левее
                continue
            if ex_start >= req_end:
                # дальше уже нет пересечений
                break

            # Есть пересечение
            if ex_start > current_start:
                # дырка слева
                missing.append(
                    {
                        "start_at": current_start.isoformat(),
                        "end_at": ex_start.isoformat(),
                    }
                )

            # сдвигаем current_start вправо
            if ex_end > current_start:
                current_start = ex_end

            if current_start >= req_end:
                break

        # хвост справа, если остался
        if current_start < req_end:
            missing.append(
                {
                    "start_at": current_start.isoformat(),
                    "end_at": req_end.isoformat(),
                }
            )

    return missing
