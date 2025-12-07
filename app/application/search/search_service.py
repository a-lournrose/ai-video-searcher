from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Literal
import json
import math

from app.application.search.query_parser import (
    parse_query,
    ParsedQuery,
    QueryObjectType,
)
from app.application.search.color_score import compute_color_score
from app.application.embeddings.ruclip_embedder import embed_text
from app.domain.object import ObjectType
from app.infrastructure.db.postgres import PostgresDatabase

from app.application.video.plate_ocr import normalize_plate_text
from rapidfuzz import fuzz


@dataclass(frozen=True)
class SearchHit:
    """
    Результат поиска.

    target_type:
        "frame" или "object".
    frame_id:
        ссылка на кадр, где найдено совпадение.
    object_id:
        если поиск по объектам (PERSON/TRANSPORT) — id объекта,
        если поиск по кадрам — None.
    timestamp_sec:
        временная позиция кадра в видео.
    track_id:
        идентификатор трека объекта (если есть трекинг), иначе None.
    final_score:
        итоговый скор (для сортировки/фильтрации).
    clip_score:
        скор по ruCLIP (косинусная близость).
    color_score:
        скор по цвету (0..1).
    plate_score:
        скор по номеру (0..1).
    """
    target_type: Literal["frame", "object"]
    frame_id: str
    object_id: Optional[str]
    timestamp_sec: float

    final_score: float
    clip_score: float
    color_score: float
    plate_score: float
    track_id: Optional[int]


def _filter_hits(
    hits: List[SearchHit],
    query_has_color: bool,
    query_has_plate: bool,
    clip_min: float,
    final_min: float,
) -> List[SearchHit]:
    """
    Фильтрация результатов по:
      - clip_score >= clip_min (всегда),
      - если в запросе был цвет — требуем color_score > 0,
      - если в запросе был номер — требуем plate_score > 0,
      - final_score >= final_min.
    """
    filtered: List[SearchHit] = []

    for hit in hits:
        if hit.clip_score < clip_min:
            continue

        if query_has_color and hit.color_score <= 0.0:
            continue

        if query_has_plate and hit.plate_score <= 0.0:
            continue

        if hit.final_score < final_min:
            continue

        filtered.append(hit)

    return filtered


async def search_by_text(
    db: PostgresDatabase,
    source_id: str,
    start_at: str,
    end_at: str,
    text: str,
    max_candidates: int = 2000,
    clip_min_pure: float = 0.30,
    final_min: float = 0.30,
) -> List[SearchHit]:
    """
    Главная функция поиска по тексту в рамках:
      - конкретного источника (source_id),
      - временного окна [start_at, end_at] (ISO-строки).

    - Парсит текст (parse_query),
    - Строит эмбеддинг cleaned_text через ruCLIP,
    - Если в запросе есть type -> ищем по объектам,
      иначе -> по кадрам,
    - Считает clip_score / color_score / plate_score / final_score,
    - Фильтрует по:
        * clip_score >= clip_min_pure (всегда),
        * если в запросе был цвет — требуем color_score > 0,
        * если в запросе был номер — требуем plate_score > 0,
        * final_score >= final_min (адаптивно),
    - Если после фильтрации пусто, понижает final_min ступенчато на 0.1,
      пока не появятся какие-то результаты, и их возвращает.
    """

    parsed = parse_query(text)

    query_has_color = (
        parsed.color is not None
        or parsed.upper_color is not None
        or parsed.lower_color is not None
    )
    query_has_plate = parsed.plate is not None

    query_vector = embed_text(parsed.cleaned_text)

    if parsed.type is None:
        candidates = await _fetch_frame_candidates(
            db=db,
            source_id=source_id,
            start_at=start_at,
            end_at=end_at,
            max_candidates=max_candidates,
        )
        hits = _score_frames(parsed, query_vector, candidates)
    else:
        candidates = await _fetch_object_candidates(
            db=db,
            source_id=source_id,
            start_at=start_at,
            end_at=end_at,
            query_type=parsed.type,
            max_candidates=max_candidates,
        )
        hits = _score_objects(parsed, query_vector, candidates)

    filtered = _filter_hits(
        hits=hits,
        query_has_color=query_has_color,
        query_has_plate=query_has_plate,
        clip_min=clip_min_pure,
        final_min=final_min,
    )

    if filtered:
        filtered.sort(key=lambda h: h.final_score, reverse=True)
        return filtered

    current_final_min = final_min - 0.10
    while current_final_min >= 0.0:
        filtered = _filter_hits(
            hits=hits,
            query_has_color=query_has_color,
            query_has_plate=query_has_plate,
            clip_min=clip_min_pure,
            final_min=current_final_min,
        )
        if filtered:
            filtered.sort(key=lambda h: h.final_score, reverse=True)
            return filtered

        current_final_min -= 0.10

    if not hits:
        return []

    hits.sort(key=lambda h: h.clip_score, reverse=True)
    return hits[:5]


