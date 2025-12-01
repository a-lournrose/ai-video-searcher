from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple
import re


class QueryObjectType(str, Enum):
    PERSON = "PERSON"
    TRANSPORT = "TRANSPORT"


@dataclass(frozen=True)
class ParsedQuery:
    """
    Результат разбора пользовательского текстового запроса.
    Все поля, кроме cleaned_text, могут быть None.
    """
    type: Optional[QueryObjectType]
    color: Optional[str]
    upper_color: Optional[str]
    lower_color: Optional[str]
    plate: Optional[str]
    cleaned_text: str


# Список ключевых слов для определения типа
_PERSON_KEYWORDS = [
    "person",
    "people",
    "human",
    "man",
    "woman",
    "boy",
    "girl",
    # "люди",
    "человек",
    "человека",
    "мужчина",
    "женщина",
    "парень",
    "девушка",
    "пешеход",
]

_TRANSPORT_KEYWORDS = [
    "car",
    "cars",
    "auto",
    "vehicle",
    "truck",
    "bus",
    "машина",
    "авто",
    "тачка",
    "грузовик",
    "автобус",
    "легковая",
    "фура",
    "микроавтобус",
    "транспорт",
]

# Верхняя и нижняя одежда (для привязки цвета)
_UPPER_CLOTHES_KEYWORDS = [
    "куртк",
    "футболк",
    "кофт",
    "пиджак",
    "пальт",
    "жилет",
    "худи",
    "толстовк",
    "свитер",
    "верх",
]

_LOWER_CLOTHES_KEYWORDS = [
    "штон",
    "штам",
    "штан",
    "штаны",
    "джинс",
    "брюк",
    "юбк",
    "шорт",
    "низ",
]

# Нормализация цветов: базовое название -> список подстрок/основ
_COLOR_PATTERNS: Dict[str, List[str]] = {
    "black": ["черн", "black", "чёрн"],
    "white": ["бел", "white"],
    "gray": ["сер", "grey", "gray"],
    "red": ["красн", "red", "бордов"],
    "orange": ["оранжев", "orange"],
    "yellow": ["желт", "yellow"],
    "green": ["зелен", "зелён", "green"],
    "blue": ["син", "голуб", "blue"],
    "brown": ["коричнев", "brown"],
    "purple": ["фиолет", "purple", "пурпур"],
    "pink": ["розов", "pink"],
}


# Регулярка для российского номера (упрощённо), допускаем пробелы
# Примеры: А123ВС77, A123BC 77, а123вс777
_PLATE_REGEX = re.compile(
    r"\b([A-ZА-Я])[ -]?(\d{3})[ -]?([A-ZА-Я]{2})[ -]?(\d{2,3})\b",
    re.IGNORECASE,
)


def parse_query(text: str) -> ParsedQuery:
    """
    Основная функция разбора текстового запроса.
    Возвращает ParsedQuery с извлечёнными полями.
    """
    normalized_text = _normalize_text(text)

    plate, text_without_plate = _extract_plate(normalized_text)
    obj_type = _detect_type(normalized_text)
    colors, tokens = _detect_colors_with_tokens(normalized_text)

    upper_color, lower_color, generic_color = _split_colors_by_clothes(
        colors,
        tokens,
        obj_type,
    )

    # Если явно не разделили по верх/низ и есть единственный цвет — пишем в color
    color: Optional[str]
    if upper_color or lower_color:
        color = None
    else:
        color = generic_color

    cleaned_text = text_without_plate.strip()

    return ParsedQuery(
        type=obj_type,
        color=color,
        upper_color=upper_color,
        lower_color=lower_color,
        plate=plate,
        cleaned_text=cleaned_text,
    )


def _normalize_text(text: str) -> str:
    """
    Простейшая нормализация: приводим к нижнему регистру,
    заменяем повторяющиеся пробелы одним.
    """
    lowered = text.strip().lower()
    # убираем лишние пробелы
    return re.sub(r"\s+", " ", lowered)


def _extract_plate(text: str) -> Tuple[Optional[str], str]:
    """
    Ищет номер автомобиля (ГРЗ) по упрощённому шаблону.
    Возвращает нормализованный номер и текст без номера.
    Если номера нет — возвращает (None, исходный текст).
    """
    match = _PLATE_REGEX.search(text)
    if not match:
        return None, text

    letter1, digits, letters2, region = match.groups()

    # Нормализуем: заглавные латинские/кириллические, без пробелов
    normalized_plate = (
        f"{letter1}{digits}{letters2}{region}"
        .upper()
        .replace("Ё", "Е")
    )

    # Вырезаем найденный номер из текста
    start, end = match.span()
    text_without_plate = (text[:start] + text[end:]).strip()

    return normalized_plate, text_without_plate


