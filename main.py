import asyncio
import logging
import sys
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.formatting import as_list, as_section, Bold, Italic, Text, as_key_value, Code

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
    get_book_recommendations_keyboard,
    get_voice_keyboard,
    get_illustrations_keyboard
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

# Хранилище пользователей
user_storage = {}
writing_sessions = {}

# ASCII-арты для оформления
ASCII_ART = {
    "welcome": """
╔═══════════════════════════════════════╗
║        🎭 ЛИТЕРАТУРНЫЙ САЛОН 🎭       ║
║           ВЕРСИЯ 4.0 ✨              ║
╚═══════════════════════════════════════╝
    """,
    "authors": """
╔═══════════════════════════════════════╗
║          📚 ВЕЛИКИЕ УМЫ 📚           ║
║       Выберите собеседника           ║
╚═══════════════════════════════════════╝
    """,
    "gigachad": """
╔═══════════════════════════════════════╗
║           💪 ГИГАЧАД MODE 💪         ║
║        МОТИВАЦИЯ + КЛАССИКА          ║
╚═══════════════════════════════════════╝
    """,
    "what_if": """
╔═══════════════════════════════════════╗
║          🎭 ЧТО ЕСЛИ... 🎭           ║
║      АЛЬТЕРНАТИВНЫЕ РЕАЛЬНОСТИ       ║
╚═══════════════════════════════════════╝
    """,
    "writing": """
╔═══════════════════════════════════════╗
║          ✍️ СОВМЕСТНОЕ ТВОРЧЕСТВО    ║
║        Пишем с классиками!           ║
╚═══════════════════════════════════════╝
    """,
    "timeline": """
╔═══════════════════════════════════════╗
║          📅 ТАЙМЛАЙН ЖИЗНИ 📅        ║
║      Ключевые события писателей      ║
╚═══════════════════════════════════════╝
    """
}

def get_user_data(user_id: int) -> dict:
    """Получает данные пользователя"""
    if user_id not in user_storage:
        user_storage[user_id] = {
            "selected_author": None,
            "conversation_history": [],
            "message_count": 0,
            "gigachad_mode": False,
            "what_if_mode": False,
            "achievements": [],
            "last_active": datetime.now().isoformat(),
            "book_preferences": [],
            "level": 1,
            "xp": 0,
            "created_at": datetime.now().isoformat(),
            "streak_days": 0
        }
    return user_storage[user_id]

def format_header(title: str, emoji: str = "") -> str:
    """Форматирует заголовок с рамкой"""
    border = "═" * 40
    return f"\n{border}\n{emoji} {title}\n{border}\n"

def format_quote(text: str, author: str = "") -> str:
    """Форматирует цитату красиво"""
    quote_lines = text.split('\n')
    formatted = ""
    for line in quote_lines:
        formatted += f"   {line}\n"
    
    if author:
        formatted += f"\n{'─' * 30}\n   👤 {author}"
    
    return formatted

