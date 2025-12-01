from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

MODELS_DIR = PROJECT_ROOT / "models"
YOLO_OBJECTS_MODEL = MODELS_DIR / "yolo_objects.pt"
YOLO_PLATES_MODEL    = MODELS_DIR / "yolo_plates.pt"

DATA_DIR = PROJECT_ROOT / "data"

VIDEO_PATH = DATA_DIR / "video.mp4"

TARGET_FPS = 2.0
