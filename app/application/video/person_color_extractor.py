from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class RegionColor:
    """
    Цвет одной части человека (верх или низ) в HSV.

    h: Hue в градусах [0.0; 360.0]
    s: Saturation [0.0; 1.0]
    v: Value (яркость) [0.0; 1.0]
    pixel_count: количество пикселей, использованных при оценке
    is_chromatic: True, если область в основном цветная (а не белая/серая/чёрная)
    """
    h: float
    s: float
    v: float
    pixel_count: int
    is_chromatic: bool

    def as_tuple(self) -> tuple[float, float, float]:
        return self.h, self.s, self.v


@dataclass(frozen=True)
class PersonColorProfile:
    """
    Цветовой профиль человека: верхняя и нижняя часть одежды.
    Если какой-то части оценка невозможна (слишком мало валидных пикселей),
    соответствующее поле будет None.
    """
    upper_color: Optional[RegionColor]
    lower_color: Optional[RegionColor]


def extract_person_color_profile(
    image: Image.Image | np.ndarray,
    min_valid_fraction: float = 0.03,
) -> PersonColorProfile:
    """
    Оценка цветов верхней и нижней части одежды по кропу человека.

    Предполагаем, что YOLO-кроп более-менее плотно обрезает человека по контуру.

    Алгоритм (по шагам):

      1. Приводим вход к BGR np.ndarray.
      2. Немного нормализуем размер (по площади).
      3. Делаем "центральный" кроп по ширине (отрезаем левые/правые края с фоном).
      4. Делим по высоте на две зоны:
         - upper: примерно 15%..55% высоты (торс / куртка / футболка)
         - lower: примерно 55%..100% (штаны / юбка)
      5. Для каждой зоны считаем HSV-профиль через общий вспомогательный код:
         - отбрасываем очень тёмные пиксели (теневые),
         - решаем, хроматическая зона или ахроматическая,
         - выдаём RegionColor или None, если данных мало.
    """
    bgr_full = _to_bgr(image)

    # Немного нормализуем размер, чтобы сгладить шум, не теряя деталей.
    bgr_full = _resize_reasonable(bgr_full, target_area=140 * 80)

    # Центр по ширине (уменьшаем влияние фона по бокам).
    bgr_center = _central_strip(bgr_full, x_margin_ratio=0.15)

    upper_bgr, lower_bgr = _split_upper_lower(bgr_center)

    upper_color = _compute_region_color(upper_bgr, min_valid_fraction)
    lower_color = _compute_region_color(lower_bgr, min_valid_fraction)

    return PersonColorProfile(
        upper_color=upper_color,
        lower_color=lower_color,
    )


# ==========================
# Вспомогательные функции
# ==========================


