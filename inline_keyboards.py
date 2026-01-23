# inline_keyboards.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="🎭 Выбрать автора", callback_data="select_author"),
            InlineKeyboardButton(text="📚 Все писатели", callback_data="list_authors"),
        ],
        [
            InlineKeyboardButton(text="📊 Моя статистика", callback_data="stats"),
            InlineKeyboardButton(text="🔄 Сбросить диалог", callback_data="reset_chat"),
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
            InlineKeyboardButton(text="ℹ️ О боте", callback_data="about"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_authors_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="🖋️ Пушкин", callback_data="author_pushkin"),
            InlineKeyboardButton(text="📚 Достоевский", callback_data="author_dostoevsky"),
            InlineKeyboardButton(text="✍️ Толстой", callback_data="author_tolstoy"),
        ],
        [
            InlineKeyboardButton(text="👻 Гоголь", callback_data="author_gogol"),
            InlineKeyboardButton(text="🏥 Чехов", callback_data="author_chekhov"),
            InlineKeyboardButton(text="💪 ГИГАЧАД", callback_data="author_gigachad"),
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_chat_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Сменить автора", callback_data="change_author"),
            InlineKeyboardButton(text="🔄 Новый диалог", callback_data="reset_chat"),
        ],
        [
            InlineKeyboardButton(text="📊 Моя статистика", callback_data="stats"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
