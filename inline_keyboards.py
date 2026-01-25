from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from authors import list_author_keys, get_author


def get_authors_keyboard() -> InlineKeyboardMarkup:
    """
    Динамическая клавиатура авторов:
    - берём ключи из authors.py
    - отображаем name каждого автора
    - callback_data = author_<key>
    """
    builder = InlineKeyboardBuilder()

    keys = list_author_keys()

    # Чтобы "ГИГАЧАД" был в конце (если он есть)
    if "gigachad" in keys:
        keys = [k for k in keys if k != "gigachad"] + ["gigachad"]

    for key in keys:
        a = get_author(key) or {}
        title = a.get("name", key)
        builder.button(text=title, callback_data=f"author_{key}")

    # 2 кнопки в ряд (можешь поставить 3 если хочешь компактнее)
    builder.adjust(2)
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