# =========================
#   Поиск по кадрам
# =========================

@dataclass(frozen=True)
class _FrameCandidate:
    frame_id: str
    timestamp_sec: float
    vector: List[float]


async def _fetch_frame_candidates(
    db: PostgresDatabase,
    source_id: str,
    start_at: str,
    end_at: str,
    max_candidates: int,
) -> List[_FrameCandidate]:
    """
    Загружает кандидатов для поиска по кадрам:
    только кадры указанного source_id и в окне [start_at, end_at].
    """
    sql = """
    SELECT
        e.id,
        e.frame_id,
        e.vector,
        f.timestamp_sec
    FROM embeddings e
    JOIN frames f ON e.frame_id = f.id
    WHERE e.entity_type = 'FRAME'
      AND f.source_id = $1
      AND f.at >= $2
      AND f.at <= $3
    ORDER BY f.timestamp_sec
    LIMIT $4;
    """

    rows = await db.fetch(sql, source_id, start_at, end_at, max_candidates)

    candidates: List[_FrameCandidate] = []
    for row in rows:
        vec = _parse_vector(row["vector"])
        if vec is None:
            continue

        candidates.append(
            _FrameCandidate(
                frame_id=str(row["frame_id"]),
                timestamp_sec=float(row["timestamp_sec"]),
                vector=vec,
            )
        )

    return candidates


def _score_frames(
    parsed: ParsedQuery,  # noqa: ARG001
    query_vector: List[float],
    candidates: List[_FrameCandidate],
) -> List[SearchHit]:
    """
    Для поиска по кадрам учитываем только clip_score.
    Цвет/номер относятся к объектам, здесь 0.
    """
    hits: List[SearchHit] = []

    for cand in candidates:
        clip = _cosine_similarity(query_vector, cand.vector)
        color = 0.0
        plate = 0.0
        final = _combine_scores(clip, color, plate)

        hits.append(
            SearchHit(
                target_type="frame",
                frame_id=cand.frame_id,
                object_id=None,
                timestamp_sec=cand.timestamp_sec,
                final_score=final,
                clip_score=clip,
                color_score=color,
                plate_score=plate,
                track_id=None,  # для кадров трека нет
            )
        )

    return hits


# =========================
#   Поиск по объектам
# =========================

@dataclass(frozen=True)
class _ObjectCandidate:
    object_id: str
    frame_id: str
    timestamp_sec: float
    object_type: ObjectType
    track_id: Optional[int]          # NEW
    vector: List[float]

    transport_color_hsv: Optional[str]
    transport_plate: Optional[str]
    person_upper_hsv: Optional[str]
    person_lower_hsv: Optional[str]


async def _fetch_object_candidates(
    db: PostgresDatabase,
    source_id: str,
    start_at: str,
    end_at: str,
    query_type: QueryObjectType,
    max_candidates: int,
) -> List[_ObjectCandidate]:
    """
    Загружает кандидатов для поиска по объектам:
    только объекты, чьи кадры принадлежат source_id и лежат в [start_at, end_at].
    """
    sql = """
    SELECT
        e.object_id,
        e.vector,
        o.type AS object_type,
        o.frame_id,
        o.track_id,
        f.timestamp_sec,
        ta.color_hsv,
        ta.license_plate,
        pa.upper_color_hsv,
        pa.lower_color_hsv
    FROM embeddings e
    JOIN objects o ON e.object_id = o.id
    JOIN frames f ON o.frame_id = f.id
    LEFT JOIN transport_attrs ta ON o.id = ta.object_id
    LEFT JOIN person_attrs pa ON o.id = pa.object_id
    WHERE e.entity_type = 'OBJECT'
      AND f.source_id = $1
      AND f.at >= $2
      AND f.at <= $3
      AND (
          $4::text IS NULL
          OR o.type::text = $4::text
      )
    ORDER BY f.timestamp_sec
    LIMIT $5;
    """

    type_filter: Optional[str] = query_type.value if query_type is not None else None

    rows = await db.fetch(
        sql,
        source_id,
        start_at,
        end_at,
        type_filter,
        max_candidates,
    )

    candidates: List[_ObjectCandidate] = []

    for row in rows:
        vec = _parse_vector(row["vector"])
        if vec is None:
            continue

        candidates.append(
            _ObjectCandidate(
                object_id=str(row["object_id"]),
                frame_id=str(row["frame_id"]),
                timestamp_sec=float(row["timestamp_sec"]),
                object_type=ObjectType(row["object_type"]),
                track_id=row["track_id"],  # может быть None или int
                vector=vec,
                transport_color_hsv=row["color_hsv"],
                transport_plate=row["license_plate"],
                person_upper_hsv=row["upper_color_hsv"],
                person_lower_hsv=row["lower_color_hsv"],
            )
        )

    return candidates


