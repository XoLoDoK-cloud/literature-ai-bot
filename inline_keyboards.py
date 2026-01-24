from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_chat_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Сменить автора", callback_data="change_author"),
            InlineKeyboardButton(text="🔄 Новый диалог", callback_data="reset_chat"),
        ],
        [
            InlineKeyboardButton(text="🆚 Сравнить авторов", callback_data="compare_authors"),
            InlineKeyboardButton(text="✍️ Писать вместе", callback_data="cowrite"),
        ],
        [
            InlineKeyboardButton(text="🧹 Очистить всё", callback_data="clear_all"),
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_cowrite_mode_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="📖 Рассказ", callback_data="cowrite_prose"),
            InlineKeyboardButton(text="📝 Стихотворение", callback_data="cowrite_poem"),
        ],
        [
            InlineKeyboardButton(text="↩️ Назад", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
