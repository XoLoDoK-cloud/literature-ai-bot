# inline_keyboards.py

from __future__ import annotations

from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from authors import get_groups, get_authors_by_group


# Сколько кнопок в ряд
GROUPS_PER_ROW = 2
AUTHORS_PER_ROW = 3


def _chunk_buttons(buttons: List[InlineKeyboardButton], per_row: int) -> List[List[InlineKeyboardButton]]:
    per_row = max(1, int(per_row))
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


# =========================
# ЭПОХИ (ГРУППЫ)
# =========================
def get_groups_keyboard() -> InlineKeyboardMarkup:
    """
    callback_data: group_<group_name>
    """
    groups = get_groups()
    buttons = [InlineKeyboardButton(text=g, callback_data=f"group_{g}") for g in groups]
    rows = _chunk_buttons(buttons, GROUPS_PER_ROW)
    return InlineKeyboardMarkup(inline_keyboard=rows)


# =========================
# АВТОРЫ ВНУТРИ ЭПОХИ
# =========================
def get_authors_keyboard(group: str) -> InlineKeyboardMarkup:
    """
    callback_data: author_<author_key>
    """
    authors = get_authors_by_group(group)  # dict: key -> name

    buttons = [InlineKeyboardButton(text=name, callback_data=f"author_{key}") for key, name in authors.items()]
    rows = _chunk_buttons(buttons, AUTHORS_PER_ROW)

    # Назад к эпохам (main.py ловит F.data == "groups_menu")
    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data="groups_menu")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


# =========================
# КЛАВИАТУРА ЧАТА (после выбора автора)
# =========================
def get_chat_keyboard() -> InlineKeyboardMarkup:
    """
    callback_data должны совпадать с main.py:
    - compare_authors
    - cowrite
    - reset_chat
    - change_author
    - clear_all
    """
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


# =========================
# КЛАВИАТУРА ВЫБОРА РЕЖИМА СОАВТОРСТВА
# =========================
def get_cowrite_mode_keyboard() -> InlineKeyboardMarkup:
    """
    callback_data совпадает с main.py:
    - cowrite_prose
    - cowrite_poem
    + назад в главное меню (main_menu)
    """
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
