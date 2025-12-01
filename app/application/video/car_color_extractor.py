from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class CarColorProfile:
    """
    Репрезентативный цвет автомобиля в HSV.

    h: Hue в градусах [0.0; 360.0]
    s: Saturation [0.0; 1.0]
    v: Value (яркость) [0.0; 1.0]
    pixel_count: количество пикселей, использованных при оценке
    is_chromatic: True, если обнаружен доминирующий "цветной" тон (а не серый/белый/чёрный)
    """
    h: float
    s: float
    v: float
    pixel_count: int
    is_chromatic: bool

    def as_tuple(self) -> tuple[float, float, float]:
        return self.h, self.s, self.v

def _focus_on_car_body(bgr: np.ndarray) -> np.ndarray:
    """
    Грубое выделение зоны кузова по положению в кадре.

    Идея:
      - игнорируем крайние области (часто там фон, номера, дорога);
      - работаем с центральной "полосой", где обычно основная масса кузова.

    Это не семантическая сегментация, но сильно снижает влияние фона.
    """
    h, w = bgr.shape[:2]
    if h < 10 or w < 10:
        return bgr

    y1 = int(h * 0.15)
    y2 = int(h * 0.90)
    x1 = int(w * 0.10)
    x2 = int(w * 0.90)

    # на всякий случай страхуемся от пустых диапазонов
    if y2 <= y1 or x2 <= x1:
        return bgr

    return bgr[y1:y2, x1:x2].copy()

def extract_car_hsv_profile(
    image: Image.Image | np.ndarray,
    min_valid_fraction: float = 0.05,
) -> Optional[CarColorProfile]:
    """
    Оценка цвета автомобиля по кропу.

    Алгоритм (MVP, но уже достаточно разумный):
      1. Приводим вход к BGR np.ndarray.
      2. Уменьшаем/увеличиваем кроп до разумного размера (по площади), чтобы
         сгладить шум и не перегружать CPU.
      3. Переводим в HSV.
      4. Выкидываем совсем тёмные пиксели (теневые области).
      5. Смотрим, достаточно ли "цветных" пикселей (s > 0.2).
         - Если да → считаем машину хроматической:
             * делаем гистограмму hue, берём доминирующий диапазон,
             * по пикселям этого диапазона считаем окружное среднее hue и
               медианы s/v.
         - Если нет → считаем машину ахроматической (white/gray/black):
             * используем все "валидные" пиксели,
             * считаем медианы s/v,
             * hue берём медианный (compute_color_score для white/gray/black
               всё равно почти не использует hue).
      6. Если валидных пикселей мало (< min_valid_fraction), возвращаем None.

    :param image: кроп автомобиля (PIL.Image или BGR/GRAY np.ndarray)
    :param min_valid_fraction: минимальная доля валидных пикселей (0..1),
                               чтобы считать оценку осмысленной
    :return: CarColorProfile или None, если данных недостаточно
    """
    bgr = _to_bgr(image)

    # Сначала грубо отсекаем фон и небо, фокусируемся на кузове
    bgr = _focus_on_car_body(bgr)

    # Нормализация размера, чтобы кроп не был ни слишком мелким, ни огромным
    bgr = _resize_reasonable(bgr, target_area=160 * 160)

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    h_cv = hsv[:, :, 0].astype(np.float32)  # [0; 179]
    s_cv = hsv[:, :, 1].astype(np.float32)  # [0; 255]
    v_cv = hsv[:, :, 2].astype(np.float32)  # [0; 255]

    # Переводим в "нормальный" HSV формат:
    h_deg = h_cv * 2.0                  # [0; 360]
    s_norm = s_cv / 255.0               # [0; 1]
    v_norm = v_cv / 255.0               # [0; 1]

    # Маска валидных пикселей (не совсем чёрный мусор)
    valid_mask = v_norm > 0.1
    if not np.any(valid_mask):
        return None

    total_pixels = h_deg.size
    valid_count = int(valid_mask.sum())
    if valid_count / float(total_pixels) < min_valid_fraction:
        return None

    # Хроматические пиксели: достаточно насыщенный цвет
    s_all = s_norm[valid_mask]
    median_s_all = float(np.median(s_all))

    # Кандидаты в хроматические пиксели: достаточно насыщенные
    chroma_mask = valid_mask & (s_norm > 0.35)
    chroma_count = int(chroma_mask.sum())
    chroma_fraction = chroma_count / float(total_pixels)

    # Машину считаем хроматической, только если:
    #   - много реально насыщенных пикселей (>= 10%)
    #   - и в среднем насыщенность не маленькая (median_s > 0.25)
    if chroma_count > 0 and chroma_fraction >= 0.10 and median_s_all > 0.25:
        return _compute_chromatic_profile(h_deg, s_norm, v_norm, chroma_mask)

    # Иначе — ахроматический объект (white/gray/black)
    return _compute_achromatic_profile(h_deg, s_norm, v_norm, valid_mask)


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
        # GRAY → BGR
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    if image.ndim == 3 and image.shape[2] == 3:
        # Предполагаем, что уже BGR
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

    # Если сильно меньше — увеличиваем, если сильно больше — уменьшаем.
    scale = (target_area / float(area)) ** 0.5

    # Не меняем, если масштаб близок к 1
    if 0.7 < scale < 1.4:
        return bgr

    new_w = max(int(w * scale), 1)
    new_h = max(int(h * scale), 1)
    return cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _compute_chromatic_profile(
    h_deg: np.ndarray,
    s_norm: np.ndarray,
    v_norm: np.ndarray,
    chroma_mask: np.ndarray,
) -> CarColorProfile:
    """
    Оценка цвета для хроматической машины.

    Шаги:
      1. Берём только хроматические пиксели.
      2. Строим гистограмму hue (0..360) с шагом 5°.
      3. Выбираем bin с максимальным количеством пикселей — доминирующий тон.
      4. Оставляем пиксели в окне +/- 15° вокруг доминирующего bin.
      5. Считаем окружное среднее для hue и медианы для s/v.
    """
    h_vals = h_deg[chroma_mask]
    s_vals = s_norm[chroma_mask]
    v_vals = v_norm[chroma_mask]

    if h_vals.size == 0:
        # fallback на ахроматический метод
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

    # Учитываем цикличность hue
    lower = (bin_center - window_half_width) % 360.0
    upper = (bin_center + window_half_width) % 360.0

    if lower <= upper:
        window_mask = (h_vals >= lower) & (h_vals <= upper)
    else:
        # Окно "переломилось" через 0°
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

    # Медианы по s и v более устойчивы к выбросам
    median_s = float(np.median(s_window))
    median_v = float(np.median(v_window))

    pixel_count = int(h_window.size)
    return CarColorProfile(
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
) -> CarColorProfile:
    """
    Оценка для ахроматической машины (white/gray/black).

    Используем все валидные пиксели:
      - медиана по hue, s, v
      - hue тут не особо важен (compute_color_score для white/gray/black
        в основном смотрит на s/v).
    """
    h_vals = h_deg[valid_mask]
    s_vals = s_norm[valid_mask]
    v_vals = v_norm[valid_mask]

    if h_vals.size == 0:
        # В теории не должно случиться, но на всякий случай.
        return CarColorProfile(
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

    return CarColorProfile(
        h=median_h,
        s=median_s,
        v=median_v,
        pixel_count=pixel_count,
        is_chromatic=False,
    )