def get_xp_bar(xp: int, level: int) -> str:
    """Создает прогресс-бар XP"""
    xp_needed = level * 100
    progress = min(xp / xp_needed * 100, 100)
    filled = int(progress / 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"[{bar}] {progress:.1f}%"

# Создаем роутер
router = Router()

# ========== КРАСИВЫЕ КОМАНДЫ ==========

@router.message(CommandStart())
async def command_start(message: Message):
    """Красивая команда /start"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    # Обновляем данные пользователя
    user_data.update({
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "last_active": datetime.now().isoformat()
    })
    
    # Проверяем достижения
    new_achievements = achievements_service.check_new_achievements(user_id, user_data)
    
    # Случайное приветствие
    greetings = [
        f"✨ Добро пожаловать в мир классики, {message.from_user.first_name}!",
        f"🎭 Рады видеть вас, {message.from_user.first_name}! Готовы к беседе с великими?",
        f"📚 Приветствуем, {message.from_user.first_name}! Откройте для себя магию литературы!"
    ]
    
    welcome_text = ASCII_ART["welcome"]
    welcome_text += f"\n{random.choice(greetings)}\n"
    welcome_text += format_header("🌟 НОВЫЕ ВОЗМОЖНОСТИ", "✨")
    welcome_text += """
🎤  Голосовые цитаты от авторов
🎭  Режим "Что если..." (альтернативные реальности)
✍️  Совместное письмо с классиками
🖼️  Галерея иллюстраций и обложек
📅  Интерактивные таймлайны жизни
📚  Умные рекомендации книг
💎  Система достижений и уровней
    """
    
    welcome_text += format_header("🎯 СЕГОДНЯШНИЕ ЗАДАНИЯ", "📋")
    welcome_text += """
•  Побеседовать с 2 разными авторами
•  Получить цитату дня
•  Попробовать режим "Что если..."
    """
    
    # Показываем новые достижения
    if new_achievements:
        welcome_text += format_header("🏆 НОВЫЕ ДОСТИЖЕНИЯ", "🎉")
        for ach in new_achievements:
            welcome_text += f"\n{ach['emoji']} {ach['name']}\n"
            welcome_text += f"   {ach['description']}\n"
    
    welcome_text += format_header("👇 ВЫБЕРИТЕ ДЕЙСТВИЕ", "🎮")
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    logger.info(f"👤 Пользователь: {user_id} (@{message.from_user.username})")

@router.message(Command("gigachad"))
async def command_gigachad(message: Message):
    """Красивая команда Гигачада"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    user_data.update({
        "selected_author": "gigachad",
        "gigachad_mode": True,
        "conversation_history": []
    })
    
    response_text = ASCII_ART["gigachad"]
    response_text += format_header("РЕЖИМ АКТИВИРОВАН", "💪")
    response_text += f"\n🎯 <b>{message.from_user.first_name.upper()}</b>, готов к прокачке!\n"
    response_text += format_header("🚀 ЧТО МОЖНО СПРОСИТЬ", "🔥")
    response_text += """
•  Как книги делают тебя сильнее?
•  В чём сила классики для мужчины?
•  Что Пушкин думал бы о качалке?
•  Как дисциплинировать себя книгами?
•  Литература + спорт = ?
    """
    response_text += format_header("💡 СОВЕТ ГИГАЧАДА", "⭐")
    response_text += "\nЗадавай вопрос — получай мотивацию!\nЧитай утром, думай днём, побеждай вечером! 🏆\n"
    
    await message.answer(
        response_text,
        reply_markup=get_chat_keyboard(user_id),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("profile"))
async def command_profile(message: Message):
    """Красивый профиль пользователя"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    # Рассчитываем уровень
    xp = user_data.get("xp", 0)
    level = user_data.get("level", 1)
    xp_needed = level * 100
    xp_bar = get_xp_bar(xp, level)
    
    # Статистика по авторам
    author_stats = {}
    for msg in user_data.get("conversation_history", []):
        if msg["role"] == "assistant":
            # Упрощённый анализ автора
            text = msg["content"].lower()
            if any(name in text for name in ["пушкин", "александр"]):
                author_stats["pushkin"] = author_stats.get("pushkin", 0) + 1
    
    profile_text = format_header("👤 ВАШ ПРОФИЛЬ", "📊")
    
    # Основная информация
    profile_text += f"""
<b>🎭 Имя:</b> {user_data.get('first_name', 'Читатель')}
<b>⭐ Уровень:</b> {level}
<b>🎯 Опыт:</b> {xp}/{xp_needed}
{bold("📈 Прогресс:")} {xp_bar}
"""
    
    profile_text += format_header("📊 СТАТИСТИКА", "💬")
    profile_text += f"""
