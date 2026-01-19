from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def create_button(text: str, callback_data: str, emoji: str = "") -> InlineKeyboardButton:
    """Создает красивую кнопку с эмодзи"""
    if emoji:
        text = f"{emoji} {text}"
    return InlineKeyboardButton(text=text, callback_data=callback_data)

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню с красивыми кнопками"""
    builder = InlineKeyboardBuilder()
    
    # Первый ряд: Основные действия
    builder.row(
        create_button("Выбрать автора", "select_author", "👥"),
        create_button("ГИГАЧАД", "author_gigachad", "💪")
    )
    
    # Второй ряд: Специальные режимы
    builder.row(
        create_button("Что если...", "what_if_mode", "🎭"),
        create_button("Совместное письмо", "start_writing", "✍️")
    )
    
    # Третий ряд: Исследование
    builder.row(
        create_button("Таймлайн", "timeline_menu", "📅"),
        create_button("Рекомендации", "books_menu", "📚")
    )
    
    # Четвертый ряд: Мультимедиа
    builder.row(
        create_button("Голосовые", "voice_menu", "🎤"),
        create_button("Иллюстрации", "illustrations_menu", "🖼️")
    )
    
    # Пятый ряд: Игры и статистика
    builder.row(
        create_button("Викторина", "quiz_start", "🎯"),
        create_button("Статистика", "stats_menu", "📊")
    )
    
    # Шестой ряд: Профиль и помощь
    builder.row(
        create_button("Достижения", "achievements_menu", "🏆"),
        create_button("Помощь", "help_menu", "❓")
    )
    
    return builder.as_markup()

def get_authors_keyboard() -> InlineKeyboardMarkup:
    """Красивая клавиатура выбора автора"""
    builder = InlineKeyboardBuilder()
    
    # Авторы в стильных карточках
    authors = [
        ("Пушкин", "author_pushkin", "🖋️", "Поэт • 1799-1837"),
        ("Достоевский", "author_dostoevsky", "📚", "Философ • 1821-1881"),
        ("Толстой", "author_tolstoy", "✍️", "Мыслитель • 1828-1910"),
        ("Гоголь", "author_gogol", "👻", "Мистик • 1809-1852"),
        ("Чехов", "author_chekhov", "🏥", "Драматург • 1860-1904"),
        ("ГИГАЧАД", "author_gigachad", "💪", "Мотиватор • Легенда")
    ]
    
    for name, callback, emoji, desc in authors:
        builder.row(
            InlineKeyboardButton(
                text=f"{emoji} {name}",
                callback_data=callback
            )
        )
    
    # Кнопка возврата
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад в главное меню",
            callback_data="main_menu"
        )
    )
    
    return builder.as_markup()

def get_chat_keyboard(user_id: int, what_if_mode: bool = False) -> InlineKeyboardMarkup:
    """Красивая клавиатура для диалога"""
    builder = InlineKeyboardBuilder()
    
    # Первый ряд: Основные действия
    builder.row(
        create_button("Сменить автора", "change_author", "👥"),
        create_button("Новый диалог", "reset_chat", "🔄")
    )
    
    # Второй ряд: Информация
    builder.row(
        create_button("Об авторе", "about_author", "📖"),
        create_button("Иллюстрации", "show_illustrations", "🖼️")
    )
    
    # Третий ряд: Специальные режимы
    if what_if_mode:
        builder.row(
            create_button("Что если ВКЛ", "toggle_whatif", "🎭"),
            create_button("Гигачад-режим", "toggle_gigachad", "💪")
        )
    else:
        builder.row(
            create_button("Режим 'Что если'", "toggle_whatif", "🎭"),
            create_button("Гигачад-режим", "toggle_gigachad", "💪")
        )
    
    # Четвертый ряд: Дополнительно
    builder.row(
        create_button("Таймлайн жизни", f"timeline_{user_id}", "📅"),
        create_button("Книги автора", "author_books", "📚")
    )
    
    # Пятый ряд: Возврат
    builder.row(
        create_button("Главное меню", "main_menu", "🏠")
    )
    
    return builder.as_markup()

def get_what_if_keyboard() -> InlineKeyboardMarkup:
    """Красивая клавиатура для режима 'Что если...'"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        create_button("Выбрать автора", "select_author", "👥"),
        create_button("Примеры вопросов", "what_if_examples", "💡")
    )
    
    builder.row(
        create_button("Обычный режим", "toggle_whatif", "🔄"),
        create_button("Случайный сценарий", "random_whatif", "🎲")
    )
    
    builder.row(
        create_button("Начать беседу", "start_whatif_chat", "🚀"),
        create_button("Сохранённые сценарии", "saved_scenarios", "💾")
    )
    
    builder.row(
        create_button("Главное меню", "main_menu", "🏠")
    )
    
    return builder.as_markup()

