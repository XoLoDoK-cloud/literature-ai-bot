#!/usr/bin/env python3
# ========== ЛИТЕРАТУРНЫЙ ДИАЛОГ БОТ ==========

import asyncio
import logging
import sys
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверяем токен
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден в .env файле!")
    print("Создайте файл .env с BOT_TOKEN=ваш_токен")
    exit(1)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Импорты из наших модулей
try:
    from services.database import db
    from services.literary_ai import LiteraryAI
    from services.formatters import bold, italic, code, create_header
    logger.info("✅ Все модули успешно импортированы")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта модулей: {e}")
    logger.error("Убедитесь, что все файлы в папке services/")
    exit(1)

# Инициализация литературного ИИ
literary_ai = LiteraryAI()

# Создаем роутер
router = Router()

# ========== ДАННЫЕ О ПИСАТЕЛЯХ ==========
AUTHORS = {
    "pushkin": {
        "name": "Александр Пушкин",
        "emoji": "🖋️",
        "birth": "1799-1837",
        "description": "Великий русский поэт",
        "style": "Поэтичный, изящный, романтичный",
        "greeting": "Здравствуйте! Рад нашей беседе. Что желаете узнать?"
    },
    "dostoevsky": {
        "name": "Фёдор Достоевский", 
        "emoji": "📚",
        "birth": "1821-1881",
        "description": "Великий русский писатель",
        "style": "Глубокий, философский, психологичный",
        "greeting": "Здравствуйте. Что тревожит вашу душу?"
    },
    "tolstoy": {
        "name": "Лев Толстой",
        "emoji": "✍️", 
        "birth": "1828-1910",
        "description": "Великий русский писатель",
        "style": "Мудрый, простой, нравственный",
        "greeting": "Здравствуйте, друг мой. Поговорим о важном?"
    },
    "gogol": {
        "name": "Николай Гоголь",
        "emoji": "👻",
        "birth": "1809-1852",
        "description": "Русский прозаик и драматург",
        "style": "Ироничный, гротескный, сатиричный",
        "greeting": "А, вот и вы! Любопытно, что вы хотите узнать?"
    },
    "chekhov": {
        "name": "Антон Чехов",
        "emoji": "🏥",
        "birth": "1860-1904", 
        "description": "Русский писатель и врач",
        "style": "Лаконичный, точный, наблюдательный",
        "greeting": "Здравствуйте. Рассказывайте."
    },
    "gigachad": {
        "name": "ГИГАЧАД",
        "emoji": "💪",
        "birth": "Легенда",
        "description": "Мотивационный эксперт",
        "style": "Энергичный, мотивирующий, прямолинейный",
        "greeting": "СЛУШАЙ СЮДА! Готов к диалогу! 🔥"
    }
}