<b>💬 Сообщений:</b> {user_data.get('message_count', 0)}
<b>📅 На сайте с:</b> {datetime.fromisoformat(user_data['created_at']).strftime('%d.%m.%Y')}
<b>🔥 Дней подряд:</b> {user_data.get('streak_days', 0)}
"""
    
    # Активность по авторам
    if author_stats:
        profile_text += format_header("🎭 ЛЮБИМЫЕ АВТОРЫ", "❤️")
        for author, count in sorted(author_stats.items(), key=lambda x: x[1], reverse=True)[:3]:
            author_names = {
                "pushkin": "🖋️ Пушкин",
                "dostoevsky": "📚 Достоевский",
                "tolstoy": "✍️ Толстой",
                "gigachad": "💪 ГИГАЧАД"
            }
            name = author_names.get(author, author)
            percentage = (count / user_data.get('message_count', 1)) * 100
            bar = "█" * int(percentage / 10) + "░" * (10 - int(percentage / 10))
            profile_text += f"\n{name}: {bar} {percentage:.0f}%"
    
    profile_text += format_header("🏆 БЛИЖАЙШИЕ ЦЕЛИ", "🎯")
    profile_text += f"""
🎯 Уровень {level + 1} ({xp_needed - xp} XP до цели)
💬 {100 - user_data.get('message_count', 0)} сообщений до 100
📚 Побеседовать с 5 авторами
"""
    
    await message.answer(profile_text, parse_mode=ParseMode.HTML)

@router.message(Command("quote"))
async def command_quote(message: Message):
    """Красивая цитата дня"""
    quote = daily_quotes.get_random_quote()
    
    # Случайный стиль оформления
    styles = [
        ("📖 ЦИТАТА ДНЯ", "✨"),
        ("💫 ЖЕМЧУЖИНА МУДРОСТИ", "🌟"),
        ("🎭 СЛОВА ВЕЛИКИХ", "📚")
    ]
    title, emoji = random.choice(styles)
    
    quote_text = format_header(title, emoji)
    quote_text += format_quote(quote['text'], quote.get('work', 'Произведение'))
    quote_text += format_header("✨ ВДОХНОВЛЯЙТЕСЬ", "💎")
    quote_text += "\nКаждая прочитанная книга делает вас лучше!\n"
    
    await message.answer(quote_text, parse_mode=ParseMode.HTML)

@router.message(Command("daily"))
async def command_daily(message: Message):
    """Ежедневные задания"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    daily_text = format_header("📅 ЕЖЕДНЕВНЫЕ ЗАДАНИЯ", "🎯")
    
    # Генерируем случайные задания
    tasks = [
        "Побеседовать с Пушкиным о любви",
        "Спросить Достоевского о смысле жизни",
        "Активировать режим Гигачад",
        "Получить цитату дня",
        "Попробовать режим 'Что если...'",
        "Начать совместное письмо"
    ]
    
    daily_tasks = random.sample(tasks, 3)
    
    for i, task in enumerate(daily_tasks, 1):
        daily_text += f"\n{i}. ✅ {task}"
    
    # Награды
    daily_text += format_header("🏆 НАГРАДЫ ЗА ВЫПОЛНЕНИЕ", "💎")
    daily_text += """
•  +50 XP за каждое задание
•  +150 XP за все задания
•  Специальное достижение
•  Увеличение уровня
"""
    
    # Прогресс
    daily_text += format_header("📊 ВАШ ПРОГРЕСС", "⭐")
    daily_text += f"""
🎯 Выполнено: 0/3 заданий
⭐ Получено XP: 0
🔥 Серия выполнения: 0 дней
"""
    
    daily_text += format_header("💡 СОВЕТ", "✨")
    daily_text += "\nВыполняйте задания ежедневно для быстрого роста!\n"
    
    await message.answer(daily_text, parse_mode=ParseMode.HTML)

# ========== КРАСИВЫЕ CALLBACK ОБРАБОТЧИКИ ==========

