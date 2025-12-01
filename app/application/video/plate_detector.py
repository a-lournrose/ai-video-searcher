from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from ultralytics import YOLO

from app.config import YOLO_PLATES_MODEL


@dataclass(frozen=True)
class PlateDetection:
    """
    Детекция номера на кропе ТС.
    Координаты относительно изображения-аргумента (обычно кроп машины).
    """
    x: int
    y: int
    width: int
    height: int
    confidence: float


_YOLO_PLATES_MODEL_INSTANCE: Optional[YOLO] = None


def _get_plates_model() -> YOLO:
    """
    Ленивая загрузка модели номеров.
    """
    global _YOLO_PLATES_MODEL_INSTANCE

    if _YOLO_PLATES_MODEL_INSTANCE is None:
        if not YOLO_PLATES_MODEL.exists():
            raise FileNotFoundError(f"YOLO plates model not found: {YOLO_PLATES_MODEL}")

        _YOLO_PLATES_MODEL_INSTANCE = YOLO(str(YOLO_PLATES_MODEL))

    return _YOLO_PLATES_MODEL_INSTANCE


def detect_plates_on_vehicle(
    vehicle_image: np.ndarray,
    conf_thres: float = 0.25,
) -> List[PlateDetection]:
    """
    Запускает детекцию номеров на кропе транспортного средства.
    Возвращает список PlateDetection с координатами внутри vehicle_image.
    """
    model = _get_plates_model()

    h, w = vehicle_image.shape[:2]
    result = model(vehicle_image, conf=conf_thres, verbose=False)[0]
    boxes = result.boxes

    detections: List[PlateDetection] = []

    for box in boxes:
        x1, y1, x2, y2 = _xyxy_from_box(box)

        x1_i = max(0, int(x1))
        y1_i = max(0, int(y1))
        x2_i = min(w, int(x2))
        y2_i = min(h, int(y2))

        if x2_i <= x1_i or y2_i <= y1_i:
            continue

        conf = float(box.conf[0])

        detections.append(
            PlateDetection(
                x=x1_i,
                y=y1_i,
                width=x2_i - x1_i,
                height=y2_i - y1_i,
                confidence=conf,
            )
        )

    return detections


def _xyxy_from_box(box) -> Tuple[float, float, float, float]:
    x1 = float(box.xyxy[0][0])
    y1 = float(box.xyxy[0][1])
    x2 = float(box.xyxy[0][2])
    y2 = float(box.xyxy[0][3])
    return x1, y1, x2, y2