def get_writing_keyboard() -> InlineKeyboardMarkup:
    """Красивая клавиатура для совместного письма"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        create_button("Выбрать автора", "select_author_writing", "👥"),
        create_button("Выбрать жанр", "select_genre", "📖")
    )
    
    builder.row(
        create_button("Примеры начала", "writing_examples", "💡"),
        create_button("Продолжить историю", "continue_story", "✍️")
    )
    
    builder.row(
        create_button("Сохранить текст", "save_text", "💾"),
        create_button("Новый текст", "new_text", "🔄")
    )
    
    builder.row(
        create_button("Мои произведения", "my_writings", "📚"),
        create_button("Поделиться", "share_writing", "📤")
    )
    
    builder.row(
        create_button("Главное меню", "main_menu", "🏠")
    )
    
    return builder.as_markup()

def get_timeline_keyboard() -> InlineKeyboardMarkup:
    """Красивая клавиатура для таймлайна"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        create_button("Пушкин", "timeline_pushkin", "🖋️"),
        create_button("Достоевский", "timeline_dostoevsky", "📚")
    )
    
    builder.row(
        create_button("Толстой", "timeline_tolstoy", "✍️"),
        create_button("Гоголь", "timeline_gogol", "👻")
    )
    
    builder.row(
        create_button("Чехов", "timeline_chekhov", "🏥"),
        create_button("Все авторы", "all_timelines", "📅")
    )
    
    builder.row(
        create_button("Хронология", "chronology", "⏳"),
        create_button("Сравнить жизни", "compare_lives", "⚖️")
    )
    
    builder.row(
        create_button("Главное меню", "main_menu", "🏠")
    )
    
    return builder.as_markup()

def get_book_recommendations_keyboard(recommendations: list) -> InlineKeyboardMarkup:
    """Красивая клавиатура для рекомендаций книг"""
    builder = InlineKeyboardBuilder()
    
    for i, book in enumerate(recommendations[:4], 1):
        builder.row(
            InlineKeyboardButton(
                text=f"{i}. 📖 {book['title'][:20]}...",
                callback_data=f"book_{book['id']}"
            )
        )
    
    builder.row(
        create_button("Новые рекомендации", "new_recommendations", "🔄"),
        create_button("Мои предпочтения", "my_preferences", "⭐")
    )
    
    builder.row(
        create_button("По жанру", "by_genre", "📚"),
        create_button("По сложности", "by_difficulty", "🎯")
    )
    
    builder.row(
        create_button("Топ книг", "top_books", "🏆"),
        create_button("Случайная книга", "random_book", "🎲")
    )
    
    builder.row(
        create_button("Главное меню", "main_menu", "🏠")
    )
    
    return builder.as_markup()

def get_voice_keyboard() -> InlineKeyboardMarkup:
    """Красивая клавиатура для голосовых ответов"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        create_button("Послушать цитату", "voice_quote", "🎤"),
        create_button("Голос автора", "voice_author", "🎭")
    )
    
    builder.row(
        create_button("Озвучить текст", "voice_text", "📖"),
        create_button("Фоновая музыка", "background_music", "🎵")
    )
    
    builder.row(
        create_button("Настройки голоса", "voice_settings", "⚙️"),
        create_button("Примеры", "voice_examples", "💡")
    )
    
    builder.row(
        create_button("Мои записи", "my_recordings", "💾"),
        create_button("Поделиться", "share_voice", "📤")
    )
    
    builder.row(
        create_button("Главное меню", "main_menu", "🏠")
    )
    
    return builder.as_markup()

def get_illustrations_keyboard() -> InlineKeyboardMarkup:
    """Красивая клавиатура для иллюстраций"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        create_button("Обложки книг", "illustrations_covers", "🖼️"),
        create_button("Иллюстрации", "illustrations_art", "🎨")
    )
    
    builder.row(
        create_button("Портреты", "illustrations_portraits", "📸"),
        create_button("Места", "illustrations_places", "🏛️")
    )
    
    builder.row(
        create_button("Персонажи", "illustrations_characters", "🎭"),
        create_button("Эпоха", "illustrations_era", "📅")
    )
    
    builder.row(
        create_button("Галерея", "gallery", "🖼️"),
        create_button("Случайное изображение", "random_image", "🎲")
    )
    
    builder.row(
        create_button("Главное меню", "main_menu", "🏠")
    )
    
    return builder.as_markup()
