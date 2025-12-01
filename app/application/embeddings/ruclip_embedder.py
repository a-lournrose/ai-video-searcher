from __future__ import annotations

from typing import List, Optional
from uuid import uuid4

import cv2
import numpy as np
import ruclip
import torch
from PIL import Image

from app.application.video.frame_iterator import RawFrame
from app.domain.embedding import Embedding
from app.domain.object import Object as DomainObject
from app.domain.value_objects import (
    EmbeddingId,
    FrameId,
    EmbeddingEntityType,
)

MODEL_NAME = "ruclip-vit-base-patch32-224"
_DEVICE = "cpu"
_BATCH_SIZE = 8

_PREDICTOR: Optional[ruclip.Predictor] = None


def _get_predictor() -> ruclip.Predictor:
    """
    Ленивая инициализация ruCLIP-предиктора.
    """
    global _PREDICTOR

    if _PREDICTOR is None:
        torch.set_grad_enabled(False)
        clip_model, tokenizer = ruclip.load(MODEL_NAME, device=_DEVICE)
        _PREDICTOR = ruclip.Predictor(
            clip_model,
            tokenizer,
            _DEVICE,
            bs=_BATCH_SIZE,
            templates=None,
        )

    return _PREDICTOR


def _bgr_to_pil(image_bgr: np.ndarray) -> Image.Image:
    """
    Конвертация BGR (OpenCV) -> PIL RGB.
    """
    if image_bgr is None or image_bgr.size == 0:
        raise ValueError("Empty image for embedding")

    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(image_rgb)


def _compute_image_vector(image_bgr: np.ndarray) -> List[float]:
    predictor = _get_predictor()
    img = _bgr_to_pil(image_bgr)

    latents = predictor.get_image_latents([img])
    latents = torch.nn.functional.normalize(latents, dim=1)
    return latents[0].cpu().tolist()


def _compute_text_vector(text: str) -> List[float]:
    predictor = _get_predictor()
    latents = predictor.get_text_latents([text])
    latents = torch.nn.functional.normalize(latents, dim=1)
    return latents[0].cpu().tolist()


def embed_frame_from_raw(raw_frame: RawFrame, frame_id: FrameId) -> Embedding:
    """
    Эмбеддинг целого кадра (FRAME).

    Привязка:
      - entity_type = FRAME
      - frame_id     = переданный id кадра
      - object_id    = None
    """
    vector = _compute_image_vector(raw_frame.image)

    return Embedding(
        id=EmbeddingId(str(uuid4())),
        entity_type=EmbeddingEntityType.FRAME,
        frame_id=frame_id,
        object_id=None,
        vector=vector,
    )


def embed_object_on_frame(frame_bgr: np.ndarray, obj: DomainObject) -> Embedding:
    """
    Эмбеддинг объекта (OBJECT) по его bbox.

    Привязка:
      - entity_type = OBJECT
      - frame_id    = None
      - object_id   = obj.id
    """
    object_crop = _crop_bbox(frame_bgr, obj)
    vector = _compute_image_vector(object_crop)

    return Embedding(
        id=EmbeddingId(str(uuid4())),
        entity_type=EmbeddingEntityType.OBJECT,
        frame_id=None,
        object_id=obj.id,
        vector=vector,
    )


def embed_text(text: str) -> List[float]:
    """
    L2-нормированный эмбеддинг для текстового запроса.
    """
    text = text.strip()
    if not text:
        raise ValueError("Text for embedding must be non-empty")

    return _compute_text_vector(text)


def _crop_bbox(frame_bgr: np.ndarray, obj: DomainObject) -> np.ndarray:
    """
    Кроп кадра по bbox объекта.
    """
    h, w = frame_bgr.shape[:2]
    bbox = obj.bbox

    x1 = max(0, bbox.x)
    y1 = max(0, bbox.y)
    x2 = min(w, bbox.x + bbox.width)
    y2 = min(h, bbox.y + bbox.height)

    if x2 <= x1 or y2 <= y1:
        raise ValueError(f"Invalid bbox for object {obj.id}: {bbox}")

    crop = frame_bgr[y1:y2, x1:x2]
    if crop.size == 0:
        raise ValueError(f"Empty crop for object {obj.id}")

    return crop
