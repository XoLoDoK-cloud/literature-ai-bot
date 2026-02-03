from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from authors import get_groups, get_authors_by_group


def get_groups_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for g in get_groups():
        builder.add(InlineKeyboardButton(text=g["title"], callback_data=f'group_{g["key"]}'))
    builder.adjust(1)
    return builder.as_markup()


def get_authors_keyboard(group_key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    authors = get_authors_by_group(group_key)
    for a in authors:
        builder.add(InlineKeyboardButton(text=a["name"], callback_data=f'author_{a["key"]}'))

    builder.row(InlineKeyboardButton(text="⬅️ Назад к эпохам", callback_data="groups_menu"))
    builder.adjust(1)
    return builder.as_markup()


def get_chat_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="📝 Разбор текста", callback_data="mode_analysis"),
        InlineKeyboardButton(text="🎓 ЕГЭ-режим", callback_data="mode_ege"),
    )
    builder.row(
        InlineKeyboardButton(text="💬 Диалог авторов", callback_data="mode_dialog"),
    )

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


def get_cowrite_mode_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📖 Проза", callback_data="cowrite_prose"),
        InlineKeyboardButton(text="🪶 Стихи", callback_data="cowrite_poem"),
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))
    return builder.as_markup()


def get_back_to_chat_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ В обычный диалог", callback_data="back_to_chat"))
    return builder.as_markup()
