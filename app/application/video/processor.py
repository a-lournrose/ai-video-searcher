from __future__ import annotations

import asyncio
from typing import Optional
from uuid import uuid4

import numpy as np

from app.application.video.frame_iterator import iter_default_video_frames, RawFrame
from app.application.video.object_detector import (
    detect_objects_on_frame,
    DetectedObject,
    DetectedObjectCategory,
)
from app.application.video.plate_detector import (
    detect_plates_on_vehicle,
    PlateDetection,
)
from app.application.video.car_color_extractor import (
    extract_car_hsv_profile,
    CarColorProfile,
)
from app.application.video.plate_ocr import (
    recognize_plate_from_image,
    PlateOcrResult,
)
from app.application.video.person_color_extractor import (
    extract_person_color_profile,
    PersonColorProfile,
    RegionColor,
)
from app.application.embeddings.ruclip_embedder import (
    embed_frame_from_raw,
    embed_object_on_frame,
)

from app.domain.frame import Frame
from app.domain.object import Object as DomainObject, BBox as DomainBBox
from app.domain.attributes import TransportAttributes, PersonAttributes
from app.domain.value_objects import (
    FrameId,
    ObjectId,
    ObjectType,
    TransportAttrsId,
    PersonAttrsId,
)

from app.infrastructure.db.postgres import PostgresDatabase, load_config_from_env
from app.infrastructure.repositories import (
    FramePostgresRepository,
    ObjectPostgresRepository,
    TransportAttributesPostgresRepository,
    PersonAttributesPostgresRepository,
    EmbeddingPostgresRepository,
)


