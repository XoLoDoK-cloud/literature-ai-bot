from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_authors_keyboard() -> InlineKeyboardMarkup:
    """Красивая клавиатура с карточками авторов"""
    builder = InlineKeyboardBuilder()
    
    # Авторы с иконками и описаниями
    authors_cards = [
        {
            "text": "🖋️ Александр Пушкин",
            "callback": "author_pushkin",
            "description": "Великий поэт • 1799-1837"
        },
        {
            "text": "📚 Фёдор Достоевский", 
            "callback": "author_dostoevsky",
            "description": "Философ-писатель • 1821-1881"
        },
        {
            "text": "✍️ Лев Толстой",
            "callback": "author_tolstoy", 
            "description": "Мыслитель • 1828-1910"
        },
        {
            "text": "👻 Николай Гоголь",
            "callback": "author_gogol",
            "description": "Мастер сатиры • 1809-1852"
        },
        {
            "text": "💪 ГИГАЧАД",
            "callback": "author_gigachad",
            "description": "Мотивационный эксперт • Легенда"
        }
    ]
    
    for card in authors_cards:
        builder.row(
            InlineKeyboardButton(
                text=card["text"],
                callback_data=card["callback"]
            )
        )
    
    # Кнопки действий
    builder.row(
        InlineKeyboardButton(text="🎨 Портреты авторов", callback_data="authors_gallery"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
    )
    
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
        InlineKeyboardButton(text="🎯 Викторина", callback_data="quiz_start")
    )
    
    return builder.as_markup()

def get_author_gallery_keyboard() -> InlineKeyboardMarkup:
    """Галерея портретов авторов"""
    builder = InlineKeyboardBuilder()
    
    gallery_items = [
        ("🖼️ Портрет Пушкина", "https://upload.wikimedia.org/wikipedia/commons/5/56/Alexander_Pushkin_%28Orest_Kiprensky%2C_1827%29.jpg"),
        ("🖼️ Портрет Достоевского", "https://upload.wikimedia.org/wikipedia/commons/7/78/Vasily_Perov_-_Портрет_Ф.М.Достоевского_-_Google_Art_Project.jpg"),
        ("🖼️ Портрет Толстого", "https://upload.wikimedia.org/wikipedia/commons/c/c6/Ilya_Repin_-_Portrait_of_Leo_Tolstoy_-_Google_Art_Project.jpg"),
        ("🖼️ Портрет Гоголя", "https://upload.wikimedia.org/wikipedia/commons/0/07/Gogol_by_Moller.jpg"),
    ]
    
    for text, url in gallery_items:
        builder.row(InlineKeyboardButton(text=text, url=url))
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад к выбору", callback_data="back_to_authors"))
    
    return builder.as_markup()
