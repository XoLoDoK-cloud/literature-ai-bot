from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Данные об авторах
AUTHORS = {
    "pushkin": {
        "name": "Александр Пушкин",
        "emoji": "🖋️",
        "description": "Великий русский поэт (1799-1837)"
    },
    "dostoevsky": {
        "name": "Фёдор Достоевский",
        "emoji": "📚",
        "description": "Русский писатель и философ (1821-1881)"
    },
    "tolstoy": {
        "name": "Лев Толстой", 
        "emoji": "✍️",
        "description": "Русский писатель и мыслитель (1828-1910)"
    },
    "gogol": {
        "name": "Николай Гоголь",
        "emoji": "👻",
        "description": "Русский прозаик и драматург (1809-1852)"
    },
    "chekhov": {
        "name": "Антон Чехов",
        "emoji": "🏥", 
        "description": "Русский писатель и врач (1860-1904)"
    },
    "esenin": {
        "name": "Сергей Есенин",
        "emoji": "🌾",
        "description": "Русский поэт (1895-1925)"
    },
    "bulgakov": {
        "name": "Михаил Булгаков",
        "emoji": "🐱",
        "description": "Русский писатель и драматург (1891-1940)"
    },
    "akhmatova": {
        "name": "Анна Ахматова",
        "emoji": "🎭",
        "description": "Русская поэтесса (1889-1966)"
    }
}

def get_authors_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора автора"""
    builder = InlineKeyboardBuilder()
    
    for key, author in AUTHORS.items():
        builder.add(InlineKeyboardButton(
            text=f"{author['emoji']} {author['name']}",
            callback_data=f"author_{key}"
        ))
    
    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()

def get_chat_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура во время диалога"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        ("👥 Сменить автора", "change_author"),
        ("🔄 Новый диалог", "reset_chat"),
        ("ℹ️ О писателе", "about_author"),
        ("📚 Все авторы", "all_authors"),
        ("❓ Помощь", "help")
    ]
    
    for text, callback in buttons:
        builder.add(InlineKeyboardButton(text=text, callback_data=callback))
    
    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Основное меню"""
    builder = InlineKeyboardBuilder()
    
    builder.add(
        InlineKeyboardButton(text="📚 Выбрать писателя", callback_data="select_author"),
        InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
    )
    
    builder.adjust(1)  # Все кнопки в столбец
    return builder.as_markup()
