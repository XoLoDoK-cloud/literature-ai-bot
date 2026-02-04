# inline_keyboards.py

from typing import List, Tuple

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from authors import get_groups, get_authors_by_group


# Настройка: сколько кнопок в ряд
GROUPS_PER_ROW = 2     # эпохи (группы) — 2 в ряд
AUTHORS_PER_ROW = 3    # авторы — 3 в ряд (можно поставить 2)


def _chunk_buttons(buttons: List[InlineKeyboardButton], per_row: int) -> List[List[InlineKeyboardButton]]:
    """Разбить список кнопок на строки по per_row"""
    per_row = max(1, int(per_row))
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def groups_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора эпох (групп).
    callback_data: group:<group_name>
    """
    groups = get_groups()

    buttons = [
        InlineKeyboardButton(text=g, callback_data=f"group:{g}")
        for g in groups
    ]

    rows = _chunk_buttons(buttons, GROUPS_PER_ROW)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def authors_keyboard(group: str) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора автора внутри эпохи.
    callback_data: author:<author_key>
    """
    authors = get_authors_by_group(group)  # dict: key -> name

    buttons = [
        InlineKeyboardButton(text=name, callback_data=f"author:{key}")
        for key, name in authors.items()
    ]

    rows = _chunk_buttons(buttons, AUTHORS_PER_ROW)

    # Кнопка назад
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back:groups")])

    return InlineKeyboardMarkup(inline_keyboard=rows)
