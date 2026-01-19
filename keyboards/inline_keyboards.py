from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ========== ГЛАВНОЕ МЕНЮ ==========

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    builder = InlineKeyboardBuilder()
    
    # Основные действия
    builder.row(
        InlineKeyboardButton(text="📚 Выбрать автора", callback_data="select_author"),
        InlineKeyboardButton(text="💪 Гигачад", callback_data="author_gigachad")
    )
    
    builder.row(
        InlineKeyboardButton(text="🎭 Что если...", callback_data="what_if_mode"),
        InlineKeyboardButton(text="✍️ Совместное письмо", callback_data="start_writing")
    )
    
    builder.row(
        InlineKeyboardButton(text="📅 Таймлайн", callback_data="timeline_menu"),
        InlineKeyboardButton(text="📚 Рекомендации", callback_data="books_menu")
    )
    
    builder.row(
        InlineKeyboardButton(text="🎤 Голосовые ответы", callback_data="voice_menu"),
        InlineKeyboardButton(text="🖼️ Иллюстрации", callback_data="illustrations_menu")
    )
    
    # Дополнительные функции
    builder.row(
        InlineKeyboardButton(text="🎯 Викторина", callback_data="quiz_start"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats_menu")
    )
    
    builder.row(
        InlineKeyboardButton(text="🏆 Достижения", callback_data="achievements_menu"),
        InlineKeyboardButton(text="❓ Помощь", callback_data="help_menu")
    )
    
    return builder.as_markup()

# ========== ВЫБОР АВТОРА ==========

def get_authors_keyboard(writing_mode: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура выбора автора"""
    builder = InlineKeyboardBuilder()
    
    authors = [
        ("🖋️ Пушкин", "pushkin"),
        ("📚 Достоевский", "dostoevsky"),
        ("✍️ Толстой", "tolstoy"),
        ("👻 Гоголь", "gogol"),
        ("🏥 Чехов", "chekhov"),
        ("💪 ГИГАЧАД", "gigachad")
    ]
    
    for text, author_key in authors:
        if writing_mode:
            callback_data = f"write_with_{author_key}"
        else:
            callback_data = f"author_{author_key}"
        
        builder.button(text=text, callback_data=callback_data)
    
    builder.adjust(2)  # 2 кнопки в ряд
    
    if not writing_mode:
        builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu"))
    
    return builder.as_markup()

# ========== ЧАТ КЛАВИАТУРА ==========

def get_chat_keyboard(user_id: int, what_if_mode: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура во время диалога"""
    builder = InlineKeyboardBuilder()
    
    # Основные кнопки
    buttons = [
        ("👥 Сменить автора", "change_author"),
        ("🔄 Новый диалог", "reset_chat"),
        ("📖 Об авторе", "about_author"),
        ("🖼️ Иллюстрации", "show_illustrations")
    ]
    
    for text, callback_data in buttons:
        builder.button(text=text, callback_data=callback_data)
    
    builder.adjust(2)
    
    # Специальные режимы
    if what_if_mode:
        builder.row(
            InlineKeyboardButton(text="🎭 Что если ВКЛ", callback_data="toggle_whatif")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🎭 Режим 'Что если'", callback_data="toggle_whatif"),
            InlineKeyboardButton(text="💪 Гигачад-режим", callback_data="toggle_gigachad")
        )
    
    # Дополнительные функции
    builder.row(
        InlineKeyboardButton(text="📅 Таймлайн жизни", callback_data=f"timeline_{user_id}"),
        InlineKeyboardButton(text="📚 Книги автора", callback_data="author_books")
    )
    
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()

# ========== РЕЖИМ "ЧТО ЕСЛИ" ==========

def get_what_if_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для режима 'Что если...'"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📚 Выбрать автора", callback_data="select_author"),
        InlineKeyboardButton(text="💡 Примеры вопросов", callback_data="what_if_examples")
    )
    
    builder.row(
        InlineKeyboardButton(text="🔄 Обычный режим", callback_data="toggle_whatif"),
        InlineKeyboardButton(text="🎭 Случайный сценарий", callback_data="random_whatif")
    )
    
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    
    return builder.as_markup()

# ========== СОВМЕСТНОЕ ПИСЬМО ==========

