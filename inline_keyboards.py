from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from authors import get_groups, get_authors_by_group


# =========================
# 1) Выбор эпохи/сборника
# =========================
def get_groups_keyboard() -> InlineKeyboardMarkup:
    """
    Клавиатура выбора эпохи/сборника.
    callback_data: group_<group_key>
    """
    builder = InlineKeyboardBuilder()

    groups = get_groups()  # список dict: {"key": "...", "title": "..."}
    for g in groups:
        builder.add(
            InlineKeyboardButton(
                text=g["title"],
                callback_data=f'group_{g["key"]}'
            )
        )

    builder.adjust(1)
    return builder.as_markup()


# =========================
# 2) Выбор автора внутри эпохи
# =========================
def get_authors_keyboard(group_key: str) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора автора внутри эпохи/сборника.
    callback_data: author_<author_key>
    """
    builder = InlineKeyboardBuilder()

    authors = get_authors_by_group(group_key)  # список dict: {"key": "...", "name": "..."}
    for a in authors:
        builder.add(
            InlineKeyboardButton(
                text=a["name"],
                callback_data=f'author_{a["key"]}'
            )
        )

    # Навигация
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к эпохам", callback_data="groups_menu")
    )

    builder.adjust(1)
    return builder.as_markup()


# =========================
# 3) Основное меню в чате (после выбора автора)
# =========================
def get_chat_keyboard() -> InlineKeyboardMarkup:
    """
    Главная клавиатура действий в диалоге.
    """
    builder = InlineKeyboardBuilder()

    # 🔥 Новые режимы
    builder.row(
        InlineKeyboardButton(text="📝 Разбор текста", callback_data="mode_analysis"),
        InlineKeyboardButton(text="🎓 ЕГЭ-режим", callback_data="mode_ege"),
    )
    builder.row(
        InlineKeyboardButton(text="💬 Диалог авторов", callback_data="mode_dialog"),
    )

    # Старые функции (что у тебя уже было)
    builder.row(
        InlineKeyboardButton(text="✍️ Соавторство", callback_data="cowrite"),
        InlineKeyboardButton(text="🆚 Сравнить авторов", callback_data="compare_authors"),
    )

    builder.row(
        InlineKeyboardButton(text="🔁 Сменить автора", callback_data="change_author"),
        InlineKeyboardButton(text="🔄 Очистить диалог", callback_data="reset_chat"),
    )

    builder.row(
        InlineKeyboardButton(text="🧹 Очистить всё", callback_data="clear_all"),
        InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu"),
    )

    return builder.as_markup()


# =========================
# 4) Режим соавторства
# =========================
def get_cowrite_mode_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📖 Проза", callback_data="cowrite_prose"),
        InlineKeyboardButton(text="🪶 Стихи", callback_data="cowrite_poem"),
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"),
    )

    return builder.as_markup()


# =========================
# 5) Кнопка выхода из специальных режимов
# =========================
def get_back_to_chat_keyboard() -> InlineKeyboardMarkup:
    """
    Когда пользователь в режиме (ЕГЭ/разбор/диалог) — чтобы он мог вернуться в обычный чат.
    """
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⬅️ В обычный диалог", callback_data="back_to_chat")
    )
    return builder.as_markup()
