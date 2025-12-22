from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from typing import Literal

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.presentation.usecases.process_video_fragment import (
    process_video_fragment_usecase,
)
from app.presentation.usecases.list_sources import list_sources_usecase
from app.presentation.usecases.list_vectorized_periods import (
    list_vectorized_periods_for_source_usecase,
)
from app.presentation.usecases.search_job_create import (
    create_search_job_usecase,
)
from app.presentation.usecases.search_job_list import (
    list_search_jobs_usecase,
)

from app.domain.search_job import SearchJob
from app.domain.source import Source
from app.domain.vectorized_period import VectorizedPeriod

from app.presentation.usecases.list_event_frames import (
    list_event_frames_usecase,
)
from app.presentation.usecases.list_job_events import (
    list_job_events_usecase,
)
from app.presentation.usecases.check_vectorized_fragment import (
    check_vectorized_fragment_usecase,
)
from app.presentation.usecases.vectorization_job_create import (
    create_vectorization_job_usecase,
)
from app.presentation.usecases.vectorization_job_list import (
    list_vectorization_jobs_usecase,
)
from app.presentation.usecases.vectorization_job_get import (
    get_vectorization_job_usecase,
)

from app.domain.vectorization_job import VectorizationJob

router = APIRouter(
    prefix="/search",
    tags=["search"],
)

# {
#   "source_id": "a86bdbb0-e279-44c8-a356-20b5e26b884b",
#   "source_type_id": 2,
#   "ranges": [
#     {
#       "start_at": "2025-12-10T09:25:00",
#       "end_at": "2025-12-10T09:25:10"
#     }
#   ]
# }


# ---------- Схемы (Swagger-модели) ----------


class DateTimeRangeSchema(BaseModel):
    start_at: datetime = Field(
        ...,
        description="Начало интервала (ISO 8601)",
        example="2025-01-01T10:00:00",
    )
    end_at: datetime = Field(
        ...,
        description="Конец интервала (ISO 8601)",
        example="2025-01-01T10:00:08",
    )


class ProcessVideoFragmentRequest(BaseModel):
    source_id: str = Field(
        ...,
        description="Идентификатор источника (камеры/видео)",
        example="test-source-id-1",
    )
    source_type_id: int = Field(
        ...,
        description="Тип источника (например, камера, архивное видео и т.п.)",
        example=1,
    )
    ranges: List[DateTimeRangeSchema] = Field(
        ...,
        description="Список интервалов, для которых нужно выполнить векторизацию и анализ",
    )


class ProcessVideoFragmentResponse(BaseModel):
    detail: str = Field(
        ...,
        example="Video processing started",
    )


class SourceResponse(BaseModel):
    id: str = Field(
        ...,
        description="Внутренний идентификатор записи источника",
    )
    source_id: str = Field(
        ...,
        description="Внешний идентификатор источника",
    )
    source_type_id: int = Field(
        ...,
        description="Тип источника",
    )
    source_name: str = Field(
        ...,
        description="Человекочитаемое имя источника",
        example="Камера у входа",
    )


class VectorizedPeriodResponse(BaseModel):
    id: str = Field(
        ...,
        description="Идентификатор периода",
    )
    source_id: str = Field(
        ...,
        description="Идентификатор источника",
    )
    start_at: str = Field(
        ...,
        description="Начало интервала векторизации (ISO 8601)",
        example="2025-01-01T10:00:00",
    )
    end_at: str = Field(
        ...,
        description="Конец интервала векторизации (ISO 8601)",
        example="2025-01-01T10:00:08",
    )


class CreateSearchJobRequest(BaseModel):
    title: str = Field(
        ...,
        description="Человекочитаемое название задачи",
        example="Поиск черной машины",
    )
    text_query: str = Field(
        ...,
        description="Текстовый поисковый запрос пользователя",
        example="черная машина",
    )
    source_id: str = Field(
        ...,
        description="Идентификатор источника, по которому выполняется поиск",
        example="test-source-id-1",
    )
    source_type_id: int = Field(..., description="Тип источника")
    source_name: str = Field(..., description="Имя источника")
    start_at: datetime = Field(
        ...,
        description="Начало временного диапазона поиска",
        example="2025-01-01T10:00:00",
    )
    end_at: datetime = Field(
        ...,
        description="Конец временного диапазона поиска",
        example="2025-01-01T10:00:30",
    )


class CreateSearchJobResponse(BaseModel):
    job_id: str = Field(
        ...,
        description="Идентификатор созданной задачи поиска",
    )
    status: str = Field(
        ...,
        description="Начальный статус задачи",
        example="CREATED",
    )


