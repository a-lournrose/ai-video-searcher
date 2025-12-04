from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODELS_DIR = PROJECT_ROOT / "models"
YOLO_OBJECTS_MODEL = MODELS_DIR / "yolo_objects.pt"
YOLO_PLATES_MODEL    = MODELS_DIR / "yolo_plates.pt"

DATA_DIR = PROJECT_ROOT / "data"

# VIDEO_PATH = DATA_DIR / "video.mp4"
VIDEO_SOURCE = "http://localhost:8000/media/f82163e0181d49468c29657336ffe179/index.m3u8"

TARGET_FPS = 2.0
