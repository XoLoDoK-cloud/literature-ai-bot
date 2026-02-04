# inline_keyboards.py
from __future__ import annotations

from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from authors import get_groups, get_authors_by_group


# ===== Настройки "адаптива" =====
GROUPS_PER_ROW = 2

# Базово хотим 2 в ряд (мобильно)
AUTHORS_PER_ROW_DEFAULT = 2

# Если ФИО слишком длинные — на телефоне будет резать, поэтому делаем 1 в ряд
# Подбери число под себя: 18–22 обычно нормально
AUTHOR_TEXT_LEN_FOR_SINGLE_ROW = 20


def _chunk(buttons: List[InlineKeyboardButton], per_row: int) -> List[List[InlineKeyboardButton]]:
    per_row = max(1, int(per_row))
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def _authors_per_row_by_length(author_names: List[str]) -> int:
    """
    Адаптация под телефон:
    - если есть длинные ФИО -> 1 в ряд (чтобы не резало)
    - иначе -> 2 в ряд
    """
    if not author_names:
        return AUTHORS_PER_ROW_DEFAULT
    longest = max(len((n or "").strip()) for n in author_names)
    return 1 if longest >= AUTHOR_TEXT_LEN_FOR_SINGLE_ROW else AUTHORS_PER_ROW_DEFAULT


# =========================
# 📚 ВЫБОР ЭПОХИ
# =========================
def get_groups_keyboard() -> InlineKeyboardMarkup:
    groups = get_groups()
    buttons = [InlineKeyboardButton(text=g, callback_data=f"group_{g}") for g in groups]
    return InlineKeyboardMarkup(inline_keyboard=_chunk(buttons, GROUPS_PER_ROW))


# =========================
# 👤 ВЫБОР АВТОРА (полное ФИО + адаптация рядов)
# =========================
def get_authors_keyboard(group: str) -> InlineKeyboardMarkup:
    authors = get_authors_by_group(group)  # key -> full name (уже отсортировано)
    names = list(authors.values())

    per_row = _authors_per_row_by_length(names)

    buttons = [
        InlineKeyboardButton(text=name, callback_data=f"author_{key}")
        for key, name in authors.items()
    ]

    rows = _chunk(buttons, per_row)

    rows.append([InlineKeyboardButton(text="⬅ Назад", callback_data="groups_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# =========================
# 💬 КЛАВИАТУРА ЧАТА (мобильная)
# =========================
def get_chat_keyboard() -> InlineKeyboardMarkup:
    # На телефоне лучше, когда не всё в одной широкой строке
    rows = [
        [
            InlineKeyboardButton(text="🆚 Сравнить авторов", callback_data="compare_authors"),
        ],
        [
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
# ✍️ СОАВТОРСТВО (мобильное)
# =========================
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
