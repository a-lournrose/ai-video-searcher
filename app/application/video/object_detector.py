from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np
from ultralytics import YOLO

from app.config import YOLO_OBJECTS_MODEL
from app.application.video.frame_iterator import RawFrame


_VEHICLE_LABELS = {"car", "truck", "bus", "motorcycle", "train"}


class DetectedObjectCategory(str, Enum):
    PERSON = "PERSON"
    TRANSPORT = "TRANSPORT"


@dataclass(frozen=True)
class BBox:
    """
    Прямоугольник объекта в координатах кадра.
    """
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class DetectedObject:
    """
    Результат детекции одного объекта на кадре.
    """
    frame_index: int
    timestamp_sec: float
    category: DetectedObjectCategory
    label: str
    confidence: float
    bbox: BBox
    track_id: Optional[int] = None


_YOLO_OBJECTS_MODEL_INSTANCE: Optional[YOLO] = None


def _get_objects_model() -> YOLO:
    """
    Ленивая загрузка модели детекции объектов.
    """
    global _YOLO_OBJECTS_MODEL_INSTANCE

    if _YOLO_OBJECTS_MODEL_INSTANCE is None:
        if not YOLO_OBJECTS_MODEL.exists():
            raise FileNotFoundError(f"YOLO objects model not found: {YOLO_OBJECTS_MODEL}")

        _YOLO_OBJECTS_MODEL_INSTANCE = YOLO(str(YOLO_OBJECTS_MODEL))

    return _YOLO_OBJECTS_MODEL_INSTANCE


def detect_objects_on_frame(
    frame: RawFrame,
    conf_thres: float = 0.25,
    use_tracking: bool = False,
) -> List[DetectedObject]:
    """
    Принимает один RawFrame и возвращает список DetectedObject (PERSON / TRANSPORT).

    Если use_tracking=True, использует встроенный трекер YOLO и
    проставляет track_id для объектов.

    Никаких операций с БД — только детекция/трекинг.
    """
    model = _get_objects_model()

    image: np.ndarray = frame.image
    height, width = image.shape[:2]

    if use_tracking:
        # persist=True — YOLO будет хранить состояние трекера между вызовами
        result = model.track(
            image,
            conf=conf_thres,
            persist=True,
            verbose=False,
        )[0]
    else:
        # Обычная детекция без трекинга
        result = model(
            image,
            conf=conf_thres,
            verbose=False,
        )[0]

    boxes = result.boxes
    names = result.names

    detected: List[DetectedObject] = []

    for box in boxes:
        cls_id = int(box.cls[0])
        raw_label = names.get(cls_id, "")

        if raw_label == "person":
            category = DetectedObjectCategory.PERSON
        elif raw_label in _VEHICLE_LABELS:
            category = DetectedObjectCategory.TRANSPORT
        else:
            # Остальные классы нам пока не интересны
            continue

        x1, y1, x2, y2 = _xyxy_from_box(box)

        x1_i = max(0, int(x1))
        y1_i = max(0, int(y1))
        x2_i = min(width, int(x2))
        y2_i = min(height, int(y2))

        if x2_i <= x1_i or y2_i <= y1_i:
            # Защита от вырожденных боксов
            continue

        bbox = BBox(
            x=x1_i,
            y=y1_i,
            width=x2_i - x1_i,
            height=y2_i - y1_i,
        )

        confidence = float(box.conf[0])

        track_id: Optional[int] = None
        if use_tracking and box.id is not None:
            track_id = int(box.id[0])

        detected.append(
            DetectedObject(
                frame_index=frame.index,
                timestamp_sec=frame.timestamp_sec,
                category=category,
                label=raw_label,
                confidence=confidence,
                bbox=bbox,
                track_id=track_id,
            )
        )

    return detected


def _xyxy_from_box(box) -> Tuple[float, float, float, float]:
    """
    Вытаскивает координаты x1, y1, x2, y2 из YOLO-бокса.
    """
    x1 = float(box.xyxy[0][0])
    y1 = float(box.xyxy[0][1])
    x2 = float(box.xyxy[0][2])
    y2 = float(box.xyxy[0][3])
    return x1, y1, x2, y2
