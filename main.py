import asyncio
import logging
import sys
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Импорт конфигурации
from config import BOT_TOKEN, GIGACHAT_CREDENTIALS

# Импорт сервисов
from services.gigachat_client import GigaChatClient
from services.daily_quotes import daily_quotes
from services.statistics import stats_service
from services.quiz_service import quiz_service
from services.achievements import achievements_service
from services.timeline_service import timeline_service
from services.book_recommendations import book_recommendations

# Импорт клавиатур
from keyboards.inline_keyboards import (
    get_main_menu_keyboard,
    get_authors_keyboard,
    get_chat_keyboard,
    get_quiz_keyboard,
    get_timeline_keyboard,
    get_what_if_keyboard,
    get_writing_keyboard,
    get_book_recommendations_keyboard
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Инициализация клиентов
gigachat_client = GigaChatClient(GIGACHAT_CREDENTIALS)

# Хранилище пользователей (временное)
user_storage = {}
writing_sessions = {}  # Для режима совместного письма

def get_user_data(user_id: int) -> dict:
    """Получает данные пользователя"""
    if user_id not in user_storage:
        user_storage[user_id] = {
            "selected_author": None,
            "conversation_history": [],
            "message_count": 0,
            "gigachad_mode": False,
            "achievements": [],
            "last_active": datetime.now().isoformat(),
            "book_preferences": [],
            "what_if_mode": False
        }
    return user_storage[user_id]

# Создаем роутер
router = Router()

# ========== КОМАНДЫ БОТА ==========

@router.message(CommandStart())
async def command_start(message: Message):
    """Команда /start - главное меню"""
    user_id = message.from_user.id
    
    # Получаем или создаем данные пользователя
    user_data = get_user_data(user_id)
    user_data["username"] = message.from_user.username
    user_data["first_name"] = message.from_user.first_name
    user_data["last_active"] = datetime.now().isoformat()
    
    # Проверяем новые достижения
    new_achievements = achievements_service.check_new_achievements(user_id, user_data)
    
    welcome_text = f"""
{'═' * 40}
🎭 <b>ЛИТЕРАТУРНЫЙ САЛОН v3.0</b> 🚀
{'═' * 40}

👋 <b>Добро пожаловать, {message.from_user.first_name}!</b>

✨ <b>Новые возможности:</b>
• 🎤 <b>Голосовые ответы</b> (новинка!)
• 🎭 <b>Режим "Что если..."</b>
• ✍️ <b>Совместное письмо</b> с авторами
• 🖼️ <b>Иллюстрации книг</b>
• 📅 <b>Таймлайн жизни</b> писателей
• 📚 <b>Рекомендации книг</b>

🎯 <b>Сегодняшняя миссия:</b>
Побеседовать с 2 разными авторами
"""
    
    if new_achievements:
        welcome_text += f"\n🏆 <b>Новое достижение!</b>\n"
        for ach in new_achievements:
            welcome_text += f"• {ach['name']} - {ach['description']}\n"
    
    welcome_text += f"\n{'═' * 40}\n👇 <b>Выберите действие:</b>"
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    logger.info(f"👤 Новый пользователь: {user_id} (@{message.from_user.username})")

@router.message(Command("gigachad"))
async def command_gigachad(message: Message):
    """Быстрая команда Гигачада"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    user_data["selected_author"] = "gigachad"
    user_data["gigachad_mode"] = True
    user_data["conversation_history"] = []
    
    await message.answer(
        "💪 <b>РЕЖИМ ГИГАЧАД АКТИВИРОВАН!</b>\n\n"
        "<i>Мотивация + литература = ЛЕГЕНДА</i>\n\n"
        "🔥 <b>Примеры вопросов:</b>\n"
        "• Как прокачать мозг книгами?\n"
        "• В чём сила классики для мужчины?\n"
        "• Что Пушкин думал бы о качалке?\n\n"
        "<code>🚀 Задавай вопрос — получай мотивацию!</code>",
        reply_markup=get_chat_keyboard(user_id),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("whatif"))
async def command_whatif(message: Message):
    """Режим 'Что если...'"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    user_data["what_if_mode"] = True
    
    await message.answer(
        "🎭 <b>РЕЖИМ 'ЧТО ЕСЛИ...'</b>\n\n"
        "<i>Исследуйте альтернативные реальности с писателями!</i>\n\n"
        "🔮 <b>Примеры вопросов:</b>\n"
        "• Что если Пушкин жил в 21 веке?\n"
        "• Что если Достоевский писал детективы?\n"
        "• Что если Толстой был IT-предпринимателем?\n\n"
        "<code>Выберите автора и задавайте 'что если' вопросы!</code>",
        reply_markup=get_what_if_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("write"))
async def command_write(message: Message):
    """Совместное письмо с автором"""
    user_id = message.from_user.id
    
    await message.answer(
        "✍️ <b>СОВМЕСТНОЕ ПИСЬМО</b>\n\n"
        "<i>Напишите произведение вместе с великим писателем!</i>\n\n"
        "📝 <b>Как это работает:</b>\n"
        "1. Выберите автора\n"
        "2. Выберите жанр\n"
        "3. Начните писать предложение\n"
        "4. Автор продолжит за вас\n\n"
        "<code>Создайте шедевр вместе с классиком! 🎨</code>",
        reply_markup=get_writing_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("timeline"))
async def command_timeline(message: Message):
    """Таймлайн жизни писателей"""
    await message.answer(
        "📅 <b>ТАЙМЛАЙН ЖИЗНИ ПИСАТЕЛЕЙ</b>\n\n"
        "<i>Исследуйте ключевые события жизни классиков</i>",
        reply_markup=get_timeline_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("books"))
async def command_books(message: Message):
    """Рекомендации книг"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    recommendations = book_recommendations.get_recommendations(
        user_data.get("conversation_history", []),
        user_data.get("book_preferences", [])
    )
    
    books_text = "📚 <b>ПЕРСОНАЛЬНЫЕ РЕКОМЕНДАЦИИ</b>\n\n"
    
    for i, rec in enumerate(recommendations[:5], 1):
        books_text += f"{i}. <b>{rec['title']}</b> - {rec['author']}\n"
        books_text += f"   <i>{rec['reason']}</i>\n\n"
    
    books_text += "<code>Выберите книгу для получения подробностей:</code>"
    
    await message.answer(
        books_text,
        reply_markup=get_book_recommendations_keyboard(recommendations[:5]),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("voice"))
async def command_voice(message: Message):
    """Голосовые ответы от авторов"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data.get("selected_author"):
        await message.answer(
            "⚠️ <b>Сначала выберите автора!</b>\n\n"
            "Используйте /start для выбора автора.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    author_key = user_data["selected_author"]
    author_names = {
        "pushkin": "Александр Пушкин",
        "dostoevsky": "Фёдор Достоевский",
        "tolstoy": "Лев Толстой",
        "gigachad": "💪 ГИГАЧАД"
    }
    author_name = author_names.get(author_key, "Писатель")
    
    # Получаем цитату для озвучки
    quote = daily_quotes.get_random_quote(author_key)
    
    # Показываем текст цитаты
    await message.answer(
        f"🎤 <b>ГОЛОСОВАЯ ЦИТАТА ОТ {author_name.upper()}</b>\n\n"
        f"<blockquote>«{quote['text']}»</blockquote>\n\n"
        f"<i>— {quote.get('work', 'Произведение')}</i>\n\n"
        f"<code>🔊 Аудио генерируется... (в разработке)</code>",
        parse_mode=ParseMode.HTML
    )
    
    # Здесь будет код генерации голосового сообщения
    # Пока отправляем текстовое объяснение
    await message.answer(
        "🎯 <b>ГОЛОСОВЫЕ ОТВЕТЫ (в разработке)</b>\n\n"
        "<i>Скоро авторы заговорят с вами!</i>\n\n"
        "🛠️ <b>Технологии:</b>\n"
        "• Yandex SpeechKit для синтеза речи\n"
        "• Индивидуальные голоса для каждого автора\n"
        "• Эмоциональное окрашивание речи\n\n"
        "<code>Следите за обновлениями! 🚀</code>"
    )

@router.message(Command("stats"))
async def command_stats(message: Message):
    """Статистика пользователя"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    stats_text = stats_service.format_user_stats(user_data, message.from_user.first_name)
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

@router.message(Command("quote"))
async def command_quote(message: Message):
    """Случайная цитата"""
    quote = daily_quotes.get_random_quote()
    
    quote_text = f"""
📖 <b>ЦИТАТА ДНЯ</b>
{'═' * 35}

<blockquote>«{quote['text']}»</blockquote>

<i>— {quote.get('work', 'Произведение')}</i>

{'═' * 35}
<code>✨ Вдохновляйтесь и читайте больше!</code>
"""
    
    await message.answer(quote_text, parse_mode=ParseMode.HTML)

@router.message(Command("achievements"))
async def command_achievements(message: Message):
    """Достижения пользователя"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    achievements_text = achievements_service.format_achievements(user_data)
    
    await message.answer(achievements_text, parse_mode=ParseMode.HTML)

# ========== ОБРАБОТЧИКИ INLINE-КНОПОК ==========

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Главное меню"""
    await callback.message.edit_text(
        "🎭 <b>ГЛАВНОЕ МЕНЮ</b>\n\n"
        "<i>Выберите действие:</i>",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "select_author")
async def callback_select_author(callback: CallbackQuery):
    """Выбор автора"""
    await callback.message.edit_text(
        "📚 <b>ВЫБЕРИТЕ АВТОРА</b>\n\n"
        "<i>С кем хотите побеседовать?</i>",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data.startswith("author_"))
async def callback_author_selected(callback: CallbackQuery):
    """Автор выбран"""
    author_key = callback.data.split("_")[1]
    
    author_names = {
        "pushkin": ("🖋️ Александр Пушкин", "Приветствую! О чём желаете побеседовать?"),
        "dostoevsky": ("📚 Фёдор Достоевский", "Здравствуйте. Что тревожит вашу душу?"),
        "tolstoy": ("✍️ Лев Толстой", "Здравствуйте. Говорите правду — я слушаю."),
        "gogol": ("👻 Николай Гоголь", "А, вот и вы! Что привело вас в мой мир?"),
        "chekhov": ("🏥 Антон Чехов", "Здравствуйте. Рассказывайте."),
        "gigachad": ("💪 ГИГАЧАД", f"СЛУШАЙ СЮДА, {callback.from_user.first_name.upper()}! Готов к вопросам! 💪")
    }
    
    author_name, greeting = author_names.get(author_key, ("Писатель", "Рад беседе!"))
    
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    user_data["selected_author"] = author_key
    user_data["conversation_history"] = []
    
    # Получаем цитату дня для этого автора
    quote = daily_quotes.get_daily_quote(author_key)
    
    response_text = f"""
{'═' * 35}
✅ <b>ВЫБРАН: {author_name}</b>
{'═' * 35}

{greeting}

📖 <b>ЦИТАТА ДНЯ ОТ АВТОРА:</b>
<blockquote>«{quote['text']}»</blockquote>
<i>— {quote.get('work', 'Произведение')}</i>

{'═' * 35}
👇 <b>Задавайте вопросы:</b>
"""
    
    await callback.message.edit_text(
        response_text,
        reply_markup=get_chat_keyboard(user_id, user_data.get("what_if_mode", False)),
        parse_mode=ParseMode.HTML
    )
    await callback.answer(f"Выбран: {author_name}")

@router.callback_query(F.data == "toggle_whatif")
async def callback_toggle_whatif(callback: CallbackQuery):
    """Переключение режима 'Что если...'"""
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    
    current_mode = user_data.get("what_if_mode", False)
    user_data["what_if_mode"] = not current_mode
    
    if not current_mode:
        await callback.message.answer(
            "🎭 <b>РЕЖИМ 'ЧТО ЕСЛИ...' ВКЛЮЧЁН!</b>\n\n"
            "<i>Теперь задавайте альтернативные вопросы!</i>\n\n"
            "Примеры:\n"
            "• Что если вы жили в наше время?\n"
            "• Что если вы писали в другом жанре?\n"
            "• Что если ваша жизнь сложилась иначе?\n\n"
            "<code>Исследуйте параллельные реальности! 🌌</code>"
        )
    else:
        await callback.message.answer(
            "👌 <b>Режим 'Что если...' отключён</b>\n\n"
            "<i>Возвращаемся к обычным вопросам</i>"
        )
    
    await callback.answer()

@router.callback_query(F.data == "start_writing")
async def callback_start_writing(callback: CallbackQuery):
    """Начало совместного письма"""
    user_id = callback.from_user.id
    
    await callback.message.edit_text(
        "✍️ <b>СОВМЕСТНОЕ ПИСЬМО</b>\n\n"
        "<i>Выберите автора для совместного творчества:</i>",
        reply_markup=get_authors_keyboard(writing_mode=True),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data.startswith("write_with_"))
async def callback_write_with_author(callback: CallbackQuery):
    """Письмо с конкретным автором"""
    author_key = callback.data.split("_")[2]
    
    author_names = {
        "pushkin": "Александром Пушкиным",
        "dostoevsky": "Фёдором Достоевским", 
        "tolstoy": "Львом Толстым",
        "gigachad": "💪 ГИГАЧАДОМ"
    }
    
    author_name = author_names.get(author_key, "писателем")
    
    # Сохраняем сессию письма
    writing_sessions[callback.from_user.id] = {
        "author": author_key,
        "text": "",
        "genre": "story",
        "turn": "user"  # Чья очередь писать
    }
    
    await callback.message.edit_text(
        f"✍️ <b>ПИШЕМ С {author_name.upper()}</b>\n\n"
        f"<i>Начните предложение, а автор продолжит за вас!</i>\n\n"
        "📝 <b>Пример начала:</b>\n"
        "'Однажды утром...'\n"
        "'В далёком царстве...'\n"
        "'Он никогда не думал, что...'\n\n"
        "<code>Напишите первое предложение:</code>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data.startswith("timeline_"))
async def callback_timeline(callback: CallbackQuery):
    """Показ таймлайна автора"""
    author_key = callback.data.split("_")[1]
    
    timeline_text = timeline_service.get_author_timeline(author_key)
    
    await callback.message.answer(
        timeline_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_timeline_keyboard(author_key)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("book_"))
async def callback_book_details(callback: CallbackQuery):
    """Детали книги"""
    book_id = callback.data.split("_")[1]
    book_info = book_recommendations.get_book_details(book_id)
    
    if book_info:
        # Здесь будет код для показа обложки книги
        # Пока отправляем текстовое описание
        await callback.message.answer(
            f"📚 <b>{book_info['title'].upper()}</b>\n\n"
            f"<b>Автор:</b> {book_info['author']}\n"
            f"<b>Год:</b> {book_info['year']}\n"
            f"<b>Жанр:</b> {book_info['genre']}\n\n"
            f"<b>Описание:</b>\n{book_info['description']}\n\n"
            f"<b>Почему рекомендуем:</b>\n{book_info['reason']}\n\n"
            f"<code>Читайте с удовольствием! 📖</code>",
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.answer("Книга не найдена", show_alert=True)
    
    await callback.answer()

@router.callback_query(F.data == "toggle_gigachad")
async def callback_toggle_gigachad(callback: CallbackQuery):
    """Переключение режима Гигачад"""
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    
    current_mode = user_data.get("gigachad_mode", False)
    user_data["gigachad_mode"] = not current_mode
    
    if not current_mode:
        await callback.message.answer(
            "💪 <b>РЕЖИМ ГИГАЧАД ВКЛЮЧЁН!</b>\n\n"
            "<i>Теперь ответы будут мотивационными!</i>\n\n"
            "<code>💥 Готовьтесь к прокачке!</code>"
        )
    else:
        await callback.message.answer(
            "👌 <b>Режим Гигачад отключён</b>"
        )
    
    await callback.answer()

@router.callback_query(F.data == "show_illustrations")
async def callback_show_illustrations(callback: CallbackQuery):
    """Показать иллюстрации"""
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    author_key = user_data.get("selected_author")
    
    if not author_key:
        await callback.answer("Сначала выберите автора", show_alert=True)
        return
    
    illustrations = {
        "pushkin": [
            ("Обложка 'Евгения Онегина'", "https://example.com/pushkin1.jpg"),
            ("Иллюстрация к 'Капитанской дочке'", "https://example.com/pushkin2.jpg"),
            ("Портрет Пушкина", "https://example.com/pushkin3.jpg")
        ],
        "dostoevsky": [
            ("Обложка 'Преступления и наказания'", "https://example.com/dost1.jpg"),
            ("Иллюстрация к 'Идиоту'", "https://example.com/dost2.jpg"),
            ("Портрет Достоевского", "https://example.com/dost3.jpg")
        ],
        "gigachad": [
            ("💪 Мотивационная картинка", "https://example.com/giga1.jpg"),
            ("🏋️ ГИГАЧАД в зале", "https://example.com/giga2.jpg"),
            ("📚 Книги + качалка", "https://example.com/giga3.jpg")
        ]
    }
    
    author_illustrations = illustrations.get(author_key, [])
    
    if not author_illustrations:
        await callback.answer("Иллюстрации не найдены", show_alert=True)
        return
    
    # Отправляем первую иллюстрацию как пример
    await callback.message.answer(
        f"🖼️ <b>ИЛЛЮСТРАЦИИ</b>\n\n"
        f"<i>Ссылки на изображения произведений:</i>\n\n"
        f"1. {author_illustrations[0][0]}\n"
        f"2. {author_illustrations[1][0]}\n"
        f"3. {author_illustrations[2][0]}\n\n"
        f"<code>🔗 Ссылки доступны в веб-версии</code>",
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer()

# ========== ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ ==========

@router.message(F.text)
async def handle_message(message: Message):
    """Обработка всех текстовых сообщений"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    # Проверяем, находится ли пользователь в режиме совместного письма
    if user_id in writing_sessions:
        await handle_writing_mode(message, user_id, user_data)
        return
    
    # Обычный режим диалога
    author_key = user_data.get("selected_author")
    
    if not author_key:
        await message.answer(
            "⚠️ <b>Сначала выберите писателя!</b>\n\n"
            "Используйте /start для выбора автора.",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    author_names = {
        "pushkin": "Александр Пушкин",
        "dostoevsky": "Фёдор Достоевский", 
        "tolstoy": "Лев Толстой",
        "gogol": "Николай Гоголь",
        "chekhov": "Антон Чехов",
        "gigachad": "💪 ГИГАЧАД"
    }
    
    author_name = author_names.get(author_key, "Писатель")
    
    # Показываем статус "печатает"
    status_text = f"✍️ {author_name} обдумывает ответ..."
    if user_data.get("what_if_mode"):
        status_text = f"🎭 {author_name} исследует альтернативную реальность..."
    elif user_data.get("gigachad_mode"):
        status_text = f"💪 {author_name} качает ответ..."
    
    status_msg = await message.answer(f"<i>{status_text}</i>", parse_mode=ParseMode.HTML)
    
    try:
        # Формируем промпт в зависимости от режима
        if user_data.get("what_if_mode"):
            user_message = f"Что если {message.text}"
        else:
            user_message = message.text
        
        # Генерируем ответ через GigaChat
        response = await gigachat_client.generate_response(
            author_key=author_key,
            author_name=author_name,
            user_message=user_message,
            conversation_history=user_data.get("conversation_history", []),
            gigachad_mode=user_data.get("gigachad_mode", False),
            what_if_mode=user_data.get("what_if_mode", False)
        )
        
        # Обновляем историю
        user_data["conversation_history"].append({
            "role": "user",
            "content": message.text,
            "timestamp": datetime.now().isoformat()
        })
        user_data["conversation_history"].append({
            "role": "assistant", 
            "content": response,
            "timestamp": datetime.now().isoformat()
        })
        user_data["message_count"] = user_data.get("message_count", 0) + 1
        user_data["last_active"] = datetime.now().isoformat()
        
        # Ограничиваем историю
        if len(user_data["conversation_history"]) > 10:
            user_data["conversation_history"] = user_data["conversation_history"][-10:]
        
        # Проверяем достижения
        new_achievements = achievements_service.check_new_achievements(user_id, user_data)
        
        # Удаляем статус
        await status_msg.delete()
        
        # Форматируем ответ
        emoji = "🎭" if user_data.get("what_if_mode") else "💪" if user_data.get("gigachad_mode") else "🖋️"
        
        response_text = f"""
{emoji} <b>{author_name.upper()}</b>
{'═' * 35}

{response}

{'═' * 35}
"""
        
        if new_achievements:
            response_text += "\n🏆 <b>НОВОЕ ДОСТИЖЕНИЕ!</b>\n"
            for ach in new_achievements:
                response_text += f"• {ach['name']}\n"
            response_text += f"\n{'═' * 35}\n"
        
        response_text += "\n👇 <b>Продолжить беседу?</b>"
        
        # Отправляем ответ
        await message.answer(
            response_text,
            reply_markup=get_chat_keyboard(user_id, user_data.get("what_if_mode", False)),
            parse_mode=ParseMode.HTML
        )
        
        # Обновляем предпочтения для рекомендаций книг
        book_recommendations.update_preferences(user_id, message.text, author_key)
        
        logger.info(f"💬 Сообщение: {user_id} -> {author_key} ({len(message.text)} chars)")
        
    except Exception as e:
        # Удаляем статус в случае ошибки
        try:
            await status_msg.delete()
        except:
            pass
        
        await message.answer(
            f"❌ <b>Ошибка:</b> {str(e)[:100]}\n\n"
            "Попробуйте перезапустить бота: /start",
            parse_mode=ParseMode.HTML
        )
        logger.error(f"Ошибка обработки сообщения: {e}")

async def handle_writing_mode(message: Message, user_id: int, user_data: dict):
    """Обработка сообщений в режиме совместного письма"""
    session = writing_sessions[user_id]
    author_key = session["author"]
    
    author_names = {
        "pushkin": "Александр Пушкин",
        "dostoevsky": "Фёдор Достоевский",
        "tolstoy": "Лев Толстой",
        "gigachad": "💪 ГИГАЧАД"
    }
    author_name = author_names.get(author_key, "Писатель")
    
    if session["turn"] == "user":
        # Пользователь пишет предложение
        session["text"] += message.text + " "
        session["turn"] = "author"
        
        # Показываем статус
        status_msg = await message.answer(f"✍️ <i>{author_name} продолжает вашу мысль...</i>", parse_mode=ParseMode.HTML)
        
        # Автор продолжает текст
        continuation = await gigachat_client.continue_writing(
            author_key=author_key,
            author_name=author_name,
            current_text=session["text"],
            genre=session["genre"]
        )
        
        session["text"] += continuation + " "
        session["turn"] = "user"
        
        # Удаляем статус
        await status_msg.delete()
        
        # Показываем результат
        await message.answer(
            f"✍️ <b>СОВМЕСТНОЕ ТВОРЧЕСТВО</b>\n\n"
            f"<b>Ваша часть:</b>\n<blockquote>{message.text}</blockquote>\n\n"
            f"<b>{author_name} продолжает:</b>\n<blockquote>{continuation}</blockquote>\n\n"
            f"<b>Полный текст:</b>\n<blockquote>{session['text'][:500]}...</blockquote>\n\n"
            f"<code>📝 Продолжайте писать или /stop_writing для завершения</code>",
            parse_mode=ParseMode.HTML
        )
        
    else:
        await message.answer("⏳ Автор ещё думает над продолжением...")

# ========== ЗАПУСК БОТА ==========

async def main():
    """Основная функция запуска"""
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    
    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК ЛИТЕРАТУРНОГО БОТА v3.0")
    logger.info(f"🤖 Бот: {BOT_TOKEN[:15]}...")
    logger.info(f"🔑 GigaChat: {'✅' if gigachat_client.available else '❌'}")
    logger.info("=" * 50)
    logger.info("✨ Новые фичи:")
    logger.info("• Голосовые ответы")
    logger.info("• Режим 'Что если...'")
    logger.info("• Совместное письмо")
    logger.info("• Иллюстрации книг")
    logger.info("• Таймлайн жизни")
    logger.info("• Рекомендации книг")
    logger.info("=" * 50)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