def get_writing_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для совместного письма"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📚 Выбрать автора", callback_data="select_author_writing"),
        InlineKeyboardButton(text="🎭 Выбрать жанр", callback_data="select_genre")
    )
    
    builder.row(
        InlineKeyboardButton(text="💡 Примеры начала", callback_data="writing_examples"),
        InlineKeyboardButton(text="📖 Продолжить историю", callback_data="continue_story")
    )
    
    builder.row(
        InlineKeyboardButton(text="💾 Сохранить текст", callback_data="save_text"),
        InlineKeyboardButton(text="🔄 Новый текст", callback_data="new_text")
    )
    
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    
    return builder.as_markup()

# ========== ТАЙМЛАЙН ==========

def get_timeline_keyboard(selected_author: str = None) -> InlineKeyboardMarkup:
    """Клавиатура для таймлайна"""
    builder = InlineKeyboardBuilder()
    
    authors = [
        ("🖋️ Таймлайн Пушкина", "timeline_pushkin"),
        ("📚 Таймлайн Достоевского", "timeline_dostoevsky"),
        ("✍️ Таймлайн Толстого", "timeline_tolstoy"),
        ("👻 Таймлайн Гоголя", "timeline_gogol"),
        ("🏥 Таймлайн Чехова", "timeline_chekhov")
    ]
    
    for text, callback_data in authors:
        builder.button(text=text, callback_data=callback_data)
    
    builder.adjust(2)
    
    if selected_author:
        builder.row(
            InlineKeyboardButton(text="📖 Ключевые произведения", callback_data=f"works_{selected_author}"),
            InlineKeyboardButton(text="🎭 Важные события", callback_data=f"events_{selected_author}")
        )
    
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    
    return builder.as_markup()

# ========== РЕКОМЕНДАЦИИ КНИГ ==========

def get_book_recommendations_keyboard(recommendations: list) -> InlineKeyboardMarkup:
    """Клавиатура для рекомендаций книг"""
    builder = InlineKeyboardBuilder()
    
    for i, book in enumerate(recommendations[:5], 1):
        builder.button(
            text=f"{i}. {book['title'][:20]}...",
            callback_data=f"book_{book['id']}"
        )
    
    builder.adjust(2)
    
    builder.row(
        InlineKeyboardButton(text="🔄 Новые рекомендации", callback_data="new_recommendations"),
        InlineKeyboardButton(text="📖 Мои предпочтения", callback_data="my_preferences")
    )
    
    builder.row(
        InlineKeyboardButton(text="🎯 По жанру", callback_data="by_genre"),
        InlineKeyboardButton(text="⭐ По сложности", callback_data="by_difficulty")
    )
    
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    
    return builder.as_markup()

# ========== ВИКТОРИНА ==========

def get_quiz_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для викторины"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🎯 Легкая викторина", callback_data="quiz_easy"),
        InlineKeyboardButton(text="🧠 Средняя викторина", callback_data="quiz_medium")
    )
    
    builder.row(
        InlineKeyboardButton(text="🏆 Сложная викторина", callback_data="quiz_hard"),
        InlineKeyboardButton(text="🎲 Случайные вопросы", callback_data="quiz_random")
    )
    
    builder.row(
        InlineKeyboardButton(text="📊 Мои результаты", callback_data="quiz_results"),
        InlineKeyboardButton(text="🏆 Рейтинг", callback_data="quiz_leaderboard")
    )
    
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    
    return builder.as_markup()

# ========== ГОЛОСОВЫЕ ОТВЕТЫ ==========

def get_voice_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для голосовых ответов"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🎤 Послушать цитату", callback_data="voice_quote"),
        InlineKeyboardButton(text="🎭 Голос автора", callback_data="voice_author")
    )
    
    builder.row(
        InlineKeyboardButton(text="📖 Озвучить текст", callback_data="voice_text"),
        InlineKeyboardButton(text="🎵 Фоновая музыка", callback_data="background_music")
    )
    
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки голоса", callback_data="voice_settings"),
        InlineKeyboardButton(text="💡 Примеры", callback_data="voice_examples")
    )
    
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    
    return builder.as_markup()

# ========== ИЛЛЮСТРАЦИИ ==========

def get_illustrations_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для иллюстраций"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🖼️ Обложки книг", callback_data="illustrations_covers"),
        InlineKeyboardButton(text="🎨 Иллюстрации", callback_data="illustrations_art")
    )
    
    builder.row(
        InlineKeyboardButton(text="📸 Портреты", callback_data="illustrations_portraits"),
        InlineKeyboardButton(text="🏛️ Места", callback_data="illustrations_places")
    )
    
    builder.row(
        InlineKeyboardButton(text="🎭 Персонажи", callback_data="illustrations_characters"),
        InlineKeyboardButton(text="📅 Эпоха", callback_data="illustrations_era")
    )
    
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    
    return builder.as_markup()