# ========== КРАСИВЫЕ КЛАВИАТУРЫ ==========
def get_main_keyboard():
    """Главная клавиатура выбора автора"""
    keyboard = [
        [
            InlineKeyboardButton(text="🖋️ Пушкин", callback_data="author_pushkin"),
            InlineKeyboardButton(text="📚 Достоевский", callback_data="author_dostoevsky"),
            InlineKeyboardButton(text="✍️ Толстой", callback_data="author_tolstoy")
        ],
        [
            InlineKeyboardButton(text="👻 Гоголь", callback_data="author_gogol"),
            InlineKeyboardButton(text="🏥 Чехов", callback_data="author_chekhov"),
            InlineKeyboardButton(text="💪 ГИГАЧАД", callback_data="author_gigachad")
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
            InlineKeyboardButton(text="📊 Моя статистика", callback_data="stats")
        ],
        [
            InlineKeyboardButton(text="ℹ️ О проекте", callback_data="about")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_chat_keyboard(author_key: str = None):
    """Клавиатура во время диалога"""
    keyboard = [
        [
            InlineKeyboardButton(text="🔄 Новый диалог", callback_data="new_chat"),
            InlineKeyboardButton(text="👥 Сменить автора", callback_data="change_author")
        ],
        [
            InlineKeyboardButton(text="📖 Об авторе", callback_data="about_author"),
            InlineKeyboardButton(text="📚 Все писатели", callback_data="all_authors")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    # Если автор выбран, добавляем заголовок
    if author_key and author_key in AUTHORS:
        author = AUTHORS[author_key]
        keyboard.insert(0, [
            InlineKeyboardButton(
                text=f"💬 Диалог с {author['emoji']} {author['name'].split()[0]}",
                callback_data="current_chat"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_help_keyboard():
    """Клавиатура для помощи"""
    keyboard = [
        [
            InlineKeyboardButton(text="🎭 Выбрать автора", callback_data="choose_author"),
            InlineKeyboardButton(text="📚 Список писателей", callback_data="all_authors")
        ],
        [
            InlineKeyboardButton(text="💬 Начать диалог", callback_data="new_chat"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ========== КРАСИВЫЕ ФОРМАТИРОВАНИЯ ==========
def format_welcome_message(user_name: str) -> str:
    """Форматирует приветственное сообщение"""
    return f"""
✨ {bold('ЛИТЕРАТУРНЫЙ ДИАЛОГ')} ✨

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

👋 {bold(f'Добро пожаловать, {user_name}!')}

🎭 {italic('Погрузитесь в мир русской классической литературы')}

💭 {bold('Задайте вопрос любому писателю и получите ответ в его уникальном стиле!')}

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

👇 {bold('Выберите писателя для диалога:')}
"""

def format_author_selection(author: dict, user_name: str) -> str:
    """Форматирует сообщение о выборе автора"""
    return f"""
{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

✨ {bold('АВТОР ВЫБРАН')} ✨

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

{author['emoji']} {bold(author['name'])}
{italic(author['birth'])} • {author['description']}

{code('──────────────────────────────')}

🎭 {bold('Стиль общения:')}
{italic(author['style'])}

{code('──────────────────────────────')}

💬 {bold('Приветствие:')}
{author['greeting']}

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

{code('💡 Теперь вы можете задавать вопросы!')}
"""

def format_author_response(author: dict, response: str) -> str:
    """Форматирует ответ автора"""
    return f"""
{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

{author['emoji']} {bold(author['name'].split()[0])}:
{response}

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

{code('💭 Продолжайте диалог или используйте кнопки ниже')}
"""

def format_no_author_message(user_name: str) -> str:
    """Форматирует сообщение при отсутствии выбранного автора"""
    return f"""
{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

🎭 {bold('ВЫБОР СОБЕСЕДНИКА')}

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

👋 {bold(f'{user_name}, чтобы начать диалог,')}
{bold('выберите писателя из списка:')}

{code('──────────────────────────────')}

🖋️ {bold('Александр Пушкин')}
{italic('Поэтичный и изящный стиль')}

📚 {bold('Фёдор Достоевский')}
{italic('Глубокий и философский')}

✍️ {bold('Лев Толстой')}
{italic('Мудрый и простой')}

👻 {bold('Николай Гоголь')}
{italic('Ироничный и сатиричный')}

🏥 {bold('Антон Чехов')}
{italic('Лаконичный и точный')}

💪 {bold('ГИГАЧАД')}
{italic('Энергичный и мотивирующий')}

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

{code('✨ Просто нажмите на кнопку с именем автора!')}
"""

# ========== КОМАНДЫ ==========
@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        
        # Создаем или получаем данные пользователя
        user_data = db.get_user_data(user_id)
        user_data["username"] = message.from_user.username
        user_data["first_name"] = user_name
        db.save_user_data(user_id, user_data)
        
        await message.answer(
            format_welcome_message(user_name),
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_keyboard()
        )
        
        logger.info(f"✅ Старт: {user_id} (@{message.from_user.username})")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в /start: {e}")
        await message.answer(
            "Произошла ошибка при запуске. Попробуйте позже.",
            parse_mode=ParseMode.HTML
        )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = f"""
{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

📚 {bold('ПОМОЩЬ')} 🎭

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

✨ {bold('Как использовать бота:')}

1️⃣ {bold('Выберите писателя')}
   • Нажмите на кнопку с именем автора
   • Каждый имеет уникальный стиль общения

2️⃣ {bold('Задавайте вопросы')}
   • О литературе и творчестве
   • О жизни и философии
   • О любых интересующих темах

3️⃣ {bold('Управляйте диалогом')}
   • 🔄 Новый диалог — начать разговор заново
   • 👥 Сменить автора — выбрать нового писателя
   • 📖 Об авторе — узнать больше о писателе

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

📋 {bold('Доступные команды:')}
• /start — начать диалог
• /help — помощь
• /authors — список писателей
• /stats — ваша статистика

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

{code('🎭 Приятного общения с классиками!')}
"""
    await message.answer(
        help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_help_keyboard()
    )

@router.message(Command("authors"))
async def cmd_authors(message: Message):
    """Список авторов"""
    authors_text = f"""
{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

👥 {bold('ВСЕ ПИСАТЕЛИ')} 📚

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

✨ {bold('Доступные для диалога:')}

{code('──────────────────────────────')}

🖋️ {bold('Александр Пушкин')}
{italic('1799-1837 • Великий русский поэт')}

📚 {bold('Фёдор Достоевский')}
{italic('1821-1881 • Философ и писатель')}

✍️ {bold('Лев Толстой')}
{italic('1828-1910 • Мыслитель и прозаик')}

👻 {bold('Николай Гоголь')}
{italic('1809-1852 • Мастер сатиры')}

🏥 {bold('Антон Чехов')}
{italic('1860-1904 • Писатель и врач')}

💪 {bold('ГИГАЧАД')}
{italic('Легенда • Мотивационный эксперт')}

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

{code('✨ Выберите автора для начала диалога!')}
"""
    await message.answer(
        authors_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard()
    )

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика пользователя"""
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_data = db.get_user_data(user_id)
    
    stats_text = f"""
{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

📊 {bold('ВАША СТАТИСТИКА')} ✨

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

👤 {bold('Пользователь:')} {user_name}
🆔 {bold('ID:')} {code(str(user_id))}

{code('──────────────────────────────')}

📈 {bold('Активность:')}
💬 {bold('Всего сообщений:')} {user_data.get('message_count', 0)}
🗓️ {bold('Дата регистрации:')} {user_data.get('created_at', 'Неизвестно')[:10]}

{code('──────────────────────────────')}

🎭 {bold('Текущий собеседник:')}
"""
    
    author_key = user_data.get('selected_author')
    if author_key and author_key in AUTHORS:
        author = AUTHORS[author_key]
        stats_text += f"{author['emoji']} {bold(author['name'])}"
    else:
        stats_text += italic("Автор не выбран")
    
    stats_text += f"""

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

{code('🎯 Продолжайте общение для новых достижений!')}
"""
    
    await message.answer(
        stats_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard()
    )

# ========== ОБРАБОТЧИКИ КНОПОК ==========
@router.callback_query(F.data.startswith("author_"))
async def author_selected_callback(callback: CallbackQuery):
    """Выбор конкретного автора"""
    try:
        author_key = callback.data.split("_")[1]
        
        if author_key not in AUTHORS:
            await callback.answer("Автор не найден")
            return
        
        author = AUTHORS[author_key]
        user_id = callback.from_user.id
        user_name = callback.from_user.first_name
        
        # Сохраняем выбор в базе
        user_data = db.get_user_data(user_id)
        user_data["selected_author"] = author_key
        db.save_user_data(user_id, user_data)
        
        await callback.message.edit_text(
            format_author_selection(author, user_name),
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard(author_key)
        )
        
        await callback.answer(f"Выбран: {author['name'].split()[0]}")
        logger.info(f"✅ Выбор автора: {user_id} → {author_key}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в выборе автора: {e}")
        await callback.answer("Ошибка выбора автора")

@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    """Обработчик кнопки помощи"""
    await cmd_help(callback.message)
    await callback.answer("📚 Помощь")

@router.callback_query(F.data == "about")
async def about_callback(callback: CallbackQuery):
    """О проекте"""
    about_text = f"""
{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

ℹ️ {bold('О ПРОЕКТЕ')} ✨

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

🎭 {bold('Литературный Диалог')}

💭 {italic('Уникальный проект для общения с русскими классиками')}

✨ {bold('Возможности:')}
• 🗣️ Беседа с великими писателями
• 📚 Ответы в характерном стиле каждого автора
• 💾 Сохранение истории диалогов
• 🎭 Уникальные личности классиков

{code('──────────────────────────────')}

📖 {bold('Цель проекта:')}
{italic('Сделать классическую литературу ближе и понятнее')}
{italic('через интерактивное общение с писателями')}

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

{code('🎨 Разработано с любовью к литературе')}
{code('📚 Приятного общения с классиками!')}
"""
    await callback.message.answer(
        about_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard()
    )
    await callback.answer("ℹ️ О проекте")

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    """Возврат в главное меню"""
    await cmd_start(callback.message)
    await callback.answer("🏠 Главное меню")

@router.callback_query(F.data == "change_author")
async def change_author_callback(callback: CallbackQuery):
    """Смена автора"""
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name
    
    change_text = f"""
{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

👥 {bold('СМЕНА АВТОРА')} ✨

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

👋 {bold(f'{user_name}, выберите нового собеседника:')}

{code('──────────────────────────────')}

💡 {italic('Каждый автор имеет свой уникальный стиль:')}
• 🖋️ Пушкин — поэтичный и изящный
• 📚 Достоевский — глубокий и философский
• ✍️ Толстой — мудрый и простой
• 👻 Гоголь — ироничный и сатиричный
• 🏥 Чехов — лаконичный и точный
• 💪 ГИГАЧАД — энергичный и мотивирующий

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

{code('🎭 Выберите автора для продолжения диалога!')}
"""
    
    await callback.message.edit_text(
        change_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard()
    )
    await callback.answer("👥 Смена автора")

@router.callback_query(F.data == "new_chat")
async def new_chat_callback(callback: CallbackQuery):
    """Новый диалог"""
    user_id = callback.from_user.id
    user_name = callback.from_user.first_name
    db.reset_conversation(user_id)
    
    new_chat_text = f"""
{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

🔄 {bold('НОВЫЙ ДИАЛОГ')} ✨

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

✅ {bold('История диалога очищена!')}

{code('──────────────────────────────')}

👋 {bold(f'{user_name}, теперь вы можете начать')}
{bold('совершенно новый диалог!')}

🎭 {italic('Выберите автора и задайте первый вопрос')}

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

{code('💡 Совет: Попробуйте нового автора!')}
"""
    
    await callback.message.edit_text(
        new_chat_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_keyboard()
    )
    await callback.answer("🔄 Новый диалог")

@router.callback_query(F.data == "about_author")
async def about_author_callback(callback: CallbackQuery):
    """Информация об авторе"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    author_key = user_data.get("selected_author")
    
    if not author_key or author_key not in AUTHORS:
        await callback.answer("Сначала выберите автора")
        return
    
    author = AUTHORS[author_key]
    
    # Факты об авторе
    facts = {
        "pushkin": [
            "📖 Написал первое стихотворение в 8 лет",
            "🎓 Окончил Царскосельский лицей в 1817 году",
            "✍️ Роман «Евгений Онегин» писал 7 лет",
            "🌍 Владел 13 иностранными языками",
            "⚔️ Участвовал в 29 дуэлях",
            "💔 Последняя дуэль была 27 января 1837 года"
        ],
        "dostoevsky": [
            "🎭 Пережил инсценировку смертной казни",
            "⛓️ 4 года провел на каторге в Сибири",
            "📝 Роман «Игрок» написал за 26 дней",
            "💊 Страдал эпилепсией с 18 лет",
            "❤️ Был дважды женат",
            "🏆 Речь о Пушкине стала триумфом"
        ],
        "tolstoy": [
            "🏡 Родился и жил в Ясной Поляне",
            "📚 Открыл школу для крестьянских детей",
            "✍️ «Войну и мир» писал 6 лет",
            "🚶 В 82 года ушел из дома",
            "⛪ Был отлучен от церкви",
            "🌍 Произведения переведены на 100+ языков"
        ],
        "gogol": [
            "🔥 Сжег второй том «Мертвых душ»",
            "😨 Боялся быть похороненным заживо",
            "✍️ Писал стоя за конторкой",
            "🏫 Был преподавателем истории",
            "🇮🇹 12 лет прожил в Италии",
            "📖 Последние слова: «Лестницу, поскорее!»"
        ],
        "chekhov": [
            "👨‍⚕️ По профессии был врачом",
            "💊 Лечил больных бесплатно",
            "🌳 Посадил более 1000 деревьев",
            "🗺️ Путешествовал на Сахалин",
            "🏆 Признан одним из лучших драматургов",
            "📝 Следовал принципу краткости"
        ],
        "gigachad": [
            "💪 КАЖДЫЙ ДЕНЬ ЧИТАЕТ 100 СТРАНИЦ",
            "🔥 ЗНАЕТ КЛАССИКОВ НАИЗУСТЬ",
            "🚀 МОТИВИРУЕТ НА САМОРАЗВИТИЕ",
            "🏆 ЧИТАЕТ КНИГИ ДАЖЕ ВО СНЕ",
            "📚 СЧИТАЕТ ЧТЕНИЕ ТРЕНИРОВКОЙ",
            "💪 НИКОГДА НЕ СДАЕТСЯ"
        ]
    }
    
    author_info = f"""
{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

📖 {bold('ОБ АВТОРЕ')} {author['emoji']}

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

{author['emoji']} {bold(author['name'])}
{italic(author['birth'])} • {author['description']}

{code('──────────────────────────────')}

🎭 {bold('Стиль общения:')}
{author['style']}

{code('──────────────────────────────')}

✨ {bold('Интересные факты:')}
"""
    
    author_info += "\n".join(facts.get(author_key, ["• Информация обновляется..."]))
    
    author_info += f"""

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

{code('🎭 Продолжайте диалог, чтобы узнать лучше!')}
"""
    
    await callback.message.answer(
        author_info,
        parse_mode=ParseMode.HTML
    )
    await callback.answer(f"📖 {author['name'].split()[0]}")

@router.callback_query(F.data == "all_authors")
async def all_authors_callback(callback: CallbackQuery):
    """Все авторы"""
    await cmd_authors(callback.message)
    await callback.answer("📚 Все писатели")

@router.callback_query(F.data == "stats")
async def stats_callback(callback: CallbackQuery):
    """Статистика"""
    await cmd_stats(callback.message)
    await callback.answer("📊 Статистика")

@router.callback_query(F.data == "choose_author")
async def choose_author_callback(callback: CallbackQuery):
    """Выбор автора из помощи"""
    await cmd_start(callback.message)
    await callback.answer("🎭 Выбор автора")

@router.callback_query(F.data == "current_chat")
async def current_chat_callback(callback: CallbackQuery):
    """Текущий диалог"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    author_key = user_data.get("selected_author")
    
    if author_key and author_key in AUTHORS:
        author = AUTHORS[author_key]
        await callback.answer(f"Вы общаетесь с {author['name']}")
    else:
        await callback.answer("Автор не выбран")

# ========== ОБРАБОТКА СООБЩЕНИЙ ==========
@router.message(F.text)
async def handle_message(message: Message):
    """Обработка всех текстовых сообщений"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        user_data = db.get_user_data(user_id)
        
        # Проверяем, выбран ли автор
        if not user_data.get("selected_author"):
            await message.answer(
                format_no_author_message(user_name),
                parse_mode=ParseMode.HTML,
                reply_markup=get_main_keyboard()
            )
            return
        
        # Если автор выбран - обрабатываем сообщение
        author_key = user_data["selected_author"]
        author = AUTHORS.get(author_key, AUTHORS["pushkin"])
        
        # Показываем статус "автор думает"
        status_msg = await message.answer(
            f"{italic('✨ ' + author['emoji'] + ' ' + author['name'].split()[0] + ' обдумывает ответ...')}",
            parse_mode=ParseMode.HTML
        )
        
        # Генерируем ответ через литературный ИИ
        try:
            response = await literary_ai.generate_response(
                author_key=author_key,
                author_name=author['name'],
                user_message=message.text,
                conversation_history=user_data.get("conversation_history", [])
            )
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            response = f"Извините, {author['name'].split()[0]} временно задумался. Попробуйте задать вопрос немного иначе."
        
        # Обновляем базу данных
        db.update_conversation(
            user_id=user_id,
            author_key=author_key,
            user_message=message.text,
            bot_response=response
        )
        
        # Удаляем статус
        await status_msg.delete()
        
        # Форматируем и отправляем ответ
        response_text = format_author_response(author, response)
        
        # Ограничиваем длину ответа
        if len(response_text) > 4000:
            response_text = response_text[:4000] + f"\n\n{code('📝 Ответ сокращен для удобства чтения')}"
        
        await message.answer(
            response_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard(author_key)
        )
        
        logger.info(f"✅ Ответ отправлен: {user_id} → {author_key}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {e}")
        await message.answer(
            f"""
{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}

⚠️ {bold('Произошла ошибка!')}

{code('──────────────────────────────')}

Попробуйте:
1. Перезапустить бота командой /start
2. Задать вопрос по-другому
3. Сбросить диалог кнопкой '🔄 Новый диалог'

{code('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}
""",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_keyboard()
        )

# ========== ЗАПУСК БОТА ==========
async def main():
    """Запуск бота"""
    try:
        # Создаем бота и диспетчер
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        dp.include_router(router)
        
        # Информация о запуске
        print("=" * 60)
        print("🚀 ЗАПУСК ЛИТЕРАТУРНОГО БОТА")
        print("=" * 60)
        print(f"🤖 Бот: {'✅ Токен загружен' if BOT_TOKEN else '❌ Токен не найден'}")
        print(f"💭 Литературный ИИ: ✅ Активирован")
        print(f"💾 База данных: ✅ Готова")
        print(f"👤 Авторов в базе: {len(AUTHORS)}")
        print("=" * 60)
        print("\n📝 Основные команды:")
        print("• /start - Начать диалог с выбором автора")
        print("• /help - Помощь по использованию")
        print("• /authors - Список всех писателей")
        print("• /stats - Ваша статистика")
        print("=" * 60)
        
        # Удаляем вебхук и запускаем поллинг
        await bot.delete_webhook(drop_pending_updates=True)
        print("\n🔄 Бот запущен и ожидает сообщений...")
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка запуска: {e}")
        print(f"\n❌ ОШИБКА: {e}")
        print("\n🔧 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
        print("1. Неправильный BOT_TOKEN в .env")
        print("2. Отсутствуют зависимости (pip install -r requirements.txt)")
        print("3. Проблемы с интернет-соединением")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Непредвиденная ошибка: {e}")