async def process_video() -> None:
    """
    Главный пайплайн обработки видео.

    - frames: записи + эмбеддинги
    - objects: PERSON / TRANSPORT
    - embeddings: для кадров и объектов
    - transport_attrs: цвет (HSV-строка), номер
    - person_attrs: верх/низ одежды (HSV-строки)
    """
    config = load_config_from_env()
    db = PostgresDatabase(config)
    await db.connect()

    try:
        frame_repo = FramePostgresRepository(db)
        object_repo = ObjectPostgresRepository(db)
        transport_attrs_repo = TransportAttributesPostgresRepository(db)
        person_attrs_repo = PersonAttributesPostgresRepository(db)
        embedding_repo = EmbeddingPostgresRepository(db)

        print("=== Video processing started ===")

        total_frames = 0
        total_persons = 0
        total_transport = 0
        total_objects_saved = 0
        total_embeddings_saved = 0
        total_transport_attrs_saved = 0
        total_person_attrs_saved = 0

        for raw in iter_default_video_frames():
            # 1. Сохраняем кадр
            frame = _raw_frame_to_frame_entity(raw)
            await frame_repo.create(frame)
            total_frames += 1

            # 2. Эмбеддинг кадра
            try:
                frame_embedding = embed_frame_from_raw(raw, frame.id)
                await embedding_repo.create(frame_embedding)
                total_embeddings_saved += 1
            except Exception as exc:
                print(f"[WARN] frame embedding failed for frame {frame.id}: {exc}")

            # 3. Детекция объектов
            detections = detect_objects_on_frame(raw, conf_thres=0.25)

            # 4. Маппим YOLO-детекции в доменные Object
            det_obj_pairs: list[tuple[DetectedObject, DomainObject]] = []
            for det in detections:
                obj = _detected_to_domain_object(det, frame.id)
                det_obj_pairs.append((det, obj))

            # 5. Сохраняем объекты + эмбеддинги объектов
            for det, obj in det_obj_pairs:
                await object_repo.create(obj)
                total_objects_saved += 1

                try:
                    obj_embedding = embed_object_on_frame(raw.image, obj)
                    await embedding_repo.create(obj_embedding)
                    total_embeddings_saved += 1
                except Exception as exc:
                    print(f"[WARN] object embedding failed for object {obj.id}: {exc}")

            persons_on_frame = sum(
                1 for d, _ in det_obj_pairs if d.category == DetectedObjectCategory.PERSON
            )
            transport_on_frame = sum(
                1 for d, _ in det_obj_pairs if d.category == DetectedObjectCategory.TRANSPORT
            )

            total_persons += persons_on_frame
            total_transport += transport_on_frame

            # 6. Обработка TRANSPORT / PERSON для атрибутов
            person_index = 0
            transport_index = 0

            for det, obj in det_obj_pairs:
                if det.category == DetectedObjectCategory.TRANSPORT:
                    car_crop = _crop_from_bbox(
                        raw.image,
                        det.bbox.x,
                        det.bbox.y,
                        det.bbox.width,
                        det.bbox.height,
                    )

                    color_profile = _safe_extract_car_color(car_crop)
                    plate_ocr_result = _safe_detect_and_ocr_plate(car_crop)

                    # HSV-строка для БД (если цвета нет — пустая строка)
                    color_str = _color_profile_to_hsv_string(color_profile) or ""
                    plate_norm = (
                        plate_ocr_result.normalized_plate
                        if plate_ocr_result is not None
                        else None
                    )

                    try:
                        transport_attrs = TransportAttributes(
                            id=TransportAttrsId(str(uuid4())),
                            object_id=obj.id,
                            color_hsv=color_str,
                            license_plate=plate_norm,
                        )
                        await transport_attrs_repo.create(transport_attrs)
                        total_transport_attrs_saved += 1
                    except Exception as exc:
                        print(
                            f"[WARN] transport attrs save failed for object {obj.id}: {exc}"
                        )

                    _log_transport_analysis(
                        raw=raw,
                        det=det,
                        transport_index=transport_index,
                        color_profile=color_profile,
                        plate_result=plate_ocr_result,
                    )

                    transport_index += 1

                elif det.category == DetectedObjectCategory.PERSON:
                    person_crop = _crop_from_bbox(
                        raw.image,
                        det.bbox.x,
                        det.bbox.y,
                        det.bbox.width,
                        det.bbox.height,
                    )

                    person_colors = _safe_extract_person_color(person_crop)

                    upper_str = _region_color_to_hsv_string(
                        person_colors.upper_color if person_colors else None
                    )
                    lower_str = _region_color_to_hsv_string(
                        person_colors.lower_color if person_colors else None
                    )

                    try:
                        person_attrs = PersonAttributes(
                            id=PersonAttrsId(str(uuid4())),
                            object_id=obj.id,
                            upper_color_hsv=upper_str,
                            lower_color_hsv=lower_str,
                        )
                        await person_attrs_repo.create(person_attrs)
                        total_person_attrs_saved += 1
                    except Exception as exc:
                        print(
                            f"[WARN] person attrs save failed for object {obj.id}: {exc}"
                        )

                    _log_person_analysis(
                        raw=raw,
                        det=det,
                        person_index=person_index,
                        profile=person_colors,
                    )

                    person_index += 1

            # 7. Сводный лог по кадру
            if total_frames <= 5 or total_frames % 10 == 0:
                _log_frame_summary(
                    raw=raw,
                    detections=[d for d, _ in det_obj_pairs],
                    objects_on_frame=len(det_obj_pairs),
                    persons_on_frame=persons_on_frame,
                    transport_on_frame=transport_on_frame,
                )

        print("=== Video processing finished ===")
        print(f"  Frames processed                : {total_frames}")
        print(f"  Objects saved (total)           : {total_objects_saved}")
        print(f"  Embeddings saved (frame+object) : {total_embeddings_saved}")
        print(f"    Persons detected              : {total_persons}")
        print(f"    Transport detected            : {total_transport}")
        print(f"  TransportAttributes saved       : {total_transport_attrs_saved}")
        print(f"  PersonAttributes saved          : {total_person_attrs_saved}")

    finally:
        await db.close()


def _raw_frame_to_frame_entity(raw: RawFrame) -> Frame:
    return Frame(
        id=FrameId(str(uuid4())),
        timestamp_sec=raw.timestamp_sec,
    )


def _detected_to_domain_object(
    det: DetectedObject,
    frame_id: FrameId,
) -> DomainObject:
    if det.category == DetectedObjectCategory.PERSON:
        obj_type = ObjectType.PERSON
    elif det.category == DetectedObjectCategory.TRANSPORT:
        obj_type = ObjectType.TRANSPORT
    else:
        raise ValueError(f"Unsupported category: {det.category}")

    bbox = DomainBBox(
        x=det.bbox.x,
        y=det.bbox.y,
        width=det.bbox.width,
        height=det.bbox.height,
    )

    return DomainObject(
        id=ObjectId(str(uuid4())),
        frame_id=frame_id,
        type=obj_type,
        bbox=bbox,
    )


def _crop_from_bbox(
    image: np.ndarray,
    x: int,
    y: int,
    width: int,
    height: int,
) -> np.ndarray:
    h, w = image.shape[:2]

    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(w, x + width)
    y2 = min(h, y + height)

    if x2 <= x1 or y2 <= y1:
        return image[0:0, 0:0]

    return image[y1:y2, x1:x2]