class SearchJobResponse(BaseModel):
    id: str
    title: str
    text_query: str
    source_id: str
    source_type_id: int
    source_name: str
    status: str
    progress: float
    start_at: str
    end_at: str

class SearchJobEventItemResponse(BaseModel):
    kind: Literal["event", "frame"] = Field(
        ...,
        description='Тип результата: "event" (событие/трек) или "frame" (отдельный кадр)',
        examples=["event"],
    )
    track_id: Optional[int] = Field(
        ...,
        description="Идентификатор трека (если есть), иначе null",
    )
    job_id: str = Field(
        ...,
        description="Идентификатор задачи поиска",
    )
    best_score: float = Field(
        ...,
        description="Лучший итоговый score внутри события или кадра",
    )
    best_object_id: Optional[str] = Field(
        ...,
        description="Идентификатор объекта с максимальным score внутри события; для кадров None",
    )
    preview_url: str = Field(
        ...,
        description="URL превью-снимка (кадр с выделенным bbox или просто кадр)",
    )
    start_at: Optional[str] = Field(
        None,
        description=(
            "Начало интервала события (ISO 8601). "
            'Для kind="event" заполнено, для kind="frame" = null.'
        ),
        example="2025-01-01T10:00:00",
    )
    end_at: Optional[str] = Field(
        None,
        description=(
            "Конец интервала события (ISO 8601). "
            'Для kind="event" заполнено, для kind="frame" = null.'
        ),
        example="2025-01-01T10:00:05",
    )
    at: Optional[str] = Field(
        None,
        description=(
            'Конкретный момент кадра для превью (ISO 8601). '
            'Для kind="frame" — сам кадр, '
            'для kind="event" — кадр-превью лучшего объекта.'
        ),
        example="2025-01-01T10:00:02",
    )


class SearchJobEventFrameResponse(BaseModel):
    event_id: str = Field(
        ...,
        description="Идентификатор строки search_job_events",
    )
    job_id: str = Field(
        ...,
        description="Идентификатор задачи поиска",
    )
    track_id: Optional[int] = Field(
        ...,
        description="Идентификатор трека (может быть null)",
    )
    object_id: str = Field(
        ...,
        description="Идентификатор объекта внутри события",
    )
    score: float = Field(
        ...,
        description="Итоговый score для данного объекта внутри события",
    )
    at: str = Field(
        ...,
        description="Момент времени кадра (ISO 8601)",
    )
    url: str = Field(
        ...,
        description="URL снимка кадра с выделенным bbox этого объекта",
    )

class VectorizationStatusResponse(BaseModel):
    status: str = Field(
        ...,
        description=(
            'Статус покрытия интервала векторами: '
            '"FULLY_VECTORIZED", "PARTIALLY_VECTORIZED" или "NOT_VECTORIZED".'
        ),
        examples=["FULLY_VECTORIZED"],
    )
    missing_ranges: List[DateTimeRangeSchema] = Field(
        ...,
        description=(
            "Список недостающих интервалов. Пустой список, если всё покрыто."
        ),
    )

class CreateVectorizationJobRequest(BaseModel):
    source_id: str = Field(
        ...,
        description="Идентификатор источника (камеры/видео)",
        example="test-source-id-1",
    )
    source_type_id: int = Field(
        ...,
        description="Тип источника (как в таблице sources/source_type_id)",
        example=1,
    )
    source_name: str = Field(
        ...,
        description="Человекочитаемое имя источника",
        example="Камера у входа",
    )
    ranges: List[DateTimeRangeSchema] = Field(
        ...,
        description=(
            "Список интервалов, для которых нужно выполнить векторизацию "
            "и анализ (в реальном времени источника)."
        ),
    )


class CreateVectorizationJobResponse(BaseModel):
    job_id: str = Field(
        ...,
        description="Идентификатор созданной задачи векторизации",
    )
    status: str = Field(
        ...,
        description="Начальный статус задачи",
        example="CREATED",
    )


class VectorizationJobItemResponse(BaseModel):
    id: str = Field(
        ...,
        description="Идентификатор задачи векторизации",
    )
    source_id: str = Field(
        ...,
        description="Идентификатор источника, к которому относится задача",
    )
    source_type_id: int = Field(
        ...,
        description="Тип источника",
        example=1,
    )
    source_name: str = Field(
        ...,
        description="Человекочитаемое имя источника",
        example="Камера у входа",
    )
    status: str = Field(
        ...,
        description="Текущий статус задачи",
        example="PENDING",
    )
    progress: float = Field(
        ...,
        description="Прогресс выполнения задачи в процентах (0..100)",
        example=42.5,
    )
    error: Optional[str] = Field(
        None,
        description="Текст ошибки, если задача завершилась с ошибкой",
    )
    ranges: List[DateTimeRangeSchema] = Field(
        ...,
        description="Список интервалов, которые планируется (или была) векторизованы",
    )

