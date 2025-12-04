from __future__ import annotations
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from app.application.search.search_service import search_by_text
from app.application.video.frame_snapshot import save_frame_with_optional_bbox

from app.domain.search_job import SearchJob
from app.domain.value_objects import SearchJobId
from app.domain.repositories.search_job_repository import SearchJobRepository

from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories.search_job_postgres_repository import SearchJobPostgresRepository
from app.domain.object import BBox

async def _run_job(job_id: SearchJobId):
    """
    Фоновый воркер — с реальным прогрессом + snapshot-ами.
    """

    db = PostgresDatabase(load_config_from_env())
    await db.connect()
    repo = SearchJobPostgresRepository(db)

    try:
        job = await repo.find_by_id(job_id)
        if job is None:
            return

        await repo.update_status(job_id, "RUNNING", None)
        await repo.update_progress(job_id, 1.0)

        # -------- 1. SEARCH --------
        hits = await search_by_text(
            db=db,
            text=job.text_query,
            source_id=job.source_id,
            start_at=job.start_at,
            end_at=job.end_at,
        )

        total = len(hits)
        await repo.update_progress(job_id, 10.0)

        # -------- 2. SAVE RESULTS JSON --------
        result_dir = Path(f"storage/search_results/{job_id}")
        result_dir.mkdir(parents=True, exist_ok=True)

        with open(result_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump([h.__dict__ for h in hits], f, indent=4, ensure_ascii=False)

        await repo.update_progress(job_id, 30.0)

        # -------- 3. SNAPSHOTS --------
        snap_dir = result_dir / "snapshots"
        snap_dir.mkdir(exist_ok=True)

        if total > 0:
            per = 70.0 / total
        else:
            per = 70.0

        for i, hit in enumerate(hits, start=1):
            bbox = None
            if hit.object_id:
                row = await db.fetchrow("""
                                        SELECT bbox_x, bbox_y, bbox_width, bbox_height
                                        FROM objects
                                        WHERE id = $1
                                        """, hit.object_id)

                bbox = None
                if row:
                    bbox = BBox(
                        x=row["bbox_x"],
                        y=row["bbox_y"],
                        width=row["bbox_width"],
                        height=row["bbox_height"],
                    )

            save_frame_with_optional_bbox(
                timestamp_sec=hit.timestamp_sec,
                out_path=snap_dir / f"{i:04d}_{hit.frame_id}.jpg",
                bbox=bbox,
            )

            await repo.update_progress(job_id, min(30 + per * i, 99.0))

        await repo.update_progress(job_id, 100.0)
        await repo.update_status(job_id, "DONE", None)
        print(f"\n✔ Результаты сохранены → {result_dir}\n")

    except Exception as exc:
        await repo.update_status(job_id, "FAILED", str(exc))
        raise exc

    finally:
        await db.close()

async def create_job(
    repo: SearchJobRepository,
    db: PostgresDatabase,
    *,
    title: str,
    text_query: str,
    source_id: str,
    start_at: str,
    end_at: str,
) -> SearchJobId:
    """
    Регистрирует задачу в БД + запускает воркер в фоне.
    """

    job_id = SearchJobId(str(uuid4()))

    job = SearchJob(
        id=job_id,
        title=title,
        text_query=text_query,
        source_id=source_id,
        start_at=start_at,
        end_at=end_at,
        progress=0.0,
        status="PENDING",
        error=None,
    )
    await repo.create(job)

    # ВАЖНО → worker запускается, но main.py не должен завершаться мгновенно
    asyncio.create_task(_run_job(job_id))

    return job_id