def _score_objects(
    parsed: ParsedQuery,
    query_vector: List[float],
    candidates: List[_ObjectCandidate],
) -> List[SearchHit]:
    hits: List[SearchHit] = []

    for cand in candidates:
        clip = _cosine_similarity(query_vector, cand.vector)
        color = _compute_object_color_score(parsed, cand)
        plate = _compute_plate_score(parsed.plate, cand.transport_plate)
        final = _combine_scores(clip, color, plate)

        hits.append(
            SearchHit(
                target_type="object",
                frame_id=cand.frame_id,
                object_id=cand.object_id,
                timestamp_sec=cand.timestamp_sec,
                final_score=final,
                clip_score=clip,
                color_score=color,
                plate_score=plate,
                track_id=cand.track_id,  # ВАЖНО: прокидываем трек
            )
        )

    return hits


def _compute_object_color_score(
    parsed: ParsedQuery,
    cand: _ObjectCandidate,
) -> float:
    """
    Цветовой скор:
    - TRANSPORT: parsed.color + transport_color_hsv.
    - PERSON: upper_color / lower_color + соответствующие HSV.
    """
    if cand.object_type == ObjectType.TRANSPORT:
        if not parsed.color:
            return 0.0

        hsv = _parse_hsv(cand.transport_color_hsv)
        if hsv is None:
            return 0.0

        h, s, v = hsv
        return compute_color_score(parsed.color, h, s, v)

    if cand.object_type == ObjectType.PERSON:
        scores: List[float] = []

        if parsed.upper_color and cand.person_upper_hsv:
            hsv_upper = _parse_hsv(cand.person_upper_hsv)
            if hsv_upper is not None:
                hu, su, vu = hsv_upper
                scores.append(compute_color_score(parsed.upper_color, hu, su, vu))

        if parsed.lower_color and cand.person_lower_hsv:
            hsv_lower = _parse_hsv(cand.person_lower_hsv)
            if hsv_lower is not None:
                hl, sl, vl = hsv_lower
                scores.append(compute_color_score(parsed.lower_color, hl, sl, vl))

        if not scores:
            return 0.0

        return sum(scores) / len(scores)

    return 0.0


def _compute_plate_score(
    query_plate: Optional[str],
    db_plate: Optional[str],
) -> float:
    """
    plate_score:
      - 1.0 при точном совпадении нормализованных номеров,
      - в остальных случаях — плавный скор по rapidfuzz (0.0..1.0).
    """
    if not query_plate or not db_plate:
        return 0.0

    q_norm = normalize_plate_text(query_plate)
    db_norm = normalize_plate_text(db_plate)

    if not q_norm or not db_norm:
        return 0.0

    if q_norm == db_norm:
        return 1.0

    score = fuzz.ratio(q_norm, db_norm) / 100.0

    MIN_PLATE_SIMILARITY = 0.4
    if score < MIN_PLATE_SIMILARITY:
        return 0.0

    return score


# =========================
#   Вспомогательные
# =========================

def _parse_vector(raw: object) -> Optional[List[float]]:
    """
    Разбор вектора из TEXT/JSON в Python-список.
    """
    if raw is None:
        return None

    if isinstance(raw, list):
        return [float(x) for x in raw]

    if isinstance(raw, str):
        try:
            data = json.loads(raw)
            return [float(x) for x in data]
        except Exception:
            return None

    return None


def _parse_hsv(hsv_str: Optional[str]) -> Optional[tuple[float, float, float]]:
    """
    Разбор строки формата "h,s,v" -> (h, s, v).
    """
    if not hsv_str:
        return None

    try:
        h_str, s_str, v_str = hsv_str.split(",")
        return float(h_str), float(s_str), float(v_str)
    except Exception:
        return None


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Косинусная близость между двумя векторами.
    """
    if len(a) != len(b):
        raise ValueError("Vectors must have the same length")

    dot = 0.0
    na = 0.0
    nb = 0.0

    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y

    if na == 0.0 or nb == 0.0:
        return 0.0

    return dot / math.sqrt(na * nb)


def _combine_scores(
    clip_score: float,
    color_score: float,
    plate_score: float,
) -> float:
    """
    Динамическое комбинирование скорингов:

    - Если нет ни цвета, ни номера:
        final = clip.
    - Если есть только цвет:
        clip ~ 0.6, color ~ 0.4.
    - Если есть только номер:
        clip ~ 0.4, plate ~ 0.6 (номер сильнее).
    - Если есть и цвет, и номер:
        clip ~ 0.4, color ~ 0.2, plate ~ 0.4.
    """
    has_color = color_score > 0.0
    has_plate = plate_score > 0.0

    if not has_color and not has_plate:
        w_clip, w_color, w_plate = 1.0, 0.0, 0.0
    elif has_color and not has_plate:
        w_clip, w_color, w_plate = 0.6, 0.4, 0.0
    elif has_plate and not has_color:
        w_clip, w_color, w_plate = 0.4, 0.0, 0.6
    else:
        w_clip, w_color, w_plate = 0.4, 0.2, 0.4

    return (
        w_clip * clip_score
        + w_color * color_score
        + w_plate * plate_score
    )