@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Главное меню с красивым оформлением"""
    menu_text = format_header("🎭 ГЛАВНОЕ МЕНЮ", "✨")
    menu_text += """
🏠  Добро пожаловать в центр управления!

Выберите раздел для продолжения:
"""
    
    await callback.message.edit_text(
        menu_text,
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "select_author")
async def callback_select_author(callback: CallbackQuery):
    """Красивый выбор автора"""
    authors_text = ASCII_ART["authors"]
    authors_text += format_header("ВЫБЕРИТЕ СОБЕСЕДНИКА", "👥")
    authors_text += """
Каждый автор обладает уникальным стилем:

🖋️  <b>Пушкин</b> — романтичный и остроумный
📚  <b>Достоевский</b> — глубокий философ
✍️  <b>Толстой</b> — мудрый наставник
👻  <b>Гоголь</b> — ироничный мистик
🏥  <b>Чехов</b> — лаконичный наблюдатель
💪  <b>ГИГАЧАД</b> — мотивационный эксперт
"""
    authors_text += format_header("💡 СОВЕТ", "🌟")
    authors_text += "\nНачните с того автора, чьи произведения вам ближе!\n"
    
    await callback.message.edit_text(
        authors_text,
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data.startswith("author_"))
async def callback_author_selected(callback: CallbackQuery):
    """Красивый выбор автора"""
    author_key = callback.data.split("_")[1]
    
    author_info = {
        "pushkin": {
            "name": "🖋️ Александр Пушкин",
            "greeting": "Приветствую вас, друг мой! О чём желаете побеседовать?",
            "fact": "Автор более 800 стихотворений и создатель современного русского языка",
            "emoji": "✨"
        },
        "dostoevsky": {
            "name": "📚 Фёдор Достоевский",
            "greeting": "Здравствуйте. Что тревожит вашу душу сегодня?",
            "fact": "Пережил инсценировку казни и 4 года каторги",
            "emoji": "🌀"
        },
        "tolstoy": {
            "name": "✍️ Лев Толстой",
            "greeting": "Здравствуйте. Говорите правду — я слушаю.",
            "fact": "В 82 года ушёл из дома, чтобы жить в простоте",
            "emoji": "🌳"
        },
        "gigachad": {
            "name": "💪 ГИГАЧАД",
            "greeting": f"СЛУШАЙ СЮДА, {callback.from_user.first_name.upper()}! ГОТОВ К ВОПРОСАМ! 💪",
            "fact": "Считает, что каждая прочитанная книга — +10 к силе характера",
            "emoji": "🏋️"
        }
    }
    
    info = author_info.get(author_key, author_info["pushkin"])
    
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    user_data.update({
        "selected_author": author_key,
        "conversation_history": []
    })
    
    # Получаем цитату дня
    quote = daily_quotes.get_daily_quote(author_key)
    
    # Форматируем ответ
    response_text = format_header(info["name"], info["emoji"])
    response_text += f"\n{info['greeting']}\n"
    
    response_text += format_header("💎 ИНТЕРЕСНЫЙ ФАКТ", "✨")
    response_text += f"\n{info['fact']}\n"
    
    response_text += format_header("📖 ЦИТАТА ДНЯ ОТ АВТОРА", "⭐")
    response_text += format_quote(quote['text'], quote.get('work', 'Произведение'))
    
    response_text += format_header("🎯 ЧТО МОЖНО СПРОСИТЬ", "💡")
    response_text += """
•  О жизни и творчестве
•  О философских взглядах
•  О любимых произведениях
•  О современности
•  О чём угодно!
"""
    
    response_text += format_header("👇 НАЧИНАЙТЕ БЕСЕДУ", "💬")
    
    await callback.message.edit_text(
        response_text,
        reply_markup=get_chat_keyboard(user_id),
        parse_mode=ParseMode.HTML
    )
    await callback.answer(f"Выбран: {info['name']}")

@router.callback_query(F.data == "toggle_gigachad")
async def callback_toggle_gigachad(callback: CallbackQuery):
    """Красивое переключение режима"""
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    
    current_mode = user_data.get("gigachad_mode", False)
    user_data["gigachad_mode"] = not current_mode
    
    if not current_mode:
        response_text = format_header("💪 РЕЖИМ ГИГАЧАД АКТИВИРОВАН", "🎉")
        response_text += """