# ---------- Эндпоинты ----------


# @router.post(
#     "/video/process-fragment",
#     response_model=ProcessVideoFragmentResponse,
#     status_code=202,
#     summary="Обработать фрагмент видео",
#     description=(
#         "Запускает пайплайн обработки видеофрагмента для заданного источника и "
#         "списка интервалов: сохранение кадров, эмбеддинги, детекция объектов и т.п."
#     ),
# )
# async def process_video_fragment(
#     payload: ProcessVideoFragmentRequest,
#     background_tasks: BackgroundTasks,
# ) -> ProcessVideoFragmentResponse:
#     ranges_payload = [
#         {
#             "start_at": r.start_at.isoformat(),
#             "end_at": r.end_at.isoformat(),
#         }
#         for r in payload.ranges
#     ]
#
#     background_tasks.add_task(
#         process_video_fragment_usecase,
#         source_id=payload.source_id,
#         source_type_id=payload.source_type_id,
#         ranges=ranges_payload,
#     )
#
#     return ProcessVideoFragmentResponse(detail="Video processing started")


@router.get(
    "/sources",
    response_model=List[SourceResponse],
    summary="Получить список источников",
    description="Возвращает все источники, известные системе (таблица sources).",
)
async def get_sources() -> List[SourceResponse]:
    sources: List[Source] = await list_sources_usecase()
    return [
        SourceResponse(
            id=str(src.id),
            source_id=src.source_id,
            source_type_id=src.source_type_id,
            source_name=src.source_name,
        )
        for src in sources
    ]


@router.get(
    "/sources/{source_id}/periods",
    response_model=List[VectorizedPeriodResponse],
    summary="Получить векторизованные периоды для источника",
    description=(
        "Возвращает список интервалов, для которых уже выполнена векторизация "
        "по данному источнику."
    ),
)
async def get_vectorized_periods_for_source(
    source_id: str,
) -> List[VectorizedPeriodResponse]:
    periods: List[VectorizedPeriod] = (
        await list_vectorized_periods_for_source_usecase(source_id)
    )

    return [
        VectorizedPeriodResponse(
            id=str(p.id),
            source_id=p.source_id,
            start_at=p.start_at,
            end_at=p.end_at,
        )
        for p in periods
    ]


@router.post(
    "/jobs",
    response_model=CreateSearchJobResponse,
    status_code=202,
    summary="Создать задачу поиска",
    description=(
        "Создаёт задачу поиска по текстовому запросу в пределах указанного интервала "
        "для конкретного источника. Поиск выполняется асинхронно воркером."
    ),
)
async def create_search_job(
    payload: CreateSearchJobRequest,
) -> CreateSearchJobResponse:
    job_id = await create_search_job_usecase(
        title=payload.title,
        text_query=payload.text_query,
        source_id=payload.source_id,
        source_type_id=payload.source_type_id,
        source_name=payload.source_name,
        start_at=payload.start_at.isoformat(),
        end_at=payload.end_at.isoformat(),
    )

    return CreateSearchJobResponse(
        job_id=job_id,
        status="CREATED",
    )


@router.get(
    "/jobs",
    response_model=List[SearchJobResponse],
    summary="Список задач поиска",
    description="Возвращает все задачи поиска (активные и завершённые).",
)
async def list_search_jobs() -> List[SearchJobResponse]:
    jobs = await list_search_jobs_usecase()

    result: List[SearchJobResponse] = []
    for j in jobs:
        # SearchJob — доменная датакласс-модель, аккуратно маппим в схему ответа
        result.append(
            SearchJobResponse(
                id=str(j.id),
                title=j.title,
                text_query=j.text_query,
                source_id=j.source_id,
                source_type_id=j.source_type_id,
                source_name=j.source_name,
                status=j.status,
                progress=j.progress,
                start_at=j.start_at,
                end_at=j.end_at,
            )
        )

    return result

@router.get(
    "/jobs/{job_id}/events",
    response_model=List[SearchJobEventItemResponse],
    summary="Список событий для задачи поиска",
    description=(
        "Группирует результаты поиска по track_id и возвращает события с превью "
        '(кадр с выделенным bbox объекта или кадр, если kind="frame").'
    ),
)
async def list_search_job_events(
    job_id: str,
) -> List[SearchJobEventItemResponse]:
    items = await list_job_events_usecase(job_id=job_id)
    return [SearchJobEventItemResponse(**item) for item in items]


