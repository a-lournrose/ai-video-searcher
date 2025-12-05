from __future__ import annotations

from datetime import datetime
from typing import List

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


router = APIRouter(
    prefix="/search",
    tags=["search"],
)


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
        example="f2a1e3e4-4a1f-4c2d-9c41-5d7d7d7d7d7d",
    )
    source_id: str = Field(
        ...,
        description="Внешний идентификатор источника",
        example="test-source-id-1",
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
    status: str
    progress: float
    start_at: str
    end_at: str


# ---------- Эндпоинты ----------


@router.post(
    "/video/process-fragment",
    response_model=ProcessVideoFragmentResponse,
    status_code=202,
    summary="Обработать фрагмент видео",
    description=(
        "Запускает пайплайн обработки видеофрагмента для заданного источника и "
        "списка интервалов: сохранение кадров, эмбеддинги, детекция объектов и т.п."
    ),
)
async def process_video_fragment(
    payload: ProcessVideoFragmentRequest,
) -> ProcessVideoFragmentResponse:
    ranges_payload = [
        {
            "start_at": r.start_at.isoformat(),
            "end_at": r.end_at.isoformat(),
        }
        for r in payload.ranges
    ]

    await process_video_fragment_usecase(
        source_id=payload.source_id,
        ranges=ranges_payload,
    )

    return ProcessVideoFragmentResponse(detail="Video processing started")


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
                status=j.status,
                progress=j.progress,
                start_at=j.start_at,
                end_at=j.end_at,
            )
        )

    return result
