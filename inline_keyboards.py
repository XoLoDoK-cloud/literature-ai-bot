from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from authors import (
    list_group_keys,
    get_group_title,
    list_author_keys_by_group,
    get_author,
)


def get_groups_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for g in list_group_keys():
        builder.button(text=get_group_title(g), callback_data=f"group_{g}")

    builder.adjust(1)
    return builder.as_markup()


def get_authors_keyboard(group_key: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    keys = list_author_keys_by_group(group_key)

    for key in keys:
        a = get_author(key) or {}
        builder.button(text=a.get("name", key), callback_data=f"author_{key}")

    builder.adjust(2)

    builder.row()
    builder.button(text="🔙 Назад к эпохам", callback_data="groups_menu")
    builder.adjust(2, 1)
    return builder.as_markup()


def get_chat_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="👥 Смена автора", callback_data="change_author")
    builder.button(text="🔄 Новый диалог", callback_data="reset_chat")

    builder.button(text="🆚 Сравнение", callback_data="compare_authors")
    builder.button(text="✍️ Писать вместе", callback_data="cowrite")

    builder.button(text="🏠 Главное меню", callback_data="main_menu")
    builder.button(text="🧹 Полная очистка", callback_data="clear_all")

    builder.adjust(2, 2, 2)
    return builder.as_markup()


def get_cowrite_mode_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.button(text="📝 Проза (рассказ)", callback_data="cowrite_prose")
    builder.button(text="🎼 Поэзия (стих)", callback_data="cowrite_poem")
    builder.button(text="🔙 Назад", callback_data="main_menu")

    builder.adjust(1, 1, 1)
    return builder.as_markup()