def _detect_type(text: str) -> Optional[QueryObjectType]:
    """
    Определяет тип объекта (PERSON или TRANSPORT) по ключевым словам.
    Если ничего не найдено или совпадения равны — возвращает None.
    """
    person_score = _count_keyword_hits(text, _PERSON_KEYWORDS)
    transport_score = _count_keyword_hits(text, _TRANSPORT_KEYWORDS)

    if person_score == 0 and transport_score == 0:
        return None

    if person_score > transport_score:
        return QueryObjectType.PERSON
    if transport_score > person_score:
        return QueryObjectType.TRANSPORT

    # неоднозначный случай
    return None


def _count_keyword_hits(text: str, keywords: List[str]) -> int:
    """
    Считает количество вхождений ключевых слов как подстрок.
    Работает достаточно грубо, но для наших целей достаточно.
    """
    score = 0
    for keyword in keywords:
        if keyword in text:
            score += 1
    return score


def _detect_colors_with_tokens(text: str) -> Tuple[List[Tuple[int, str]], List[str]]:
    """
    Возвращает:
    - список найденных цветов в виде (индекс_токена, нормализованный_цвет)
    - список токенов (строк)
    """
    tokens = text.split()
    found: List[Tuple[int, str]] = []

    for idx, token in enumerate(tokens):
        normalized_token = token.strip(",.!?;:")
        color = _match_color(normalized_token)
        if color is not None:
            found.append((idx, color))

    return found, tokens


def _match_color(token: str) -> Optional[str]:
    """
    Возвращает базовый цвет по токену, если он похож на один из известных.
    Проверка по подстроке-основе ('красн', 'син', 'blue' и т.д.).
    """
    for color_name, patterns in _COLOR_PATTERNS.items():
        for pattern in patterns:
            if pattern in token:
                return color_name
    return None


def _split_colors_by_clothes(
    colors: List[Tuple[int, str]],
    tokens: List[str],
    obj_type: Optional[QueryObjectType],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Пытается разделить цвета на верх и низ для PERSON.
    Если тип не PERSON или нет достаточного контекста — возвращает generic_color.
    """
    if obj_type != QueryObjectType.PERSON or not colors:
        # для транспорта / неизвестного типа просто берём первый цвет как общий
        generic_color = colors[0][1] if colors else None
        return None, None, generic_color

    upper_color: Optional[str] = None
    lower_color: Optional[str] = None

    # Для привязки цвета к одежде используем ближайший цвет к ключевому слову
    for idx, token in enumerate(tokens):
        token_clean = token.strip(",.!?;:")

        if _token_matches_any(token_clean, _UPPER_CLOTHES_KEYWORDS):
            nearest_color = _closest_color_for_index(colors, idx)
            if nearest_color and upper_color is None:
                upper_color = nearest_color

        if _token_matches_any(token_clean, _LOWER_CLOTHES_KEYWORDS):
            nearest_color = _closest_color_for_index(colors, idx)
            if nearest_color and lower_color is None:
                lower_color = nearest_color

    # Если верх/низ не определились, но есть хотя бы один цвет — считаем его общим
    if upper_color is None and lower_color is None and colors:
        generic_color = colors[0][1]
    else:
        generic_color = None

    return upper_color, lower_color, generic_color


def _token_matches_any(token: str, patterns: List[str]) -> bool:
    """
    Проверяет, содержит ли токен какую-либо из указанных подстрок.
    Используем подстроки типа 'куртк', 'джинс', чтобы немного сгладить падежи.
    """
    for pattern in patterns:
        if pattern in token:
            return True
    return False


def _closest_color_for_index(
    colors: List[Tuple[int, str]],
    index: int,
    max_distance: int = 3,
) -> Optional[str]:
    """
    Находит цвет, ближайший по позиции к указанному индексу токена.
    max_distance ограничивает количество токенов до цвета.
    """
    best: Optional[Tuple[int, str]] = None
    best_distance = max_distance + 1

    for color_idx, color_name in colors:
        distance = abs(color_idx - index)
        if distance <= max_distance and distance < best_distance:
            best = (color_idx, color_name)
            best_distance = distance

    if best is None:
        return None

    return best[1]