def _safe_extract_car_color(car_crop: np.ndarray) -> Optional[CarColorProfile]:
    if car_crop.size == 0:
        return None

    try:
        return extract_car_hsv_profile(car_crop)
    except Exception as exc:
        print(f"[WARN] car color extraction failed: {exc}")
        return None


def _safe_detect_and_ocr_plate(car_crop: np.ndarray) -> Optional[PlateOcrResult]:
    if car_crop.size == 0:
        return None

    try:
        plate_detections = detect_plates_on_vehicle(car_crop, conf_thres=0.25)
    except Exception as exc:
        print(f"[WARN] plate detection failed: {exc}")
        return None

    if not plate_detections:
        return None

    best_plate: PlateDetection = max(plate_detections, key=lambda d: d.confidence)

    plate_crop = _crop_from_bbox(
        car_crop,
        best_plate.x,
        best_plate.y,
        best_plate.width,
        best_plate.height,
    )

    if plate_crop.size == 0:
        return None

    try:
        return recognize_plate_from_image(plate_crop)
    except Exception as exc:
        print(f"[WARN] plate OCR failed: {exc}")
        return None


def _safe_extract_person_color(person_crop: np.ndarray) -> Optional[PersonColorProfile]:
    if person_crop.size == 0:
        return None

    try:
        return extract_person_color_profile(person_crop)
    except Exception as exc:
        print(f"[WARN] person color extraction failed: {exc}")
        return None


def _hsv_to_string(h: float, s: float, v: float) -> str:
    return f"{h:.1f},{s:.3f},{v:.3f}"


def _color_profile_to_hsv_string(
    profile: Optional[CarColorProfile],
) -> Optional[str]:
    if profile is None:
        return None
    return _hsv_to_string(profile.h, profile.s, profile.v)


def _region_color_to_hsv_string(
    region: Optional[RegionColor],
) -> Optional[str]:
    if region is None:
        return None
    return _hsv_to_string(region.h, region.s, region.v)


def _log_frame_summary(
    raw: RawFrame,
    detections: list[DetectedObject],
    objects_on_frame: int,
    persons_on_frame: int,
    transport_on_frame: int,
) -> None:
    print(
        f"[frame #{raw.index:04d} @ {raw.timestamp_sec:6.3f}s] "
        f"objects={objects_on_frame}, persons={persons_on_frame}, "
        f"transport={transport_on_frame}, detections_raw={len(detections)}"
    )


def _format_region_color(prefix: str, region: Optional[RegionColor]) -> str:
    if region is None:
        return f"{prefix}: n/a"

    h, s, v = region.h, region.s, region.v
    return (
        f"{prefix}: HSV=({h:6.1f}, {s:4.2f}, {v:4.2f}), "
        f"pixels={region.pixel_count}, "
        f"chromatic={region.is_chromatic}"
    )


def _log_transport_analysis(
    raw: RawFrame,
    det: DetectedObject,
    transport_index: int,
    color_profile: Optional[CarColorProfile],
    plate_result: Optional[PlateOcrResult],
) -> None:
    color_part = "color: n/a"
    if color_profile is not None:
        h, s, v = color_profile.h, color_profile.s, color_profile.v
        color_part = (
            f"color: HSV=({h:6.1f}, {s:4.2f}, {v:4.2f}), "
            f"pixels={color_profile.pixel_count}, "
            f"chromatic={color_profile.is_chromatic}"
        )

    plate_part = "plate: n/a"
    if plate_result is not None:
        plate_part = (
            f"plate: raw='{plate_result.raw_text}', "
            f"normalized='{plate_result.normalized_plate}'"
        )

    print(
        f"[frame #{raw.index:04d} @ {raw.timestamp_sec:6.3f}s] "
        f"TRANSPORT[{transport_index}] {color_part}; {plate_part}"
    )


def _log_person_analysis(
    raw: RawFrame,
    det: DetectedObject,
    person_index: int,
    profile: Optional[PersonColorProfile],
) -> None:
    if profile is None:
        upper_part = "upper: n/a"
        lower_part = "lower: n/a"
    else:
        upper_part = _format_region_color("upper", profile.upper_color)
        lower_part = _format_region_color("lower", profile.lower_color)

    print(
        f"[frame #{raw.index:04d} @ {raw.timestamp_sec:6.3f}s] "
        f"PERSON[{person_index}] {upper_part}; {lower_part}"
    )


if __name__ == "__main__":
    asyncio.run(process_video())