def _to_bgr(image: Image.Image | np.ndarray) -> np.ndarray:
    """
    Приводит вход к BGR np.ndarray (uint8).
    """
    if isinstance(image, Image.Image):
        rgb = np.array(image.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

    if not isinstance(image, np.ndarray):
        raise TypeError("image must be PIL.Image or np.ndarray")

    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    if image.ndim == 3 and image.shape[2] == 3:
        return image

    raise ValueError("Unsupported image format for _to_bgr")


def _resize_reasonable(bgr: np.ndarray, target_area: int) -> np.ndarray:
    """
    Масштабирует изображение так, чтобы площадь была около target_area.
    Сохраняет соотношение сторон.
    """
    h, w = bgr.shape[:2]
    area = h * w
    if area == 0:
        return bgr

    scale = (target_area / float(area)) ** 0.5
    if 0.7 < scale < 1.4:
        return bgr

    new_w = max(int(w * scale), 1)
    new_h = max(int(h * scale), 1)
    return cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _central_strip(bgr: np.ndarray, x_margin_ratio: float = 0.15) -> np.ndarray:
    """
    Берём центральную вертикальную полосу, отрезая края по ширине.
    Обычно по бокам много фона, в центре – одежда.
    """
    h, w = bgr.shape[:2]
    if w < 10:
        return bgr

    margin = int(w * x_margin_ratio)
    x1 = margin
    x2 = w - margin
    if x2 <= x1:
        return bgr

    return bgr[:, x1:x2].copy()


def _split_upper_lower(bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Делит кроп по высоте на две части:

      - верх: примерно 15%..55% высоты (чуть ниже головы → до пояса)
      - низ:  55%..100% (штаны/юбка/ноги)

    Это грубая, но на практике достаточно рабочая эвристика.
    """
    h, w = bgr.shape[:2]
    if h < 10:
        return bgr.copy(), bgr.copy()

    y_upper_top = int(h * 0.15)
    y_upper_bottom = int(h * 0.55)
    y_lower_top = y_upper_bottom
    y_lower_bottom = h

    # страхуемся от вырожденных случаев
    if y_upper_bottom <= y_upper_top:
        y_upper_top = 0
        y_upper_bottom = max(h // 2, 1)

    if y_lower_bottom <= y_lower_top:
        y_lower_top = y_upper_bottom
        y_lower_bottom = h

    upper = bgr[y_upper_top:y_upper_bottom, :].copy()
    lower = bgr[y_lower_top:y_lower_bottom, :].copy()

    return upper, lower


def _compute_region_color(
    bgr_region: np.ndarray,
    min_valid_fraction: float,
) -> Optional[RegionColor]:
    """
    Считает цветовой профиль для одной зоны (верх или низ).
    Логика такая же, как для машины, только без
    специфики "кузов/фон".
    """
    if bgr_region.size == 0:
        return None

    hsv = cv2.cvtColor(bgr_region, cv2.COLOR_BGR2HSV)

    h_cv = hsv[:, :, 0].astype(np.float32)  # [0; 179]
    s_cv = hsv[:, :, 1].astype(np.float32)  # [0; 255]
    v_cv = hsv[:, :, 2].astype(np.float32)  # [0; 255]

    h_deg = h_cv * 2.0
    s_norm = s_cv / 255.0
    v_norm = v_cv / 255.0

    # Отбрасываем совсем тёмное (тени, шум):
    valid_mask = v_norm > 0.1
    if not np.any(valid_mask):
        return None

    total_pixels = h_deg.size
    valid_count = int(valid_mask.sum())
    if valid_count / float(total_pixels) < min_valid_fraction:
        return None

    # Общая оценка "цветности" зоны по медиане насыщенности.
    s_all = s_norm[valid_mask]
    median_s_all = float(np.median(s_all))

    # Кандидаты в хроматические пиксели: достаточно насыщенные
    chroma_mask = valid_mask & (s_norm > 0.35)
    chroma_count = int(chroma_mask.sum())
    chroma_fraction = chroma_count / float(total_pixels)

    # Зону считаем хроматической, только если:
    #   - есть заметное количество насыщенных пикселей,
    #   - и средняя насыщенность не маленькая.
    if chroma_count > 0 and chroma_fraction >= 0.10 and median_s_all > 0.25:
        return _compute_chromatic_profile(h_deg, s_norm, v_norm, chroma_mask)

    # Иначе — ахроматическая зона (white/gray/black).
    return _compute_achromatic_profile(h_deg, s_norm, v_norm, valid_mask)


def _compute_chromatic_profile(
    h_deg: np.ndarray,
    s_norm: np.ndarray,
    v_norm: np.ndarray,
    chroma_mask: np.ndarray,
) -> RegionColor:
    """
    Оценка цвета для хроматической области (яркая одежда).
    """
    h_vals = h_deg[chroma_mask]
    s_vals = s_norm[chroma_mask]
    v_vals = v_norm[chroma_mask]

    if h_vals.size == 0:
        # fallback — считаем как ахроматическую область
        valid_mask = v_norm > 0.1
        return _compute_achromatic_profile(h_deg, s_norm, v_norm, valid_mask)

    # Гистограмма hue
    bin_width = 5.0
    bins = int(360.0 / bin_width)
    hist, bin_edges = np.histogram(h_vals, bins=bins, range=(0.0, 360.0))

    max_bin_idx = int(hist.argmax())
    bin_center = (bin_edges[max_bin_idx] + bin_edges[max_bin_idx + 1]) / 2.0

    # Окно вокруг доминирующего bin
    window_half_width = 15.0

    lower = (bin_center - window_half_width) % 360.0
    upper = (bin_center + window_half_width) % 360.0

    if lower <= upper:
        window_mask = (h_vals >= lower) & (h_vals <= upper)
    else:
        window_mask = (h_vals >= lower) | (h_vals <= upper)

    if not np.any(window_mask):
        window_mask = np.ones_like(h_vals, dtype=bool)

    h_window = h_vals[window_mask]
    s_window = s_vals[window_mask]
    v_window = v_vals[window_mask]

    # Окружное среднее по hue
    h_rad = np.deg2rad(h_window)
    mean_sin = float(np.mean(np.sin(h_rad)))
    mean_cos = float(np.mean(np.cos(h_rad)))
    mean_angle = np.arctan2(mean_sin, mean_cos)
    mean_h_deg = float(np.rad2deg(mean_angle)) % 360.0

    median_s = float(np.median(s_window))
    median_v = float(np.median(v_window))
    pixel_count = int(h_window.size)

    return RegionColor(
        h=mean_h_deg,
        s=median_s,
        v=median_v,
        pixel_count=pixel_count,
        is_chromatic=True,
    )


def _compute_achromatic_profile(
    h_deg: np.ndarray,
    s_norm: np.ndarray,
    v_norm: np.ndarray,
    valid_mask: np.ndarray,
) -> RegionColor:
    """
    Оценка для ахроматической области (white/gray/black).
    """
    h_vals = h_deg[valid_mask]
    s_vals = s_norm[valid_mask]
    v_vals = v_norm[valid_mask]

    if h_vals.size == 0:
        return RegionColor(
            h=0.0,
            s=0.0,
            v=0.0,
            pixel_count=0,
            is_chromatic=False,
        )

    median_h = float(np.median(h_vals)) % 360.0
    median_s = float(np.median(s_vals))
    median_v = float(np.median(v_vals))
    pixel_count = int(h_vals.size)

    return RegionColor(
        h=median_h,
        s=median_s,
        v=median_v,
        pixel_count=pixel_count,
        is_chromatic=False,
    )
