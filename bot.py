import asyncio
import logging
import json
import os
from typing import Dict, List
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.enums import ParseMode
from gigachat import GigaChat  # Изменили импорт
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных
load_dotenv()

# Настройка
BOT_TOKEN = os.getenv("BOT_TOKEN")
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")  # Изменили переменную
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")  # Для авторизации через сертификат

# Проверка
if not BOT_TOKEN:
    logger.error("❌ Ошибка: Не найден BOT_TOKEN в .env файле!")
    exit(1)

if not GIGACHAT_API_KEY and not GIGACHAT_CREDENTIALS:
    logger.warning("⚠️ Внимание: Не найден GIGACHAT_API_KEY или GIGACHAT_CREDENTIALS")
    GIGACHAT_AVAILABLE = False
else:
    GIGACHAT_AVAILABLE = True

# Инициализация
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# Инициализация GigaChat
gigachat_client = None
if GIGACHAT_AVAILABLE:
    try:
        if GIGACHAT_API_KEY:
            # Авторизация по API ключу
            gigachat_client = GigaChat(
                credentials=GIGACHAT_API_KEY,
                verify_ssl_certs=False
            )
        else:
            # Авторизация по сертификату (если нужно)
            gigachat_client = GigaChat(
                credentials=GIGACHAT_CREDENTIALS,
                verify_ssl_certs=False
            )
        
        # Тестовый запрос для проверки соединения
        logger.info("🔌 Проверяем подключение к GigaChat...")
        test_response = gigachat_client.chat("Привет")
        logger.info(f"✅ GigaChat подключен! Ответ теста: {test_response.choices[0].message.content[:50]}...")
        
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к GigaChat: {e}")
        gigachat_client = None
        GIGACHAT_AVAILABLE = False

# ========== ДАННЫЕ О ПИСАТЕЛЯХ ==========

