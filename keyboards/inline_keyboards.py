from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Данные об авторах
AUTHORS = {
    "pushkin": {
        "name": "Александр Пушкин",
        "emoji": "🖋️",
        "description": "Великий русский поэт"
    },
    "dostoevsky": {
        "name": "Фёдор Достоевский",
        "emoji": "📚",
        "description": "Русский писатель и философ"
    },
    "tolstoy": {
        "name": "Лев Толстой", 
        "emoji": "✍️",
        "description": "Русский писатель и мыслитель"
    },
    "gogol": {
        "name": "Николай Гоголь",
        "emoji": "👻",
        "description": "Русский прозаик и драматург"
    },
    "chekhov": {
        "name": "Антон Чехов",
        "emoji": "🏥", 
        "description": "Русский писатель и врач"
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
        ("❓ Помощь", "help")
    ]
    
    for text, callback in buttons:
        builder.add(InlineKeyboardButton(text=text, callback_data=callback))
    
    builder.adjust(2)  # 2 кнопки в ряд
    return builder.as_markup()
