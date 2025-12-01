#!/usr/bin/env bash

# 0) Чистим старый venv
deactivate 2>/dev/null || true
rm -rf .venv

# 1) Создаём и активируем venv
python3 -m venv .venv
source .venv/bin/activate

# 2) Инструменты сборки
python -m pip install --upgrade pip==24.2 setuptools==70.0.0 wheel==0.44.0

# 3) Базовые пакеты (cv2, numpy, pillow, tqdm)
pip install \
  numpy==1.26.4 \
  pillow==10.4.0 \
  tqdm==4.66.5 \
  opencv-python-headless==4.10.0.84 \
  --extra-index-url https://download.pytorch.org/whl/cpu

# 4) Стек ruclip без автозависимостей (как у тебя)
pip install --force-reinstall \
  "transformers==4.25.1" \
  "torch==2.3.0+cpu" \
  "huggingface_hub==0.23.0" \
  "ruclip==0.0.2" \
  --no-deps \
  --extra-index-url https://download.pytorch.org/whl/cpu

# 5) Явно докидываем РОВНО те зависимости, которых не хватает из-за --no-deps
pip install \
  typing_extensions==4.12.2 \
  more-itertools==8.12.0 \
  torchvision==0.18.0+cpu \
  youtokentome==1.0.6 \
  filelock==3.14.0 \
  fsspec==2024.2.0 \
  jinja2==3.1.4 \
  networkx==3.2.1 \
  sympy==1.12 \
  packaging==24.1 \
  pyyaml==6.0.2 \
  requests==2.32.3 \
  --extra-index-url https://download.pytorch.org/whl/cpu

pip install "fastapi>=0.115" "uvicorn[standard]>=0.30" "python-multipart>=0.0.9"

# 6) Чистим кэш HF и отключаем проверку ETag (как ты делал)
rm -rf ~/.cache/huggingface/hub
export HF_HUB_DISABLE_ETAG=true

# 7) YOLO (Ultralytics) без автозависимостей + необходимые минимальные зависимости
pip install ultralytics==8.3.0 --no-deps

pip install \
  psutil \
  matplotlib \
  pandas

pip install pytesseract rapidfuzz

pip install asyncpg python-dotenv