🎯 Теперь все ответы будут:

•  Мотивационными и уверенными
•  Краткими и по делу
•  Связывающими литературу с жизнью
•  С мемной, но умной харизмой

🔥 Пример ответа:
"Слушай сюда! Книги — это железо для мозга!
Читай каждый день как делаешь подходы в зале!"
"""
    else:
        response_text = format_header("👌 РЕЖИМ ГИГАЧАД ОТКЛЮЧЁН", "✅")
        response_text += "\nВозвращаемся к обычному стилю общения.\n"
    
    await callback.message.answer(response_text, parse_mode=ParseMode.HTML)
    await callback.answer()

# ========== КРАСИВЫЙ ОБРАБОТЧИК СООБЩЕНИЙ ==========

@router.message(F.text)
async def handle_message(message: Message):
    """Красивый обработчик сообщений"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    # Проверка автора
    author_key = user_data.get("selected_author")
    if not author_key:
        error_text = format_header("⚠️ ВНИМАНИЕ", "🎭")
        error_text += "\nСначала выберите автора для беседы!\n"
        error_text += format_header("🎯 КАК ЭТО СДЕЛАТЬ", "👉")
        error_text += "\nИспользуйте кнопку ниже или команду /start\n"
        
        await message.answer(
            error_text,
            reply_markup=get_main_menu_keyboard(),
            parse_mode=ParseMode.HTML
        )
        return
    
    # Имя автора
    author_names = {
        "pushkin": ("Александр Пушкин", "🖋️"),
        "dostoevsky": ("Фёдор Достоевский", "📚"),
        "tolstoy": ("Лев Толстой", "✍️"),
        "gogol": ("Николай Гоголь", "👻"),
        "chekhov": ("Антон Чехов", "🏥"),
        "gigachad": ("💪 ГИГАЧАД", "💪")
    }
    author_name, author_emoji = author_names.get(author_key, ("Писатель", "🎭"))
    
    # Статус "печатает"
    status_messages = {
        "pushkin": f"{author_emoji} Пушкин обдумывает ответ...",
        "dostoevsky": f"{author_emoji} Достоевский погружается в размышления...",
        "tolstoy": f"{author_emoji} Толстой размышляет мудро...",
        "gogol": f"{author_emoji} Гоголь создаёт образ...",
        "chekhov": f"{author_emoji} Чехов формулирует мысль...",
        "gigachad": f"{author_emoji} ГИГАЧАД качает ответ..."
    }
    
    status_text = status_messages.get(author_key, f"{author_emoji} Автор думает...")
    
    # Показываем анимированный статус
    dots = ["", ".", "..", "..."]
    for i in range(3):
        status_msg = await message.answer(f"<i>{status_text}{dots[i]}</i>", parse_mode=ParseMode.HTML)
        await asyncio.sleep(0.5)
        if i < 2:
            await status_msg.delete()
    
    try:
        # Генерируем ответ
        response = await gigachat_client.generate_response(
            author_key=author_key,
            author_name=author_name,
            user_message=message.text,
            conversation_history=user_data.get("conversation_history", []),
            gigachad_mode=user_data.get("gigachad_mode", False),
            what_if_mode=user_data.get("what_if_mode", False)
        )
        
        # Обновляем данные
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
        user_data["xp"] = user_data.get("xp", 0) + 10
        user_data["last_active"] = datetime.now().isoformat()
        
        # Проверяем уровень
        if user_data["xp"] >= user_data["level"] * 100:
            user_data["level"] += 1
            user_data["xp"] = 0
        
        # Ограничиваем историю
        if len(user_data["conversation_history"]) > 10:
            user_data["conversation_history"] = user_data["conversation_history"][-10:]
        
        # Проверяем достижения
        new_achievements = achievements_service.check_new_achievements(user_id, user_data)
        
        # Удаляем последний статус
        await status_msg.delete()
        
        # Форматируем ответ
        response_header = format_header(f"{author_emoji} {author_name.upper()}", "💬")
        
        # Разбиваем ответ на абзацы для лучшего форматирования
        response_paragraphs = response.split('\n')
        formatted_response = ""
        for para in response_paragraphs:
            if para.strip():
                formatted_response += f"   {para}\n"
        
        response_text = response_header + "\n" + formatted_response
        
        # Добавляем разделитель
        response_text += f"\n{'─' * 40}\n"
        
        # Показываем новые достижения
        if new_achievements:
            response_text += format_header("🏆 НОВОЕ ДОСТИЖЕНИЕ", "🎉")
            for ach in new_achievements:
                response_text += f"\n{ach['emoji']} <b>{ach['name']}</b>\n"
                response_text += f"   {ach['description']}\n"
            response_text += f"\n{'─' * 40}\n"
        
        # Добавляем статистику
        response_text += f"⭐ <b>Уровень:</b> {user_data.get('level', 1)} | "
        response_text += f"🎯 <b>XP:</b> {user_data.get('xp', 0)}/{user_data.get('level', 1)*100}\n"
        response_text += f"💬 <b>Сообщений:</b> {user_data.get('message_count', 0)}\n"
        
        # Кнопка продолжения
        response_text += format_header("👇 ПРОДОЛЖИТЬ БЕСЕДУ", "💭")
        
        # Отправляем ответ
        await message.answer(
            response_text,
            reply_markup=get_chat_keyboard(user_id, user_data.get("what_if_mode", False)),
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"💬 {user_id} -> {author_key}: {len(message.text)} chars")
        
    except Exception as e:
        # Удаляем статус в случае ошибки
        try:
            await status_msg.delete()
        except:
            pass
        
        error_text = format_header("❌ ОШИБКА", "⚠️")
        error_text += f"\nНе удалось получить ответ:\n<code>{str(e)[:100]}</code>\n"
        error_text += format_header("🎯 ЧТО ДЕЛАТЬ", "👉")
        error_text += "\n1. Попробуйте переформулировать вопрос\n"
        error_text += "2. Используйте /start для перезагрузки\n"
        error_text += "3. Подождите несколько минут\n"
        
        await message.answer(error_text, parse_mode=ParseMode.HTML)
        logger.error(f"Ошибка: {e}")

