from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
import pytesseract
from PIL import Image

# Если tesseract не в PATH — раскомментируй и пропиши путь:
# pytesseract.pytesseract.tesseract_cmd = "/usr/local/bin/tesseract"

# Разрешённые символы для нормализованного номера (латиница + цифры)
ALLOWED_PLATE_CHARS = "ABEKMHOPCTYX0123456789"

# Отображение русских букв в латинские эквиваленты для номеров
RUS_TO_LAT_MAP = {
    "А": "A",
    "В": "B",
    "Е": "E",
    "К": "K",
    "М": "M",
    "Н": "H",
    "О": "O",
    "Р": "P",
    "С": "C",
    "Т": "T",
    "У": "Y",
    "Х": "X",
}


@dataclass(frozen=True)
class PlateOcrResult:
    """
    Результат распознавания номера.
    """
    raw_text: str          # сырой текст от tesseract
    normalized_plate: Optional[str]  # нормализованный номер (или None, если не удалось)


def recognize_plate_from_image(
    image: Image.Image | np.ndarray,
) -> PlateOcrResult:
    """
    Принимает кроп номера (PIL.Image или np.ndarray BGR/GRAY),
    возвращает результат OCR и нормализованный номер (если удалось).
    """
    gray = _to_grayscale(image)
    preprocessed = _preprocess_plate_image(gray)
    raw_text = _run_tesseract(preprocessed)
    normalized = normalize_plate_text(raw_text)
    return PlateOcrResult(raw_text=raw_text, normalized_plate=normalized)


def normalize_plate_text(text: str) -> Optional[str]:
    """
    Нормализует текст, полученный от OCR, в формат номера:
    - upper()
    - убираем все пробелы и неалфавитно-цифровые символы
    - приводим кириллицу к латинице (только допустимый набор)
    - отбрасываем всё, что не входит в ALLOWED_PLATE_CHARS

    Возвращает нормализованную строку или None, если в итоге пусто.
    """
    if not text:
        return None

    cleaned = []
    upper = text.strip().upper()

    for ch in upper:
        if ch.isspace():
            continue

        # Цифры сразу пропускаем, если они валидные
        if ch.isdigit():
            cleaned.append(ch)
            continue

        # Кириллица → латиница, если есть в карте
        if "А" <= ch <= "Я" or ch == "Ё":
            mapped = RUS_TO_LAT_MAP.get(ch, None)
            if mapped is None:
                continue
            ch = mapped

        # Некоторые типичные OCR-путаницы:
        if ch in {"O", "Q"}:
            # Очень часто O/0 путаются, но мы не знаем контекст.
            # Оставляем как букву O (в допустимом наборе).
            ch = "O"
        elif ch in {"I", "L"}:
            # Часто I/L → 1
            ch = "1"
        elif ch == "Z":
            # Иногда Z вместо 2
            ch = "2"
        elif ch == "S":
            # S вместо 5
            ch = "5"
        elif ch == "B":
            # B вместо 8 (но B есть и в алфавите номеров; оставляем как B)
            ch = "B"

        if ch in ALLOWED_PLATE_CHARS:
            cleaned.append(ch)

    if not cleaned:
        return None

    return "".join(cleaned)


# ==============================
# Вспомогательные функции OCR
# ==============================


def _to_grayscale(image: Image.Image | np.ndarray) -> np.ndarray:
    """
    Приводит входное изображение к grayscale np.ndarray (uint8).
    Поддерживает вход в формате PIL.Image или np.ndarray (BGR/GRAY).
    """
    if isinstance(image, Image.Image):
        # PIL → grayscale
        return np.array(image.convert("L"))

    if len(image.shape) == 2:
        # Уже grayscale
        return image

    if len(image.shape) == 3:
        # BGR → GRAY
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    raise ValueError("Unsupported image format for _to_grayscale")


def _preprocess_plate_image(gray: np.ndarray) -> np.ndarray:
    """
    Минимальный препроцессинг кропа номера перед Tesseract:

    - приводим к разумной высоте (чтобы символы были крупнее)
    - никаких бинаризаций / CLAHE / blur — даём Tesseract'у "живую" картинку.
    """
    h, w = gray.shape[:2]

    # Если номер слишком мелкий по высоте — масштабируем вверх
    target_height = 80
    if h < target_height:
        scale = target_height / float(h)
        new_w = int(w * scale)
        gray = cv2.resize(gray, (new_w, target_height), interpolation=cv2.INTER_CUBIC)

    # Если номер слишком огромный — можно чуть уменьшить (не обязательно)
    max_height = 160
    h2, w2 = gray.shape[:2]
    if h2 > max_height:
        scale = max_height / float(h2)
        new_w = int(w2 * scale)
        gray = cv2.resize(gray, (new_w, max_height), interpolation=cv2.INTER_AREA)

    return gray


def _run_tesseract(image: np.ndarray) -> str:
    """
    Запускает Tesseract на уже подготовленном изображении.

    Конфигурация:
    - --psm 7: одна строка текста (под номер отлично подходит)
    - --oem 3: LSTM
    - whitelist: только допустимые для номера символы
    """
    pil_img = Image.fromarray(image)

    whitelist = "ABEKMHOPCTYXабекмнорстухАВЕКМНОРСТУХ0123456789"
    config = (
        "--oem 3 "
        "--psm 7 "
        f"-c tessedit_char_whitelist={whitelist}"
    )

    raw = pytesseract.image_to_string(pil_img, lang="rus+eng", config=config)

    return raw.replace("\n", " ").replace("\x0c", " ").strip()