@router.get(
    "/jobs/{job_id}/events/{track_id}/frames",
    response_model=List[SearchJobEventFrameResponse],
    summary="Кадры внутри события",
    description=(
        "Возвращает все объекты/кадры внутри одного события (одного track_id) "
        "с URL снимков кадра и bbox для каждого объекта."
    ),
)
async def list_search_job_event_frames(
    job_id: str,
    track_id: int,
) -> List[SearchJobEventFrameResponse]:
    items = await list_event_frames_usecase(
        job_id=job_id,
        track_id=track_id,
    )
    return [SearchJobEventFrameResponse(**item) for item in items]

@router.get(
    "/sources/{source_id}/vectorization-status",
    response_model=VectorizationStatusResponse,
    summary="Проверить, есть ли векторизация для интервала",
    description=(
        "По source_id и интервалу времени возвращает статус покрытия "
        "векторами и список недостающих подинтервалов."
    ),
)
async def get_vectorization_status_for_interval(
    source_id: str,
    start_at: datetime = Query(..., description="Начало интервала (ISO 8601)"),
    end_at: datetime = Query(..., description="Конец интервала (ISO 8601)"),
) -> VectorizationStatusResponse:
    result = await check_vectorized_fragment_usecase(
        source_id=source_id,
        start_at=start_at.isoformat(),
        end_at=end_at.isoformat(),
    )

    missing = [
        DateTimeRangeSchema(
            start_at=datetime.fromisoformat(r["start_at"]),
            end_at=datetime.fromisoformat(r["end_at"]),
        )
        for r in result["missing_ranges"]
    ]

    return VectorizationStatusResponse(
        status=result["status"],
        missing_ranges=missing,
    )

@router.post(
    "/vectorization/jobs",
    response_model=CreateVectorizationJobResponse,
    status_code=202,
    summary="Создать задачу векторизации",
    description=(
        "Создаёт задачу на векторизацию указанных интервалов для источника. "
        "Фактическая обработка запускается асинхронно воркером."
    ),
)
async def create_vectorization_job(
    payload: CreateVectorizationJobRequest,
) -> CreateVectorizationJobResponse:
    ranges_payload = [
        {
            "start_at": r.start_at.isoformat(),
            "end_at": r.end_at.isoformat(),
        }
        for r in payload.ranges
    ]

    job_id = await create_vectorization_job_usecase(
        source_id=payload.source_id,
        source_type_id=payload.source_type_id,
        source_name=payload.source_name,
        ranges=ranges_payload,
    )

    return CreateVectorizationJobResponse(
        job_id=str(job_id),
        status="CREATED",
    )

@router.get(
    "/vectorization/jobs",
    response_model=List[VectorizationJobItemResponse],
    summary="Список задач векторизации",
    description="Возвращает все задачи векторизации (для мониторинга/админки).",
)
async def list_vectorization_jobs() -> List[VectorizationJobItemResponse]:
    jobs: List[VectorizationJob] = await list_vectorization_jobs_usecase()

    items: List[VectorizationJobItemResponse] = []

    for j in jobs:
        ranges = [
            DateTimeRangeSchema(
                start_at=datetime.fromisoformat(r["start_at"]),
                end_at=datetime.fromisoformat(r["end_at"]),
            )
            for r in j.ranges
        ]

        items.append(
            VectorizationJobItemResponse(
                id=str(j.id),
                source_id=j.source_id,
                source_type_id=j.source_type_id,
                source_name=j.source_name,
                status=j.status,
                progress=j.progress,
                error=j.error,
                ranges=ranges,
            )
        )

    return items

@router.get(
    "/vectorization/jobs/{job_id}",
    response_model=VectorizationJobItemResponse,
    summary="Детали задачи векторизации",
    description="Возвращает детальную информацию по одной задаче векторизации.",
)
async def get_vectorization_job(
    job_id: str,
) -> VectorizationJobItemResponse:
    job = await get_vectorization_job_usecase(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Vectorization job not found")

    ranges = [
        DateTimeRangeSchema(
            start_at=datetime.fromisoformat(r["start_at"]),
            end_at=datetime.fromisoformat(r["end_at"]),
        )
        for r in job.ranges
    ]

    return VectorizationJobItemResponse(
        id=str(job.id),
        source_id=job.source_id,
        source_type_id=job.source_type_id,
        source_name=job.source_name,
        status=job.status,
        progress=job.progress,
        error=job.error,
        ranges=ranges,
    )

