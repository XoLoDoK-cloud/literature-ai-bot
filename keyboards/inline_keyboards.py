from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = [
        # Первый ряд: 3 кнопки
        [
            InlineKeyboardButton(text="🎭 Выбрать автора", callback_data="select_author"),
            InlineKeyboardButton(text="📚 Все писатели", callback_data="all_authors"),
            InlineKeyboardButton(text="💪 ГИГАЧАД", callback_data="author_gigachad")
        ],
        # Второй ряд: 2 кнопки
        [
            InlineKeyboardButton(text="📊 Моя статистика", callback_data="stats"),
            InlineKeyboardButton(text="🔄 Сбросить диалог", callback_data="reset_chat")
        ],
        # Третий ряд: 2 кнопки
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
            InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_authors_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора автора - красивое расположение в 2 ряда"""
    keyboard = [
        # Первый ряд: 3 кнопки
        [
            InlineKeyboardButton(text="🖋️ Пушкин", callback_data="author_pushkin"),
            InlineKeyboardButton(text="📚 Достоевский", callback_data="author_dostoevsky"),
            InlineKeyboardButton(text="✍️ Толстой", callback_data="author_tolstoy")
        ],
        # Второй ряд: 3 кнопки
        [
            InlineKeyboardButton(text="👻 Гоголь", callback_data="author_gogol"),
            InlineKeyboardButton(text="🏥 Чехов", callback_data="author_chekhov"),
            InlineKeyboardButton(text="💪 ГИГАЧАД", callback_data="author_gigachad")
        ],
        # Третий ряд: 2 кнопки
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
        ],
        # Четвертый ряд: 2 кнопки
        [
            InlineKeyboardButton(text="ℹ️ О боте", callback_data="about"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_chat_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура во время диалога - также в 2 ряда"""
    keyboard = [
        # Первый ряд: 2 кнопки
        [
            InlineKeyboardButton(text="👥 Сменить автора", callback_data="change_author"),
            InlineKeyboardButton(text="🔄 Новый диалог", callback_data="reset_chat")
        ],
        # Второй ряд: 2 кнопки
        [
            InlineKeyboardButton(text="ℹ️ Об авторе", callback_data="about_author"),
            InlineKeyboardButton(text="📋 Все авторы", callback_data="list_authors")
        ],
        # Третий ряд: 1 кнопка по центру
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_compact_authors_keyboard() -> InlineKeyboardMarkup:
    """Компактная клавиатура для выбора автора (только эмодзи в первом ряду)"""
    keyboard = [
        # Первый ряд: только эмодзи (5 кнопок)
        [
            InlineKeyboardButton(text="🖋️", callback_data="author_pushkin"),
            InlineKeyboardButton(text="📚", callback_data="author_dostoevsky"),
            InlineKeyboardButton(text="✍️", callback_data="author_tolstoy"),
            InlineKeyboardButton(text="👻", callback_data="author_gogol"),
            InlineKeyboardButton(text="🏥", callback_data="author_chekhov")
        ],
        # Второй ряд: имена авторов (3 кнопки)
        [
            InlineKeyboardButton(text="🖋️ Пушкин", callback_data="author_pushkin"),
            InlineKeyboardButton(text="📚 Достоевский", callback_data="author_dostoevsky"),
            InlineKeyboardButton(text="✍️ Толстой", callback_data="author_tolstoy")
        ],
        # Третий ряд: имена авторов (3 кнопки)
        [
            InlineKeyboardButton(text="👻 Гоголь", callback_data="author_gogol"),
            InlineKeyboardButton(text="🏥 Чехов", callback_data="author_chekhov"),
            InlineKeyboardButton(text="💪 ГИГАЧАД", callback_data="author_gigachad")
        ],
        # Четвертый ряд: служебные кнопки
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
