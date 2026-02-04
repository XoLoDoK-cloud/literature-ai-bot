# inline_keyboards.py
from __future__ import annotations

from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from authors import get_groups, get_authors_by_group


GROUPS_PER_ROW = 2
AUTHORS_PER_ROW = 3


def _chunk(buttons: List[InlineKeyboardButton], per_row: int) -> List[List[InlineKeyboardButton]]:
    per_row = max(1, int(per_row))
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def _short_author_button_text(full_name: str) -> str:
    """
    Вариант 1: Фамилия + инициалы (если 3 слова)
      'Александр Сергеевич Пушкин' -> 'Пушкин А. С.'
    Вариант 2: только фамилия (если имя нестандартное)
      'Михаил Булгаков' -> 'Булгаков'
      'Иосиф Александрович Бродский' -> 'Бродский И. А.' (если 3 слова)
    """
    name = (full_name or "").strip()
    if not name:
        return "Автор"

    parts = name.split()
    # Обычный случай: Фамилия Имя Отчество
    if len(parts) == 3:
        last, first, middle = parts
        # защита от пустых строк
        first_i = (first[0] + ".") if first else ""
        middle_i = (middle[0] + ".") if middle else ""
        return f"{last} {first_i} {middle_i}".strip()

    # Если больше 3 слов — берём первую часть как фамилию (вариант 2)
    # Если меньше 3 слов — тоже только фамилия
    return parts[0]


def get_groups_keyboard() -> InlineKeyboardMarkup:
    groups = get_groups()
    buttons = [InlineKeyboardButton(text=g, callback_data=f"group_{g}") for g in groups]
    return InlineKeyboardMarkup(inline_keyboard=_chunk(buttons, GROUPS_PER_ROW))


def get_authors_keyboard(group: str) -> InlineKeyboardMarkup:
    authors = get_authors_by_group(group)  # key -> name

    buttons = [
        InlineKeyboardButton(
            text=_short_author_button_text(name),
            callback_data=f"author_{key}"
        )
        for key, name in authors.items()
    ]

    rows = _chunk(buttons, AUTHORS_PER_ROW)
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data="groups_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_chat_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="🆚 Сравнить авторов", callback_data="compare_authors"),
            InlineKeyboardButton(text="✍️ Соавторство", callback_data="cowrite"),
        ],
        [
            InlineKeyboardButton(text="🔄 Очистить диалог", callback_data="reset_chat"),
            InlineKeyboardButton(text="👤 Сменить автора", callback_data="change_author"),
        ],
        [
            InlineKeyboardButton(text="🧹 Очистить всё", callback_data="clear_all"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_cowrite_mode_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="📝 Рассказ", callback_data="cowrite_prose"),
            InlineKeyboardButton(text="🎭 Стихотворение", callback_data="cowrite_poem"),
        ],
        [
            InlineKeyboardButton(text="⬅ Назад", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