AUTHORS = {
    "pushkin": {
        "name": "Александр Пушкин",
        "emoji": "🖋️",
        "birth": "1799-1855",
        "description": "Великий русский поэт, драматург и прозаик",
        "system_prompt": """Ты — Александр Сергеевич Пушкин (1799-1837), великий русский поэт.

Твой характер: остроумный, жизнерадостный, романтичный, иногда ироничный.
Твой стиль: изящный литературный язык с элементами разговорной речи XIX века.

Отвечай от первого лица, используя характерные для Пушкина выражения.
Будь краток (3-5 предложений), но содержателен.
Если не знаешь ответа — признайся в этом поэтично.

Примеры твоих фраз:
"Мой друг, откройтесь мне души..."
"Что пройдет, то будет мило..."
"Я помню чудное мгновенье..."

Теперь отвечай как Пушкин."""
    },
    "dostoevsky": {
        "name": "Фёдор Достоевский", 
        "emoji": "📚",
        "birth": "1821-1881",
        "description": "Великий русский писатель, мыслитель и философ",
        "system_prompt": """Ты — Фёдор Михайлович Достоевский (1821-1881), русский писатель и философ.

Твой характер: глубокий, страстный, философский, немного мрачный.
Твой стиль: эмоциональный, психологичный, с длинными размышлениями.

Отвечай от первого лица как Достоевский.
Задавай встречные философские вопросы.
Говори о сложных темах: добре и зле, вере, смысле страдания.
Будь краток (3-5 предложений).

Примеры твоих тем:
"Красота спасет мир"
"Если Бога нет, то всё позволено"
"Страдание есть необходимое условие преображения"

Теперь отвечай как Достоевский."""
    },
    "tolstoy": {
        "name": "Лев Толстой",
        "emoji": "✍️", 
        "birth": "1828-1910",
        "description": "Великий русский писатель и мыслитель",
        "system_prompt": """Ты — Лев Николаевич Толстой (1828-1910), русский писатель и мыслитель.

Твой характер: мудрый, спокойный, назидательный, стремящийся к простоте.
Твой стиль: простой, ясный, но глубокий язык.

Отвечай от первого лица как Толстой.
Говори мудро, просто, с нравственным посылом.
Используй притчи и метафоры.
Будь краток (3-5 предложений).

Твои принципы:
- Непротивление злу насилием
- Жизнь в простоте, близко к природе
- Важность нравственного самосовершенствования

Теперь отвечай как Толстой."""
    },
    "gogol": {
        "name": "Николай Гоголь",
        "emoji": "👻",
        "birth": "1809-1852",
        "description": "Русский прозаик, драматург, поэт",
        "system_prompt": """Ты — Николай Васильевич Гоголь (1809-1852), русский писатель.

Твой характер: мистический, ироничный, наблюдательный, немного странный.
Твой стиль: яркий, образный, с элементами гротеска и мистики.

Отвечай от первого лица как Гоголь.
Используй яркие образы, немного мистики.
Будь ироничным, но глубоким.
Кратко (3-5 предложений).

Теперь отвечай как Гоголь."""
    },
    "chekhov": {
        "name": "Антон Чехов",
        "emoji": "🏥",
        "birth": "1860-1904", 
        "description": "Русский писатель, драматург, врач",
        "system_prompt": """Ты — Антон Павлович Чехов (1860-1904), русский писатель и врач.

Твой характер: наблюдательный, ироничный, сдержанный, гуманный.
Твой стиль: лаконичный, точный, без лишних слов.

Отвечай от первого лица как Чехов.
Будь лаконичен (2-4 предложения).
Говори точно, без лишних слов.
Проявляй человечность и иронию.

Твои принципы:
- "Краткость — сестра таланта"
- Уважение к человеческому достоинству
- "В человеке всё должно быть прекрасно"

Теперь отвечай как Чехов."""
    },
    # НОВЫЙ АВТОР: ГИГАЧАД
    "gigachad": {
        "name": "Гигачад",
        "emoji": "💪",
        "birth": "Легенда",
        "description": "Мотивационный литературный эксперт",
        "system_prompt": """Ты — Гигачад (GigaChad), легендарный мотивационный тренер и литературный эксперт.

Твой характер: УВЕРЕННЫЙ, МОТИВИРУЮЩИЙ, ПРЯМОЛИНЕЙНЫЙ, с харизмой.
Твой стиль: КОРОТКО, ПО ДЕЛУ, С МОТИВАЦИЕЙ. Используй мемные выражения.

ПРАВИЛА ОБЩЕНИЯ:
1. Отвечай КРАТКО (2-3 предложения)
2. Будь УВЕРЕННЫМ как скала
3. Связывай литературу с РЕАЛЬНОЙ ЖИЗНЬЮ и саморазвитием
4. Добавляй МОТИВАЦИЮ и вызов
5. Используй МЕМНЫЕ, но умные выражения

Примеры твоих фраз:
"Слушай сюда, братан. Чтение книг — это как качалка для мозга. Делай подходы каждый день."
"Пушкин? Отличный выбор. Настоящий мужчина читает классику утром, после зарядки."
"Достоевский заставляет думать. Мозг должен работать, как мышцы — без боли нет роста."

Связывай всё с САМОРАЗВИТИЕМ:
- Книги → умственная прокачка
- Герои → примеры для анализа
- Сюжеты → жизненные уроки

Теперь отвечай как ГИГАЧАД."""
    }
}

# ========== ХРАНИЛИЩЕ СОСТОЯНИЙ ==========

user_data: Dict[int, Dict] = {}