# ========== СПЕЦИАЛЬНЫЕ КОМАНДЫ С ОФОРМЛЕНИЕМ ==========

@router.message(Command("whatif"))
async def command_whatif(message: Message):
    """Красивый режим 'Что если...'"""
    whatif_text = ASCII_ART["what_if"]
    whatif_text += format_header("ИССЛЕДУЙТЕ АЛЬТЕРНАТИВНЫЕ РЕАЛЬНОСТИ", "🌌")
    whatif_text += """
🎭 Что было бы, если...

•  Пушкин жил в 21 веке?
•  Достоевский писал детективы?
•  Толстой был IT-предпринимателем?
•  Гоголь создавал комиксы?
•  Чехов вёл медицинский блог?
"""
    whatif_text += format_header("🎯 КАК РАБОТАЕТ", "⚡")
    whatif_text += """
1. Выберите автора
2. Задайте вопрос "Что если..."
3. Получите творческий ответ!
"""
    whatif_text += format_header("💡 ПРИМЕРЫ ВОПРОСОВ", "✨")
    whatif_text += """
"Что если бы вы жили в наше время?"
"Что если бы ваши герои встретились?"
"Что если бы вы писали в другом жанре?"
"""
    whatif_text += format_header("👇 НАЧНИТЕ ИССЛЕДОВАНИЕ", "🚀")
    
    await message.answer(
        whatif_text,
        reply_markup=get_what_if_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("write"))
