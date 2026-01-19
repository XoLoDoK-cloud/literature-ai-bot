# ========== keyboards.py ==========
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ========== КЛАВИАТУРЫ ==========

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="👥 Выбрать автора", callback_data="select_author"),
        InlineKeyboardButton(text="💪 Гигачад", callback_data="select_gigachad")
    )
    
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="🔄 Сбросить диалог", callback_data="reset_chat")
    )
    
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
        InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
    )
    
    return builder.as_markup()

def get_authors_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора автора"""
    builder = InlineKeyboardBuilder()
    
    authors = [
        ("Пушкин", "author_pushkin", "🖋️"),
        ("Достоевский", "author_dostoevsky", "📚"),
        ("Толстой", "author_tolstoy", "✍️"),
        ("Гоголь", "author_gogol", "👻"),
        ("Чехов", "author_chekhov", "🏥"),
        ("Гигачад", "author_gigachad", "💪")
    ]
    
    for name, callback, emoji in authors:
        builder.row(
            InlineKeyboardButton(
                text=f"{emoji} {name}",
                callback_data=callback
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
    )
    
    return builder.as_markup()

def get_chat_keyboard(include_gigachad_mode: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура во время диалога"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="👥 Сменить автора", callback_data="change_author"),
        InlineKeyboardButton(text="🔄 Новый диалог", callback_data="reset_chat")
    )
    
    builder.row(
        InlineKeyboardButton(text="ℹ️ Об авторе", callback_data="about_author"),
        InlineKeyboardButton(text="📋 Все авторы", callback_data="list_authors")
    )
    
    if include_gigachad_mode:
        builder.row(
            InlineKeyboardButton(text="👑 Гигачад активен!", callback_data="gigachad_info")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="💪 Включить Гигачад-стиль", callback_data="toggle_gigachad_style")
        )
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()
