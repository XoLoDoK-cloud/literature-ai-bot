#!/usr/bin/env python3
# ========== ОСНОВНОЙ ФАЙЛ БОТА ==========

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

# Получаем токены
BOT_TOKEN = os.getenv("BOT_TOKEN")
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")

# Проверяем токены
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден в .env файле!")
    print("Создайте файл .env с BOT_TOKEN=ваш_токен")
    exit(1)

if not GIGACHAT_CREDENTIALS:
    print("⚠️ ВНИМАНИЕ: GIGACHAT_CREDENTIALS не найден")
    print("Бот будет работать без GigaChat (только умные заглушки)")

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
    from services.gigachat_client import GigaChatClient
    from services.context_analyzer import context_analyzer
    from services.formatters import bold, italic, create_header
    logger.info("✅ Все модули успешно импортированы")
except ImportError as e:
    logger.error(f"❌ Ошибка импорта модулей: {e}")
    logger.error("Убедитесь, что все файлы в папке services/")
    exit(1)

# Инициализация клиента GigaChat
gigachat_client = GigaChatClient(GIGACHAT_CREDENTIALS)

# Создаем роутер
router = Router()

# ========== ДАННЫЕ О ПИСАТЕЛЯХ ==========
AUTHORS = {
    "pushkin": {
        "name": "Александр Пушкин",
        "emoji": "🖋️",
        "birth": "1799-1837",
        "description": "Великий русский поэт, драматург и прозаик",
        "greeting": "Здравствуйте! Рад нашей беседе. Что желаете узнать?"
    },
    "dostoevsky": {
        "name": "Фёдор Достоевский", 
        "emoji": "📚",
        "birth": "1821-1881",
        "description": "Великий русский писатель, мыслитель и философ",
        "greeting": "Здравствуйте. Что тревожит вашу душу? Готов выслушать и ответить."
    },
    "tolstoy": {
        "name": "Лев Толстой",
        "emoji": "✍️", 
        "birth": "1828-1910",
        "description": "Великий русский писатель и мыслитель",
        "greeting": "Здравствуйте, друг мой. Поговорим о важном?"
    },
    "gogol": {
        "name": "Николай Гоголь",
        "emoji": "👻",
        "birth": "1809-1852",
        "description": "Русский прозаик, драматург, поэт",
        "greeting": "А, вот и вы! Любопытно, что вы хотите узнать?"
    },
    "chekhov": {
        "name": "Антон Чехов",
        "emoji": "🏥",
        "birth": "1860-1904", 
        "description": "Русский писатель, драматург, врач",
        "greeting": "Здравствуйте. Рассказывайте. Краткость — сестра таланта."
    }
}