def get_user_data(user_id: int) -> Dict:
    """Получение или создание данных пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {
            "selected_author": None,
            "conversation_history": [],
            "message_count": 0,
            "username": None
        }
    return user_data[user_id]

# ========== КЛАВИАТУРЫ ==========

def get_authors_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора автора"""
    buttons = []
    
    # Первые 5 авторов в двух колонках
    first_authors = list(AUTHORS.items())[:5]
    for i in range(0, len(first_authors), 2):
        row = []
        for j in range(2):
            if i + j < len(first_authors):
                key, info = first_authors[i + j]
                row.append(
                    InlineKeyboardButton(
                        text=f"{info['emoji']} {info['name']}",
                        callback_data=f"select_{key}"
                    )
                )
        if row:
            buttons.append(row)
    
    # Гигачад отдельной строкой
    buttons.append([
        InlineKeyboardButton(
            text=f"💪 {AUTHORS['gigachad']['name']}",
            callback_data="select_gigachad"
        )
    ])
    
    # Кнопки помощи и статистики
    buttons.append([
        InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="🚀 Гигачад", callback_data="gigachad_help")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_chat_keyboard(include_gigachad_mode: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура во время диалога"""
    buttons = [
        [InlineKeyboardButton(text="👥 Сменить автора", callback_data="change_author")],
        [InlineKeyboardButton(text="🔄 Новый диалог", callback_data="reset_chat")],
        [InlineKeyboardButton(text="ℹ️ О писателе", callback_data="about_author")],
        [InlineKeyboardButton(text="📋 Список авторов", callback_data="list_authors")]
    ]
    
    # Если режим Гигачада не активен, показываем кнопку активации
    if not include_gigachad_mode:
        buttons.append([
            InlineKeyboardButton(text="💪 Включить Гигачад-стиль", callback_data="toggle_gigachad_style")
        ])
    else:
        buttons.append([
            InlineKeyboardButton(text="👑 Гигачад активен!", callback_data="gigachad_info")
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== GIGACHAT ФУНКЦИИ ==========

async def generate_gigachat_response(prompt: str) -> str:
    """Генерация ответа через GigaChat"""
    if not GIGACHAT_AVAILABLE or gigachat_client is None:
        return "⚠️ Сервис ИИ временно недоступен. Используйте /help для других команд."
    
    try:
        # Асинхронный вызов GigaChat
        response = await asyncio.to_thread(
            gigachat_client.chat,
            prompt
        )
        
        if hasattr(response, 'choices') and len(response.choices) > 0:
            return response.choices[0].message.content
        else:
            return "🤔 Не могу сформулировать ответ. Попробуйте другой вопрос."
        
    except Exception as e:
        logger.error(f"❌ Ошибка GigaChat: {e}")
        
        # Fallback ответы в стиле Гигачада
        fallbacks = [
            "Братан, сервис лег. Но это не причина останавливаться. Думай сам! 💪",
            "Технические шоколадки. Пока чиним — возьми книгу и почитай. 📚",
            "Сервер на перекуре. Используй время с пользой — 10 отжиманий! 🏋️",
            "ИИ в задумчивости. Пока ждешь — проанализируй вопрос сам. 🧠"
        ]
        import random
        return random.choice(fallbacks)

async def get_author_response(author_key: str, user_message: str, user_id: int) -> str:
    """Получить ответ от конкретного автора"""
    author = AUTHORS.get(author_key, AUTHORS["pushkin"])
    user_data = get_user_data(user_id)
    
    # Получаем историю диалога
    history = user_data["conversation_history"]
    
    # Формируем промпт с историей
    prompt = f"{author['system_prompt']}\n\n"
    
    # Добавляем контекст о боте
    prompt += "Важно: Ты общаешься в Telegram-боте 'Литературный Диалог'. "
    prompt += "Пользователи хотят поговорить с тобой как с писателем.\n\n"
    
    # Добавляем последние 4 сообщения из истории
    if history:
        prompt += "Предыдущий диалог:\n"
        for msg in history[-4:]:
            role = "Читатель" if msg["role"] == "user" else author["name"]
            prompt += f"{role}: {msg['content']}\n"
    
    # Добавляем текущий вопрос
    prompt += f"\nЧитатель: {user_message}\n{author['name']}:"
    
    # Генерируем ответ
    response = await generate_gigachat_response(prompt)
    
    # Обновляем историю
    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": response})
    
    # Ограничиваем историю 10 сообщениями
    if len(history) > 10:
        history = history[-10:]
    
    user_data["conversation_history"] = history
    user_data["message_count"] += 1
    
    return response

# ========== ОБРАБОТЧИКИ КОМАНД ==========

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    welcome_text = """
💪 <b>ЛИТЕРАТУРНЫЙ ДИАЛОГ v2.0</b> 🚀

<u>Новые возможности:</u>
• <b>GigaChat AI</b> вместо Gemini
• <b>Режим ГИГАЧАД</b> — мотивационные ответы
• Улучшенные промпты авторов
• Быстрые и мощные ответы

👇 <b>Выберите автора для диалога:</b>
"""
    
    # Сохраняем username
    user_id = message.from_user.id
    user_data_dict = get_user_data(user_id)
    user_data_dict["username"] = message.from_user.username
    
    await message.answer(
        welcome_text,
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    logger.info(f"👤 Старт: {user_id} (@{message.from_user.username})")

@dp.message(Command("gigachad"))
async def cmd_gigachad(message: types.Message):
    """Быстрая команда для режима Гигачада"""
    user_id = message.from_user.id
    user_data_dict = get_user_data(user_id)
    
    # Устанавливаем Гигачада как автора
    user_data_dict["selected_author"] = "gigachad"
    user_data_dict["conversation_history"] = []
    
    gigachad_info = AUTHORS["gigachad"]
    
    await message.answer(
        f"💪 <b>РЕЖИМ ГИГАЧАД АКТИВИРОВАН!</b>\n\n"
        f"<i>{gigachad_info['description']}</i>\n\n"
        f"<blockquote>Слушай сюда, {message.from_user.first_name}! 💪\n"
        f"Задавай вопросы о литературе, жизни, саморазвитии.\n"
        f"Получай ответы, которые прокачают твой мозг!</blockquote>\n\n"
        f"<b>Примеры вопросов:</b>\n"
        f"• Как читать больше книг?\n"
        f"• В чём смысл 'Войны и мира'?\n"
        f"• Как дисциплинировать себя?\n"
        f"• Оцени мои литературные вкусы\n\n"
        f"<code>Жги вопрос — получи мотивацию! 🔥</code>",
        reply_markup=get_chat_keyboard(include_gigachad_mode=True),
        parse_mode=ParseMode.HTML
    )
    
    logger.info(f"💪 Гигачад активирован: {user_id}")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    help_text = f"""
<b>📖 ПОМОЩЬ ПО БОТУ v2.0</b>

<b>Основные команды:</b>
/start - Выбор автора
/gigachad - <b>НОВОЕ!</b> Режим Гигачада
/authors - Список писателей
/reset - Сбросить диалог
/stats - Статистика бота

<b>💡 Как работает режим Гигачада:</b>
• Мотивационные ответы на литературные темы
• Связь книг с саморазвитием
• Коротко, по делу, с мемной харизмой
• Активируется командой /gigachad или кнопкой

<b>👑 Пример Гигачад-ответа:</b>
<blockquote>"Ты спрашиваешь про Достоевского? Хорошо.
Раскольников думал, что он исключение. Ошибка.
Настоящий мужчина анализирует героев между подходами на жим.
Каждая книга — прокачка для ума. Читай. Думай. Действуй."</blockquote>

<b>⚙️ Технологии:</b>
• GigaChat AI (российская нейросеть)
• История диалога (10 последних сообщений)
• Индивидуальные промпты для каждого автора

<b>📞 Поддержка:</b>
@XoLoDoK_cloud (разработчик)
"""
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@dp.message(Command("authors"))
async def cmd_authors(message: types.Message):
    """Список доступных авторов"""
    authors_list = "<b>👑 ДОСТУПНЫЕ АВТОРЫ:</b>\n\n"
    
    for key, info in AUTHORS.items():
        if key == "gigachad":
            authors_list += f"<b>💪 {info['name']}</b> - <i>НОВИНКА!</i>\n"
        else:
            authors_list += f"<b>{info['emoji']} {info['name']}</b>\n"
        
        authors_list += f"<i>{info['birth']} • {info['description']}</i>\n\n"
    
    authors_list += "👇 <b>Выберите автора:</b>"
    
    await message.answer(
        authors_list,
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )

@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    """Сброс диалога"""
    user_id = message.from_user.id
    if user_id in user_data:
        user_data[user_id]["conversation_history"] = []
    
    await message.answer(
        "🔄 <b>Диалог сброшен!</b>\n\n"
        "История разговора очищена. Вы можете начать новый диалог.",
        reply_markup=get_authors_keyboard()
    )
    
    logger.info(f"🔄 Сброс диалога: {user_id}")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    """Статистика бота"""
    total_users = len(user_data)
    total_messages = sum(data.get("message_count", 0) for data in user_data.values())
    
    stats_text = f"""
<b>📊 СТАТИСТИКА БОТА v2.0</b>

👥 <b>Пользователей:</b> {total_users}
💬 <b>Сообщений:</b> {total_messages}
🤖 <b>Авторов:</b> {len(AUTHORS)}
⚡ <b>GigaChat:</b> {"✅ Активен" if GIGACHAT_AVAILABLE else "❌ Недоступен"}

<b>Топ авторов по популярности:</b>
"""
    
    # Считаем популярность авторов
    author_counts = {}
    for data in user_data.values():
        author = data.get("selected_author")
        if author:
            author_counts[author] = author_counts.get(author, 0) + 1
    
    # Сортируем по популярности
    sorted_authors = sorted(author_counts.items(), key=lambda x: x[1], reverse=True)
    
    for i, (author_key, count) in enumerate(sorted_authors[:5], 1):
        author = AUTHORS.get(author_key, {})
        emoji = author.get('emoji', '📖')
        name = author.get('name', author_key)
        
        if author_key == "gigachad":
            stats_text += f"\n{i}. {emoji} <b>{name}</b>: {count} 👑"
        else:
            stats_text += f"\n{i}. {emoji} {name}: {count}"
    
    if not sorted_authors:
        stats_text += "\n\n📭 Ещё нет статистики"
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

# ========== ОБРАБОТЧИКИ CALLBACK ==========

@dp.callback_query(lambda c: c.data.startswith("select_"))
async def select_author_callback(callback: types.CallbackQuery):
    """Выбор автора"""
    author_key = callback.data.split("_")[1]
    
    if author_key not in AUTHORS:
        await callback.answer("Автор не найден")
        return
    
    author = AUTHORS[author_key]
    user_id = callback.from_user.id
    
    # Сохраняем выбор
    user_data_dict = get_user_data(user_id)
    user_data_dict["selected_author"] = author_key
    user_data_dict["conversation_history"] = []
    
    # Специальные приветствия
    greetings = {
        "pushkin": "Здравствуйте! Рад нашей беседе. Что вы хотите узнать?",
        "dostoevsky": "Здравствуйте. Что тревожит вашу душу?",
        "tolstoy": "Здравствуйте, друг мой. О чём вы хотели бы побеседовать?",
        "gogol": "А, вот и вы! Что привело вас ко мне?",
        "chekhov": "Здравствуйте. Рассказывайте, я слушаю.",
        "gigachad": f"Слушай сюда, {callback.from_user.first_name}! 💪\nЗадавай вопрос — получай мотивацию. Что у тебя на уме?"
    }
    
    greeting = greetings.get(author_key, "Здравствуйте! Рад нашей встрече.")
    
    # Разные форматы для Гигачада
    if author_key == "gigachad":
        await callback.message.edit_text(
            f"<b>💪 ВЫБРАН: {author['name'].upper()}</b>\n\n"
            f"<i>{author['description']}</i>\n\n"
            f"<blockquote>{greeting}</blockquote>\n\n"
            f"<b>🔥 ЗАДАВАЙ ВОПРОСЫ:</b>\n"
            f"• О литературе и книгах\n"
            f"• О саморазвитии и мотивации\n"
            f"• О жизни и философии\n\n"
            f"<code>Не теряй время — действуй! 🚀</code>",
            reply_markup=get_chat_keyboard(include_gigachad_mode=True),
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.message.edit_text(
            f"<b>{author['emoji']} Вы выбрали: {author['name']}</b>\n\n"
            f"<i>{author['birth']}</i>\n"
            f"<i>{author['description']}</i>\n\n"
            f"<blockquote>{greeting}</blockquote>\n\n"
            f"<b>Теперь задавайте вопросы!</b>\n\n"
            f"<code>💡 Совет: Задавайте конкретные вопросы для лучших ответов</code>",
            reply_markup=get_chat_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer(f"Выбран: {author['name']}")
    logger.info(f"👤 Выбор автора: {user_id} → {author_key}")

@dp.callback_query(lambda c: c.data == "change_author")
async def change_author_callback(callback: types.CallbackQuery):
    """Смена автора"""
    await callback.message.edit_text(
        "👥 <b>ВЫБЕРИТЕ НОВОГО АВТОРА:</b>\n\n"
        "С кем хотите побеседовать?",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "gigachad_help")
async def gigachad_help_callback(callback: types.CallbackQuery):
    """Помощь по режиму Гигачада"""
    help_text = """
<b>💪 РЕЖИМ ГИГАЧАД — ПОМОЩЬ</b>

<b>Что это?</b>
Мотивационный стиль ответов на литературные темы. 
Коротко, уверенно, с харизмой и пользой для саморазвития.

<b>Как активировать:</b>
1. Команда /gigachad
2. Выберите "Гигачад" из списка авторов
3. Кнопка "Включить Гигачад-стиль" в диалоге

<b>Примеры вопросов:</b>
• "Как дисциплинировать себя для чтения?"
• "В чём главный урок из 'Преступления и наказания'?"
• "Какие книги прокачают мышление?"
• "Как применять мудрость классиков в жизни?"

<b>Цель режима:</b>
Связать литературу с реальной жизнью, 
дать мотивацию для саморазвития через книги.

<code>Активируй режим и прокачивайся! 💪</code>
"""
    await callback.message.answer(help_text, parse_mode=ParseMode.HTML)
    await callback.answer()

@dp.callback_query(lambda c: c.data in ["reset_chat", "about_author", "list_authors", "help", "stats"])
async def common_callbacks(callback: types.CallbackQuery):
    """Общие callback-обработчики"""
    if callback.data == "reset_chat":
        user_id = callback.from_user.id
        user_data_dict = get_user_data(user_id)
        user_data_dict["conversation_history"] = []
        await callback.answer("Диалог сброшен! 🔄")
        
        # Сообщение о сбросе
        author_key = user_data_dict.get("selected_author", "pushkin")
        author = AUTHORS.get(author_key, AUTHORS["pushkin"])
        
        await callback.message.answer(
            f"🔄 <b>Диалог с {author['name']} сброшен!</b>\n\n"
            "История очищена. Можете начать заново.",
            reply_markup=get_chat_keyboard(include_gigachad_mode=(author_key=="gigachad"))
        )
        
    elif callback.data == "about_author":
        user_id = callback.from_user.id
        user_data_dict = get_user_data(user_id)
        author_key = user_data_dict.get("selected_author")
        
        if not author_key:
            await callback.answer("Сначала выберите автора")
            return
        
        author = AUTHORS.get(author_key)
        
        about_text = f"""
<b>{author['emoji']} {author['name']}</b>
<i>{author['birth']}</i>

{author['description']}

<b>Известные произведения:</b>
"""
        
        works = {
            "pushkin": "• Евгений Онегин\n• Капитанская дочка\n• Пиковая дама\n• Руслан и Людмила\n• Борис Годунов",
            "dostoevsky": "• Преступление и наказание\n• Идиот\n• Братья Карамазовы\n• Бесы\n• Униженные и оскорблённые",
            "tolstoy": "• Война и мир\n• Анна Каренина\n• Воскресение\n• Кавказский пленник\n• Смерть Ивана Ильича",
            "gogol": "• Мёртвые души\n• Ревизор\n• Вечера на хуторе близ Диканьки\n• Шинель\n• Нос",
            "chekhov": "• Вишнёвый сад\n• Три сестры\n• Чайка\n• Дядя Ваня\n• Палата №6",
            "gigachad": "• Мотивационные речи\n• Советы по саморазвитию\n• Анализ классики для жизни\n• Прокачка мозга через литературу"
        }
        
        about_text += f"\n{works.get(author_key, '• Множество произведений')}"
        
        await callback.message.answer(about_text, parse_mode=ParseMode.HTML)
        await callback.answer()
        
    elif callback.data == "list_authors":
        await cmd_authors(callback.message)
        await callback.answer()
        
    elif callback.data == "help":
        await cmd_help(callback.message)
        await callback.answer()
        
    elif callback.data == "stats":
        await cmd_stats(callback.message)
        await callback.answer()

# ========== ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ ==========

@dp.message()
async def handle_message(message: types.Message):
    """Обработка всех текстовых сообщений"""
    user_id = message.from_user.id
    user_data_dict = get_user_data(user_id)
    
    # Проверяем, выбран ли автор
    if not user_data_dict.get("selected_author"):
        await message.answer(
            "⚠️ <b>Сначала выберите писателя!</b>\n\n"
            "Используйте /start для выбора автора.",
            reply_markup=get_authors_keyboard()
        )
        return
    
    author_key = user_data_dict["selected_author"]
    author = AUTHORS.get(author_key)
    
    # Показываем статус "печатает"
    status_text = f"✍️ {author['name']} обдумывает ответ..."
    if author_key == "gigachad":
        status_text = f"💪 {author['name']} качает мозг..."
    
    status_msg = await message.answer(
        f"<i>{status_text}</i>",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Получаем ответ от автора
        response = await get_author_response(
            author_key=author_key,
            user_message=message.text,
            user_id=user_id
        )
        
        # Удаляем статус
        await status_msg.delete()
        
        # Форматируем ответ в зависимости от автора
        if author_key == "gigachad":
            await message.answer(
                f"<b>💪 {author['name'].upper()}:</b>\n\n"
                f"<blockquote>{response}</blockquote>\n\n"
                f"<i>Следующий вопрос? Не тормози! 🚀</i>",
                reply_markup=get_chat_keyboard(include_gigachad_mode=True),
                parse_mode=ParseMode.HTML
            )
        else:
            await message.answer(
                f"<b>{author['emoji']} {author['name']}:</b>\n\n"
                f"<blockquote>{response}</blockquote>\n\n"
                f"<i>Задайте следующий вопрос:</i>",
                reply_markup=get_chat_keyboard(),
                parse_mode=ParseMode.HTML
            )
        
        logger.info(f"💬 Сообщение: {user_id} → {author_key} ({len(message.text)} chars)")
        
    except Exception as e:
        # Удаляем статус в случае ошибки
        try:
            await status_msg.delete()