async def command_write(message: Message):
    """Красивый режим совместного письма"""
    write_text = ASCII_ART["writing"]
    write_text += format_header("СОЗДАЙТЕ ШЕДЕВР ВМЕСТЕ С КЛАССИКОМ", "✍️")
    write_text += """
🎨 Вы — автор, классик — соавтор!

Как это работает:
1. Вы начинаете предложение
2. Автор продолжает в своём стиле
3. Вы вместе создаёте текст
4. Сохраняете результат
"""
    write_text += format_header("🎭 ВЫБЕРИТЕ ЖАНР", "📖")
    write_text += """
📚  Роман — глубокое повествование
🎭  Драма — эмоциональный диалог
✨  Поэзия — рифмованные строки
🌀  Фэнтези — магические миры
🔍  Детектив — загадочный сюжет
"""
    write_text += format_header("💡 ПРИМЕРЫ НАЧАЛА", "🌟")
    write_text += """
•  "Однажды утром он проснулся и..."
•  "В далёком царстве, где..."
•  "Она никогда не думала, что..."
•  "Тайна старого дома заключалась в..."
"""
    write_text += format_header("👇 НАЧНИТЕ ТВОРИТЬ", "🎨")
    
    await message.answer(
        write_text,
        reply_markup=get_writing_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("timeline"))
async def command_timeline(message: Message):
    """Красивый таймлайн"""
    timeline_text = ASCII_ART["timeline"]
    timeline_text += format_header("ПУТЕШЕСТВИЕ ПО ВРЕМЕНИ", "⏳")
    timeline_text += """
📅 Изучите ключевые моменты жизни великих писателей:

•  Детство и юность
•  Первые произведения
•  Значимые события
•  Творческие периоды
•  Наследие
"""
    timeline_text += format_header("🎯 ЧТО УЗНАЕТЕ", "🔍")
    timeline_text += """
✨  Как формировался талант
📚  Когда написаны великие книги
💫  Что повлияло на творчество
🌟  Интересные факты из жизни
"""
    timeline_text += format_header("👇 ВЫБЕРИТЕ АВТОРА", "👥")
    
    await message.answer(
        timeline_text,
        reply_markup=get_timeline_keyboard(),
        parse_mode=ParseMode.HTML
    )

# ========== ЗАПУСК БОТА ==========

async def main():
    """Красивый запуск бота"""
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    
    # Красивое сообщение о запуске
    startup_text = """
╔══════════════════════════════════════════════════╗
║            🚀 ЛИТЕРАТУРНЫЙ БОТ v4.0 🚀          ║
║                УСПЕШНО ЗАПУЩЕН!                 ║
╚══════════════════════════════════════════════════╝
    
✨ <b>Версия:</b> 4.0 (Премиум оформление)
🎭 <b>Авторов:</b> 6 классиков + ГИГАЧАД
💎 <b>Особенности:</b> Анимации, прогресс-бары, ASCII-арт
🚀 <b>Статус:</b> Готов к работе!
"""
    
    logger.info("\n" + "=" * 60)
    logger.info("🎭 ЗАПУСК ЛИТЕРАТУРНОГО БОТА v4.0")
    logger.info(f"🤖 Бот: {BOT_TOKEN[:15]}...")
    logger.info(f"🔑 GigaChat: {'✅ Активен' if gigachat_client.available else '❌ Недоступен'}")
    logger.info("✨ Особенности: Красивое оформление, анимации, прогресс-бары")
    logger.info("=" * 60)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n" + "=" * 60)
        logger.info("⏹️  Бот остановлен пользователем")
        logger.info("=" * 60)
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}")
