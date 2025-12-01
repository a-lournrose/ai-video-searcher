from __future__ import annotations

from typing import Dict

# Поддерживаемые базовые цвета
_SUPPORTED_COLORS = {
    "red",
    "green",
    "blue",
    "yellow",
    "orange",
    "purple",
    "brown",
    "white",
    "gray",
    "black",
}

# Референсные Hue (в градусах, [0; 360))
_HUE_REF: Dict[str, float] = {
    "red": 0.0,
    "orange": 30.0,
    "yellow": 55.0,
    "green": 120.0,
    "blue": 220.0,
    "purple": 275.0,
    # Для brown используем Hue рядом с оранжевым
    "brown": 25.0,
}


def compute_color_score(query_color: str, h: float, s: float, v: float) -> float:
    """
    Вычисляет оценку соответствия цвета объекта запрошенному базовому цвету.

    :param query_color: базовый цвет, один из:
                        red, green, blue, yellow, orange, purple, brown,
                        white, gray, black (регистр не важен)
    :param h: Hue в градусах [0.0; 360.0]
    :param s: Saturation [0.0; 1.0]
    :param v: Value (яркость) [0.0; 1.0]
    :return: score в диапазоне [0.0; 1.0]
    """
    color = query_color.strip().lower()
    if color not in _SUPPORTED_COLORS:
        # Явно неизвестный цвет — возвращаем 0.0
        return 0.0

    # Нормализуем/ограничиваем входные значения
    h = _clamp(h, 0.0, 360.0)
    s = _clamp(s, 0.0, 1.0)
    v = _clamp(v, 0.0, 1.0)

    if color in ("white", "gray", "black"):
        return _score_achromatic(color, s, v)

    # Хроматические цвета (с учётом Hue)
    return _score_chromatic(color, h, s, v)


# ==========================
# Вспомогательные функции
# ==========================


