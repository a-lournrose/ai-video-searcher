from __future__ import annotations

import asyncio
from datetime import datetime
import sys

from app.config import PROJECT_ROOT
from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories import ObjectPostgresRepository
from app.domain.value_objects import ObjectId
from app.application.search.search_service import search_by_text
from app.application.video.frame_snapshot import save_frame_with_optional_bbox

MAX_CANDIDATES = 2000


async def main() -> None:
    config = load_config_from_env()
    db = PostgresDatabase(config)
    await db.connect()

    try:
        # 1. Берём текст запроса либо из аргументов CLI, либо из stdin
        if len(sys.argv) > 1:
            text = " ".join(sys.argv[1:]).strip()
        else:
            print("=== Text search demo ===")
            try:
                text = input("Введите текстовый запрос: ").strip()
            except UnicodeDecodeError:
                print(
                    "Ошибка чтения ввода из терминала.\n"
                    "Пожалуйста, передайте запрос как аргумент командной строки, например:\n"
                    "  python -m app.application.search.search_demo \"человек в красной куртке\""
                )
                return

        if not text:
            print("Пустой запрос, выходим.")
            return

        # 2. Запуск поиска
        hits = await search_by_text(
            db=db,
            text=text,
            max_candidates=MAX_CANDIDATES,
            clip_min_pure=0.30,
            final_min=0.30,
        )

        print(f"\nЗапрос: {text}")
        print(f"Найдено результатов: {len(hits)}")

        if not hits:
            return

        # 3. Каталог для сохранения кадров
        run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_root = PROJECT_ROOT / "out" / "search_results" / run_ts
        out_root.mkdir(parents=True, exist_ok=True)

        object_repo = ObjectPostgresRepository(db)

        # 4. Обработка и сохранение результатов
        for idx, hit in enumerate(hits, start=1):
            obj_part = f", object_id={hit.object_id}" if hit.object_id is not None else ""
            print(
                f"{idx:03d}. "
                f"type={hit.target_type}, "
                f"frame_id={hit.frame_id}{obj_part}, "
                f"t={hit.timestamp_sec:.3f}s, "
                f"final={hit.final_score:.3f}, "
                f"clip={hit.clip_score:.3f}, "
                f"color={hit.color_score:.3f}, "
                f"plate={hit.plate_score:.3f}"
            )

            score_str = f"{hit.final_score:.3f}".replace(".", "_")
            t_ms = int(round(hit.timestamp_sec * 1000))

            if hit.object_id is not None:
                filename = (
                    f"{idx:03d}_{hit.target_type}_t{t_ms:08d}_score{score_str}_"
                    f"obj_{hit.object_id}.jpg"
                )
            else:
                filename = (
                    f"{idx:03d}_{hit.target_type}_t{t_ms:08d}_score{score_str}.jpg"
                )

            out_path = out_root / filename

            bbox = None
            if hit.object_id is not None:
                obj = await object_repo.find_by_id(ObjectId(hit.object_id))
                if obj is None:
                    print(f"[WARN] object not found in DB: {hit.object_id}")
                else:
                    bbox = obj.bbox

            try:
                save_frame_with_optional_bbox(
                    timestamp_sec=hit.timestamp_sec,
                    out_path=out_path,
                    bbox=bbox,
                )
            except Exception as exc:
                print(f"[WARN] failed to save frame for hit #{idx}: {exc}")

        print(f"\nКадры сохранены в: {out_root}")

    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