# ========== КРАСИВЫЕ КЛАВИАТУРЫ ==========
def get_main_menu_keyboard():
    """Главное меню - красивые кнопки в 2 ряда"""
    keyboard = [
        [
            InlineKeyboardButton(text="🖋️ Пушкин", callback_data="author_pushkin"),
            InlineKeyboardButton(text="📚 Достоевский", callback_data="author_dostoevsky")
        ],
        [
            InlineKeyboardButton(text="✍️ Толстой", callback_data="author_tolstoy"),
            InlineKeyboardButton(text="👻 Гоголь", callback_data="author_gogol")
        ],
        [
            InlineKeyboardButton(text="🏥 Чехов", callback_data="author_chekhov")
        ],
        [
            InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
            InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_chat_keyboard(author_key: str = None):
    """Клавиатура во время диалога"""
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Сменить автора", callback_data="change_author"),
            InlineKeyboardButton(text="🔄 Новый диалог", callback_data="reset_chat")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Об авторе", callback_data="about_author"),
            InlineKeyboardButton(text="📋 Все авторы", callback_data="list_authors")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    
    # Если автор выбран, показываем его имя
    if author_key and author_key in AUTHORS:
        author = AUTHORS[author_key]
        keyboard.insert(0, [
            InlineKeyboardButton(
                text=f"✨ Вы общаетесь с: {author['emoji']} {author['name'].split()[0]}",
                callback_data="current_author"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_authors_grid_keyboard():
    """Сетка авторов для выбора"""
    keyboard = [
        [
            InlineKeyboardButton(text="🖋️", callback_data="author_pushkin"),
            InlineKeyboardButton(text="📚", callback_data="author_dostoevsky"),
            InlineKeyboardButton(text="✍️", callback_data="author_tolstoy"),
            InlineKeyboardButton(text="👻", callback_data="author_gogol"),
            InlineKeyboardButton(text="🏥", callback_data="author_chekhov")
        ],
        [
            InlineKeyboardButton(text="🖋️ Пушкин", callback_data="author_pushkin"),
            InlineKeyboardButton(text="📚 Достоевский", callback_data="author_dostoevsky")
        ],
        [
            InlineKeyboardButton(text="✍️ Толстой", callback_data="author_tolstoy"),
            InlineKeyboardButton(text="👻 Гоголь", callback_data="author_gogol")
        ],
        [
            InlineKeyboardButton(text="🏥 Чехов", callback_data="author_chekhov"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="help")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

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
        
        welcome_text = f"""
{create_header('ЛИТЕРАТУРНЫЙ ДИАЛОГ', '🎭')}

<b>👋 Добро пожаловать, {user_name}!</b>

✨ <i>Погрузитесь в мир русской классической литературы</i> ✨

💬 <b>Я могу представить любого русского классика.</b>
🎭 <b>Выберите писателя и задайте ему любой вопрос.</b>

👇 <b>Выберите автора для диалога:</b>
"""
        
        await message.answer(
            welcome_text,
            reply_markup=get_authors_grid_keyboard(),
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"✅ Старт: {user_id} (@{message.from_user.username})")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в /start: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = f"""
{create_header('📚 ПОМОЩЬ ПО БОТУ', '❓')}

<b>✨ Как использовать бота:</b>

1️⃣ <b>Начните общение:</b>
   • Нажмите /start или кнопку "🏠 Главное меню"
   • Выберите автора из списка

2️⃣ <b>Задавайте вопросы:</b>
   • О литературе и творчестве
   • О жизни и философии
   • О любых других темах

3️⃣ <b>Управляйте диалогом:</b>
   • 👥 Сменить автора — выбрать нового писателя
   • 🔄 Новый диалог — начать разговор заново
   • ℹ️ Об авторе — узнать о писателе больше

<b>📋 Доступные команды:</b>
• /start — начать диалог с выбором автора
• /help — показать это сообщение
• /authors — список всех писателей
• /stats — ваша статистика
• /test — проверить работу бота

<b>🎭 Доступные писатели:</b>
• 🖋️ Александр Пушкин
• 📚 Фёдор Достоевский
• ✍️ Лев Толстой
• 👻 Николай Гоголь
• 🏥 Антон Чехов

<code>💡 Совет: Не стесняйтесь задавать любые вопросы!</code>
"""
    await message.answer(help_text, parse_mode=ParseMode.HTML, reply_markup=get_main_menu_keyboard())

@router.message(Command("test"))
async def cmd_test(message: Message):
    """Тестовая команда"""
    test_text = f"""
{create_header('✅ ПРОВЕРКА РАБОТЫ БОТА', '🔧')}

<b>🎯 Статус системы:</b>
🤖 <b>Бот:</b> {"✅ Активен" if BOT_TOKEN else "❌ Не найден"}
💬 <b>GigaChat:</b> {"✅ Доступен" if gigachat_client.available else "⚠️ Умные заглушки"}
💾 <b>База данных:</b> ✅ Готова

<b>👤 Ваши данные:</b>
🆔 <b>ID:</b> <code>{message.from_user.id}</code>
📛 <b>Имя:</b> {message.from_user.first_name}
🔗 <b>Username:</b> @{message.from_user.username or "не установлен"}

<b>🚀 Попробуйте прямо сейчас:</b>
1. Нажмите кнопку ниже "🖋️ Пушкин"
2. Задайте вопрос, например:
   • "Что такое любовь?"
   • "Как писать стихи?"
   • "О чем ваше самое известное произведение?"

<code>✨ Бот готов к работе! Выберите автора и начинайте диалог!</code>
"""
    await message.answer(test_text, parse_mode=ParseMode.HTML, reply_markup=get_authors_grid_keyboard())

@router.message(Command("authors"))
async def cmd_authors(message: Message):
    """Список авторов с красивым оформлением"""
    authors_text = f"""
{create_header('👥 ВСЕ ПИСАТЕЛИ', '📚')}

<b>✨ Доступные для диалога классики:</b>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

🖋️ <b>Александр Пушкин</b>
<code>│</code> <i>1799-1837 • Великий русский поэт</i>
<code>│</code> <i>"Я помню чудное мгновенье..."</i>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

📚 <b>Фёдор Достоевский</b>
<code>│</code> <i>1821-1881 • Философ и писатель</i>
<code>│</code> <i>"Красота спасет мир"</i>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

✍️ <b>Лев Толстой</b>
<code>│</code> <i>1828-1910 • Мыслитель и прозаик</i>
<code>│</code> <i>"Все счастливые семьи похожи..."</i>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

👻 <b>Николай Гоголь</b>
<code>│</code> <i>1809-1852 • Мастер сатиры и гротеска</i>
<code>│</code> <i>"Какой же русский не любит быстрой езды?"</i>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

🏥 <b>Антон Чехов</b>
<code>│</code> <i>1860-1904 • Писатель и врач</i>
<code>│</code> <i>"Краткость — сестра таланта"</i>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<code>✨ Выберите автора для начала диалога:</code>
"""
    await message.answer(authors_text, parse_mode=ParseMode.HTML, reply_markup=get_authors_grid_keyboard())

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика пользователя"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    user_name = message.from_user.first_name
    
    stats_text = f"""
{create_header('📊 ВАША СТАТИСТИКА', '✨')}

<b>👤 Пользователь:</b> {user_name}
<b>🆔 ID:</b> <code>{user_id}</code>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<b>📈 Активность:</b>
💬 <b>Всего сообщений:</b> {user_data.get('message_count', 0)}
🗓️ <b>Дата регистрации:</b> {user_data.get('created_at', 'Неизвестно')[:10]}
🔄 <b>Последняя активность:</b> {user_data.get('updated_at', 'Неизвестно')[:10]}

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<b>🎭 Текущий автор:</b>
"""
    
    author_key = user_data.get('selected_author')
    if author_key and author_key in AUTHORS:
        author = AUTHORS[author_key]
        stats_text += f"{author['emoji']} <b>{author['name']}</b>"
    else:
        stats_text += "<i>Автор не выбран</i>"
    
    stats_text += f"\n\n<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>"
    
    # История диалогов
    stats_text += f"\n<b>💭 История диалогов:</b>\n"
    
    if user_data.get('conversation_history'):
        history = user_data['conversation_history'][-4:]  # Последние 2 пары сообщений
        for i, msg in enumerate(history):
            role_emoji = "👤" if msg['role'] == 'user' else "🖋️"
            role_text = "Вы" if msg['role'] == 'user' else "Автор"
            preview = msg['content']
            if len(preview) > 60:
                preview = preview[:57] + "..."
            
            stats_text += f"\n{role_emoji} <b>{role_text}:</b> <i>{preview}</i>"
            
            # Добавляем разделитель между парами сообщений
            if i % 2 == 1 and i < len(history) - 1:
                stats_text += f"\n<code>──────────────────────────────</code>"
    else:
        stats_text += "\n<i>История диалогов пуста</i>"
    
    stats_text += f"\n\n<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>"
    stats_text += f"\n<code>🎯 Продолжайте общение для новых достижений!</code>"
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML, reply_markup=get_main_menu_keyboard())

# ========== ОБРАБОТЧИКИ КНОПОК ==========
@router.callback_query(F.data.startswith("author_"))
async def author_selected_callback(callback: CallbackQuery):
    """Выбор конкретного автора - КРАСИВОЕ ОФОРМЛЕНИЕ"""
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
        
        # Красивое оформление выбора автора
        selection_text = f"""
{create_header('✨ АВТОР ВЫБРАН', author['emoji'])}

<b>{author['emoji']} {author['name']}</b>
<code>│</code> <i>{author['birth']} • {author['description']}</i>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<b>{author['greeting']}</b>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<code>💡 Теперь вы можете задавать вопросы!</code>
<code>🎭 Автор ответит в своем уникальном стиле</code>
"""
        
        await callback.message.edit_text(
            selection_text,
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
    """О боте - красивое оформление"""
    about_text = f"""
{create_header('ℹ️ О БОТЕ', '✨')}

<b>🎭 Литературный Диалог</b>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

✨ <b>Уникальный бот для общения с классиками</b>

💬 <i>Погрузитесь в мир русской литературы через диалог с великими писателями</i>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<b>🎯 Возможности:</b>
• 🗣️ Беседа с Пушкиным, Достоевским, Толстым и другими
• 📚 Ответы в характерном стиле каждого автора
• 💾 Сохранение истории всех диалогов
• 🎭 Уникальные личности классиков

<b>🔧 Технологии:</b>
• 🐍 Python 3.11+ и aiogram 3.x
• 🤖 GigaChat API для интеллектуальных ответов
• 💾 Локальная база данных на JSON

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<code>🎨 Разработано с любовью к литературе</code>
<code>📚 Приятного общения с классиками!</code>
"""
    await callback.message.answer(about_text, parse_mode=ParseMode.HTML, reply_markup=get_main_menu_keyboard())
    await callback.answer("ℹ️ О боте")

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    """Возврат в главное меню"""
    await cmd_start(callback.message)
    await callback.answer("🏠 Главное меню")

@router.callback_query(F.data == "change_author")
async def change_author_callback(callback: CallbackQuery):
    """Смена автора - красивое оформление"""
    change_text = f"""
{create_header('👥 СМЕНА АВТОРА', '✨')}

<b>✨ Выберите нового собеседника:</b>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<code>💡 Каждый автор имеет свой уникальный стиль:</code>
• 🖋️ Пушкин — поэтичный и изящный
• 📚 Достоевский — глубокий и философский
• ✍️ Толстой — мудрый и простой
• 👻 Гоголь — ироничный и гротескный
• 🏥 Чехов — лаконичный и точный

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<code>🎭 Выберите автора для продолжения диалога:</code>
"""
    
    await callback.message.edit_text(
        change_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_grid_keyboard()
    )
    await callback.answer("👥 Смена автора")

@router.callback_query(F.data == "reset_chat")
async def reset_chat_callback(callback: CallbackQuery):
    """Сброс диалога - красивое оформление"""
    user_id = callback.from_user.id
    db.reset_conversation(user_id)
    
    reset_text = f"""
{create_header('🔄 НОВЫЙ ДИАЛОГ', '✨')}

<b>✅ История диалога очищена!</b>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

✨ <i>Теперь вы можете начать совершенно новый диалог</i>
🎭 <i>Выберите автора и задайте первый вопрос</i>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<code>💡 Совет: Попробуйте нового автора для разнообразия!</code>
"""
    
    await callback.message.edit_text(
        reset_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_grid_keyboard()
    )
    await callback.answer("🔄 Диалог сброшен")

@router.callback_query(F.data == "about_author")
async def about_author_callback(callback: CallbackQuery):
    """Информация об авторе - красивое оформление"""
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
            "💔 Последняя дуэль с Дантесом была 27 января 1837 года"
        ],
        "dostoevsky": [
            "🎭 Пережил инсценировку смертной казни в 1849 году",
            "⛓️ 4 года провел на каторге в Омском остроге",
            "📝 Роман «Игрок» написал за 26 дней",
            "💊 Страдал эпилепсией с 18 лет",
            "❤️ Был дважды женат",
            "🏆 Речь о Пушкине в 1880 году стала триумфом"
        ],
        "tolstoy": [
            "🏡 Родился и жил в Ясной Поляне",
            "📚 Открыл школу для крестьянских детей",
            "✍️ «Войну и мир» писал 6 лет",
            "🚶 В 82 года ушел из дома и умер на станции",
            "⛪ Был отлучен от церкви в 1901 году",
            "🌍 Его произведения переведены на 100+ языков"
        ],
        "gogol": [
            "🔥 Сжег второй том «Мертвых душ»",
            "😨 Боялся быть похороненным заживо",
            "✍️ Писал стоя за конторкой",
            "🏫 Был преподавателем истории",
            "🇮🇹 12 лет прожил в Италии",
            "📖 Последние слова: «Лестницу, поскорее, давай лестницу!»"
        ],
        "chekhov": [
            "👨‍⚕️ По профессии был врачом-терапевтом",
            "💊 Лечил больных бесплатно",
            "🌳 Посадил более 1000 деревьев в Мелихове",
            "🗺️ Путешествовал на Сахалин для изучения каторги",
            "🏆 Признан одним из лучших драматургов мира",
            "📝 Следовал принципу «Краткость — сестра таланта»"
        ]
    }
    
    author_info = f"""
{create_header(f'📖 ОБ АВТОРЕ', author['emoji'])}

<b>{author['emoji']} {author['name']}</b>
<code>│</code> <i>{author['birth']}</i>
<code>│</code> <i>{author['description']}</i>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<b>✨ Интересные факты:</b>

"""
    
    author_info += "\n".join(facts.get(author_key, ["• Информация обновляется..."]))
    
    author_info += f"""

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<code>🎭 Продолжайте диалог, чтобы узнать автора лучше!</code>
"""
    
    await callback.message.answer(author_info, parse_mode=ParseMode.HTML)
    await callback.answer(f"ℹ️ {author['name'].split()[0]}")

@router.callback_query(F.data == "list_authors")
async def list_authors_callback(callback: CallbackQuery):
    """Список всех авторов из диалога"""
    await cmd_authors(callback.message)
    await callback.answer("📋 Все авторы")

@router.callback_query(F.data == "stats")
async def stats_callback(callback: CallbackQuery):
    """Статистика через кнопку"""
    await cmd_stats(callback.message)
    await callback.answer("📊 Статистика")

@router.callback_query(F.data == "current_author")
async def current_author_callback(callback: CallbackQuery):
    """Информация о текущем авторе"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    author_key = user_data.get("selected_author")
    
    if author_key and author_key in AUTHORS:
        author = AUTHORS[author_key]
        await callback.answer(f"Вы общаетесь с {author['name']}")
    else:
        await callback.answer("Автор не выбран")

# ========== ОБРАБОТКА СООБЩЕНИЙ БЕЗ ВЫБРАННОГО АВТОРА ==========
@router.message(F.text)
async def handle_message(message: Message):
    """Обработка всех текстовых сообщений"""
    try:
        user_id = message.from_user.id
        user_name = message.from_user.first_name
        user_data = db.get_user_data(user_id)
        
        # Проверяем, выбран ли автор
        if not user_data.get("selected_author"):
            # КРАСИВОЕ СООБЩЕНИЕ О ВЫБОРЕ АВТОРА
            selection_text = f"""
{create_header('🎭 ВЫБОР АВТОРА', '✨')}

<b>👋 {user_name}, чтобы начать диалог, выберите писателя:</b>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

✨ <i>Каждый автор имеет свой уникальный стиль общения:</i>

<code>──────────────────────────────</code>

🖋️ <b>Александр Пушкин</b>
<code>│</code> <i>Поэтичный, изящный, романтичный</i>

<code>──────────────────────────────</code>

📚 <b>Фёдор Достоевский</b>
<code>│</code> <i>Глубокий, философский, психологичный</i>

<code>──────────────────────────────</code>

✍️ <b>Лев Толстой</b>
<code>│</code> <i>Мудрый, простой, нравственный</i>

<code>──────────────────────────────</code>

👻 <b>Николай Гоголь</b>
<code>│</code> <i>Ироничный, гротескный, сатиричный</i>

<code>──────────────────────────────</code>

🏥 <b>Антон Чехов</b>
<code>│</code> <i>Лаконичный, точный, наблюдательный</i>

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<code>💡 Просто нажмите на кнопку с именем автора!</code>
"""
            
            await message.answer(
                selection_text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_authors_grid_keyboard()
            )
            return
        
        # Если автор выбран - обрабатываем сообщение
        author_key = user_data["selected_author"]
        author = AUTHORS.get(author_key, AUTHORS["pushkin"])
        
        # Показываем статус "автор думает"
        status_msg = await message.answer(
            f"<i>✨ {author['emoji']} {author['name'].split()[0]} обдумывает ответ...</i>",
            parse_mode=ParseMode.HTML
        )
        
        # Анализируем контекст сообщения
        context_analysis = context_analyzer.analyze_user_message(message.text)
        
        # Генерируем ответ
        try:
            response = await gigachat_client.generate_response(
                author_key=author_key,
                author_name=author['name'],
                user_message=message.text,
                conversation_history=user_data.get("conversation_history", []),
                gigachad_mode=False  # Отключаем режим гигачада
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
        response_text = f"""
<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<b>{author['emoji']} {author['name'].split()[0]}:</b>
{response}

<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>

<code>💭 Продолжайте диалог или используйте кнопки ниже</code>
"""
        
        # Ограничиваем длину ответа
        if len(response_text) > 4000:
            response_text = response_text[:4000] + "...\n\n<code>📝 Ответ сокращен для удобства чтения</code>"
        
        await message.answer(
            response_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard(author_key)
        )
        
        logger.info(f"✅ Ответ отправлен: {user_id} → {author_key}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {e}")
        await message.answer(
            f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>\n\n"
            f"⚠️ <b>Произошла ошибка!</b>\n\n"
            f"Попробуйте:\n"
            f"1. Перезапустить бота командой /start\n"
            f"2. Задать вопрос по-другому\n"
            f"3. Сбросить диалог кнопкой '🔄 Новый диалог'\n\n"
            f"<code>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard()
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
        print(f"💬 GigaChat: {'✅ Доступен' if gigachat_client.available else '⚠️ Умные заглушки'}")
        print(f"💾 База данных: ✅ Готова")
        print(f"👤 Авторов в базе: {len(AUTHORS)}")
        print("=" * 60)
        print("\n📝 Доступные команды:")
        print("• /start - Начать диалог с выбором автора")
        print("• /help - Помощь")
        print("• /test - Проверка работы")
        print("• /authors - Список писателей")
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
        print("4. Блокировка Telegram в вашем регионе")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Непредвиденная ошибка: {e}")