def _clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Ограничивает значение в пределах [min_value; max_value].
    """
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def _circular_hue_distance(h: float, ref_h: float) -> float:
    """
    Вычисляет круговое расстояние по Hue в градусах.
    Результат в диапазоне [0; 180].
    """
    d_raw = abs(h - ref_h)
    return min(d_raw, 360.0 - d_raw)


def _hue_score(d_h: float) -> float:
    """
    Преобразует расстояние по Hue в оценку [0.0; 1.0].

    Требования:
      - dH <= 10° → близко к 1.0
      - dH ~ 20° → около 0.5
      - dH >= 40° → близко к 0.0

    Реализация: простая линейная аппроксимация.
    """
    if d_h >= 40.0:
        return 0.0
    # Линейное затухание от 1.0 (0°) до 0.0 (40°)
    return 1.0 - (d_h / 40.0)


def _chromatic_s_score(s: float) -> float:
    """
    Оценка насыщенности для хроматических цветов.

    Для реальных машин позволяем небольшой запас:
      - s <= 0.05  → почти нет цвета → score ~ 0
      - 0.05 < s < 0.5 → плавный рост до 1.0
      - s >= 0.5  → считаем насыщенности достаточно → score = 1.0
    """
    if s <= 0.05:
        return 0.0
    if s >= 0.5:
        return 1.0
    return (s - 0.05) / (0.5 - 0.05)


def _chromatic_v_score(v: float) -> float:
    """
    Оценка яркости для хроматических цветов.

    Для машин тени и пересветы — норма, поэтому V не должен жёстко
    убивать цвет, а лишь слегка штрафовать крайние значения:

      - v <= 0.1  → очень тёмно, но цвет может быть виден → score ~ 0.4
      - v ~ 0.4–0.8 → оптимальная зона → score ~ 1.0
      - v >= 0.95 → очень светло/пересвет → score ~ 0.5

    Используем кусочно-линейную кривую в диапазоне [0.4; 1.0].
    """
    # Нижний хвост: 0.1 и ниже → 0.4
    if v <= 0.1:
        return 0.4

    # Основная рабочая зона: 0.1–0.4 → растём до 1.0
    if v <= 0.4:
        # 0.1 → 0.4,  0.4 → 1.0
        return 0.4 + (v - 0.1) * (1.0 - 0.4) / (0.4 - 0.1)

    # Нормальная яркость до легких пересветов: 0.4–0.8 → 1.0
    if v <= 0.8:
        return 1.0

    # Верхний хвост: 0.8–0.95 → падаем до 0.5
    if v <= 0.95:
        # 0.8 → 1.0,  0.95 → 0.5
        return 1.0 - (v - 0.8) * (1.0 - 0.5) / (0.95 - 0.8)

    # Совсем пересвет: держим на уровне 0.5
    return 0.5


def _brown_v_score(v: float) -> float:
    """
    Оценка яркости для 'brown'.

    Требование:
      - максимум при v ~ 0.3–0.6
      - при очень низком v → ближе к black
      - при очень высоком v → ближе к orange/yellow

    Используем треугольную функцию:
      - 0 при v <= 0.1 и v >= 0.8
      - максимум 1.0 при v ≈ 0.4
    """
    if v <= 0.1 or v >= 0.8:
        return 0.0
    if v <= 0.4:
        # от 0.1 до 0.4 растём от 0 до 1
        return (v - 0.1) / (0.4 - 0.1)
    # от 0.4 до 0.8 падаем от 1 до 0
    return (0.8 - v) / (0.8 - 0.4)


def _brown_s_score(s: float) -> float:
    """
    Оценка насыщенности для 'brown'.

    Идея:
      - при s < 0.3 → слишком блеклый, скорее gray → score ~ 0
      - при s ≥ 0.8 → считаем, что насыщенности достаточно → score ~ 1
      - линейный рост между 0.3 и 0.8
    """
    if s <= 0.3:
        return 0.0
    if s >= 0.8:
        return 1.0
    return (s - 0.3) / (0.8 - 0.3)


def _score_chromatic(color: str, h: float, s: float, v: float) -> float:
    """
    Оценка для хроматических цветов (red/green/blue/yellow/orange/purple/brown).

    Для brown дополнительно учитываем специфичные правила по S/V,
    для остальных — более мягкие s/v, чтобы не ломаться на тенях.
    """
    ref_h = _HUE_REF[color]
    d_h = _circular_hue_distance(h, ref_h)
    hue_component = _hue_score(d_h)

    if color == "brown":
        # Для brown по-прежнему строгие ограничения по S/V,
        # т.к. это сильно зависящий от яркости цвет.
        s_component = _brown_s_score(s)
        v_component = _brown_v_score(v)
        # Для brown оставим более жёсткую комбинацию
        score = hue_component * s_component * v_component
    else:
        s_component = _chromatic_s_score(s)
        v_component = _chromatic_v_score(v)

        # Для машин тени/освещение сильно гуляют,
        # поэтому вместо жёсткого произведения берём:
        #   hue * среднее(S, V)
        # так цвет не развалится только из-за V.
        sv_component = (s_component + v_component) / 2.0
        score = hue_component * sv_component

    return _clamp(score, 0.0, 1.0)


def _white_score(s: float, v: float) -> float:
    """
    Оценка соответствия 'white'.

    Идея:
      - насыщенность низкая: s <= 0.1 идеально, s >= 0.4 — почти не белый
      - яркость достаточно высокая: v <= 0.4 точно не белый,
        v >= 0.7 уже хорошо (0.7–0.9 — нормальный диапазон для белой машины в жизни)
    """

    # Низкая насыщенность:
    #   s <= 0.1  → s_component = 1.0
    #   s >= 0.4  → s_component = 0.0
    #   линейное падение между 0.1 и 0.4
    if s <= 0.1:
        s_component = 1.0
    elif s >= 0.4:
        s_component = 0.0
    else:
        s_component = 1.0 - (s - 0.1) / (0.4 - 0.1)

    # Высокая яркость, но с более мягкими порогами:
    #   v <= 0.4 → v_component = 0.0
    #   v >= 0.7 → v_component = 1.0
    #   линейный рост между 0.4 и 0.7
    if v <= 0.4:
        v_component = 0.0
    elif v >= 0.7:
        v_component = 1.0
    else:
        v_component = (v - 0.4) / (0.7 - 0.4)

    score = s_component * v_component
    return _clamp(score, 0.0, 1.0)


def _gray_score(s: float, v: float) -> float:
    """
    Оценка соответствия 'gray'.

    Требования:
      - s низкая
      - v средняя

    Поведение:
      - s <= 0.3 → хорошо
      - при высокой s → это уже цветной объект
      - v около 0.5 → максимум
      - при v очень низком → ближе к black
      - при v очень высоком → ближе к white
    """
    # Низкая насыщенность: s=0 → 1.0, s>=0.4 → 0.0
    if s <= 0.0:
        s_component = 1.0
    elif s >= 0.4:
        s_component = 0.0
    else:
        s_component = 1.0 - (s / 0.4)

    # Яркость: треугольная функция вокруг v≈0.5
    # v<=0.2 → 0,  v≈0.5 → 1, v>=0.9 → 0
    if v <= 0.2 or v >= 0.9:
        v_component = 0.0
    elif v <= 0.5:
        v_component = (v - 0.2) / (0.5 - 0.2)
    else:
        v_component = (0.9 - v) / (0.9 - 0.5)

    score = s_component * v_component
    return _clamp(score, 0.0, 1.0)


def _black_score(v: float) -> float:
    """
    Оценка соответствия 'black'.

    Идея:
      - v очень низкое → почти идеальный чёрный
      - v высокое → точно не чёрный
      - между ними плавное падение

      v <= 0.12 → score = 1.0
      v >= 0.50 → score = 0.0
      0.12 < v < 0.50 → линейное уменьшение от 1.0 до 0.0
    """
    if v <= 0.12:
        return 1.0
    if v >= 0.50:
        return 0.0

    return 1.0 - (v - 0.12) / (0.50 - 0.12)


def _score_achromatic(color: str, s: float, v: float) -> float:
    """
    Оценка для ахроматических цветов (white/gray/black).
    """
    if color == "white":
        return _white_score(s, v)
    if color == "gray":
        return _gray_score(s, v)
    if color == "black":
        return _black_score(v)

    # На всякий случай
    return 0.0
