from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Response

from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.application.video.snapshot_service import (
    get_snapshot_jpeg,
    SnapshotNotFoundError,
    SnapshotGenerationError,
)


router = APIRouter()


@router.get("/snapshot")
async def snapshot(
    source_id: str,
    at: str,
    object_id: Optional[str] = None,
):
    """
    Тонкий HTTP-эндпоинт.
    Вся бизнес-логика вынесена в snapshot_service.get_snapshot_jpeg.
    """
    db = PostgresDatabase(load_config_from_env())
    await db.connect()

    try:
        try:
            image_bytes = await get_snapshot_jpeg(
                db,
                source_id=source_id,
                at=at,
                object_id=object_id,
            )
        except SnapshotNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        except SnapshotGenerationError as exc:
            raise HTTPException(status_code=500, detail=str(exc))

        return Response(
            content=image_bytes,
            media_type="image/jpeg",
        )
    finally:
        await db.close()
