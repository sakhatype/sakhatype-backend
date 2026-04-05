"""Русские сообщения для ошибок валидации (422)."""

from typing import Any, List

_FIELD_LABELS = {
    "username": "Имя пользователя",
    "password": "Пароль",
    "email": "Email",
    "current_password": "Текущий пароль",
    "new_password": "Новый пароль",
    "wpm": "Скорость (WPM)",
    "raw_wpm": "Сырая скорость",
    "accuracy": "Точность",
    "mode": "Режим",
    "mode_value": "Значение режима",
    "language": "Язык",
    "difficulty": "Сложность",
    "chars_correct": "Верных символов",
    "chars_incorrect": "Ошибок",
    "chars_extra": "Лишних символов",
    "chars_missed": "Пропущенных символов",
    "count": "Количество",
}


def _field_label(loc: tuple[Any, ...]) -> str:
    for part in reversed(loc):
        if isinstance(part, str) and part not in (
            "body",
            "query",
            "path",
            "header",
            "cookie",
        ):
            return _FIELD_LABELS.get(part, part.replace("_", " "))
    return "Поле"


def _strip_value_error_prefix(msg: str) -> str:
    if msg.startswith("Value error, "):
        return msg[13:].strip()
    return msg


def translate_validation_error_item(err: dict[str, Any]) -> str:
    t = str(err.get("type") or "")
    ctx = err.get("ctx") or {}
    loc = err.get("loc") or ()
    label = _field_label(loc)
    msg = str(err.get("msg") or "")

    if t == "missing":
        return f"{label}: обязательное поле"
    if t == "string_too_short":
        m = ctx.get("min_length", "?")
        return f"{label}: минимум {m} символов"
    if t == "string_too_long":
        m = ctx.get("max_length", "?")
        return f"{label}: максимум {m} символов"
    if t == "string_type":
        return f"{label}: укажите текст"
    if t in ("int_parsing", "float_parsing"):
        return f"{label}: укажите число"
    if t == "bool_parsing":
        return f"{label}: неверный формат"
    if t == "greater_than_equal":
        ge = ctx.get("ge")
        if ge is not None:
            return f"{label}: не меньше {ge}"
        return f"{label}: некорректное значение"
    if t == "less_than_equal":
        le = ctx.get("le")
        if le is not None:
            return f"{label}: не больше {le}"
        return f"{label}: некорректное значение"
    if t == "greater_than":
        gt = ctx.get("gt")
        if gt is not None:
            return f"{label}: должно быть больше {gt}"
        return f"{label}: некорректное значение"
    if t == "less_than":
        lt = ctx.get("lt")
        if lt is not None:
            return f"{label}: должно быть меньше {lt}"
        return f"{label}: некорректное значение"
    if t.startswith("value_error"):
        inner = _strip_value_error_prefix(msg)
        return inner if inner else "Некорректное значение"
    if t == "model_attributes_type":
        return "Некорректный формат данных"
    if t == "dict_type":
        return "Ожидается объект"
    if t == "list_type":
        return "Ожидается список"

    cleaned = _strip_value_error_prefix(msg)
    if cleaned and cleaned != msg:
        return f"{label}: {cleaned}" if label != "Поле" else cleaned
    if cleaned:
        return cleaned
    return "Некорректные данные"


def format_validation_errors_detail(errors: List[dict[str, Any]]) -> str:
    parts = [translate_validation_error_item(e) for e in errors]
    return "; ".join(parts) if parts else "Некорректные данные"
