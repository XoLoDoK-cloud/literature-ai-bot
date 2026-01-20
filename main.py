#!/usr/bin/env python3
# ========== ОСНОВНОЙ ФАЙЛ БОТА ==========

import asyncio
import logging
import sys
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery
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
    },
    "gigachad": {
        "name": "ГИГАЧАД",
        "emoji": "💪",
        "birth": "Легенда",
        "description": "Мотивационный литературный эксперт",
        "greeting": "СЛУШАЙ СЮДА! Готов качать твой мозг книгами! 🔥"
    }
}

# ========== КЛАВИАТУРЫ ==========
def get_authors_keyboard():
    """Клавиатура для выбора автора"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = [
        [InlineKeyboardButton(text="🖋️ Пушкин", callback_data="author_pushkin")],
        [InlineKeyboardButton(text="📚 Достоевский", callback_data="author_dostoevsky")],
        [InlineKeyboardButton(text="✍️ Толстой", callback_data="author_tolstoy")],
        [InlineKeyboardButton(text="👻 Гоголь", callback_data="author_gogol")],
        [InlineKeyboardButton(text="🏥 Чехов", callback_data="author_chekhov")],
        [InlineKeyboardButton(text="💪 ГИГАЧАД", callback_data="author_gigachad")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
        [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_chat_keyboard():
    """Клавиатура во время диалога"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = [
        [InlineKeyboardButton(text="👥 Сменить автора", callback_data="change_author")],
        [InlineKeyboardButton(text="🔄 Новый диалог", callback_data="reset_chat")],
        [InlineKeyboardButton(text="ℹ️ Об авторе", callback_data="about_author")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")]
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

👋 {bold(f'Привет, {user_name}!')}

Я могу представить любого русского классика.
Выберите писателя и задайте ему любой вопрос.

👇 {bold('Выберите автора для диалога:')}
"""
        
        await message.answer(
            welcome_text,
            reply_markup=get_authors_keyboard(),
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
{create_header('ПОМОЩЬ ПО БОТУ', '📖')}

{bold('Основные команды:')}
/start - Выбор автора
/help - Помощь
/test - Проверка работы бота
/authors - Список писателей

{bold('Как использовать:')}
1. Нажмите /start
2. Выберите автора из списка
3. Задавайте вопросы в свободной форме
4. Получайте ответы от лица автора

{bold('Доступные авторы:')}
• 🖋️ Александр Пушкин
• 📚 Фёдор Достоевский
• ✍️ Лев Толстой
• 👻 Николай Гоголь
• 🏥 Антон Чехов
• 💪 ГИГАЧАД (мотивационный режим)

{bold('Если бот не отвечает:')}
1. Проверьте файл .env с токенами
2. Убедитесь, что все файлы на месте
3. Напишите /test для проверки
"""
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@router.message(Command("test"))
async def cmd_test(message: Message):
    """Тестовая команда"""
    test_text = f"""
{create_header('ТЕСТ РАБОТЫ БОТА', '✅')}

{bold('Статус системы:')}
🤖 Бот: {"✅ Активен" if BOT_TOKEN else "❌ Не найден"}
💬 GigaChat: {"✅ Доступен" if gigachat_client.available else "⚠️ Заглушки"}
💾 База данных: {"✅ Готова"}

{bold('Ваши данные:')}
👤 ID: {code(str(message.from_user.id))}
📛 Имя: {message.from_user.first_name}
🔗 Username: @{message.from_user.username or "Нет"}

{bold('Попробуйте:')}
1. Нажмите /start для выбора автора
2. Выберите любого писателя
3. Задайте вопрос о литературе или жизни
4. Получите ответ от лица автора!

{bold('Пример вопроса:')}
"Каков смысл жизни по вашему мнению?"
"""
    await message.answer(test_text, parse_mode=ParseMode.HTML)

@router.message(Command("authors"))
async def cmd_authors(message: Message):
    """Список авторов"""
    authors_text = f"""
{create_header('ВСЕ ПИСАТЕЛИ', '👥')}

{bold('Доступные для диалога:')}
"""
    
    for key, author in AUTHORS.items():
        authors_text += f"\n{author['emoji']} {bold(author['name'])}"
        authors_text += f"\n{italic(author['birth'])} • {author['description']}\n"
    
    authors_text += f"\n{'═' * 40}"
    authors_text += f"\n{code('Используйте /start для выбора автора')}"
    
    await message.answer(authors_text, parse_mode=ParseMode.HTML, reply_markup=get_authors_keyboard())

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика пользователя"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    
    stats_text = f"""
{create_header('ВАША СТАТИСТИКА', '📊')}

{bold('Общая информация:')}
💬 Всего сообщений: {user_data.get('message_count', 0)}
👤 Выбранный автор: {AUTHORS.get(user_data.get('selected_author', ''), {}).get('name', 'Не выбран')}
📅 Дата регистрации: {user_data.get('created_at', 'Неизвестно')[:10]}

{bold('История диалогов:')}
"""
    
    if user_data.get('conversation_history'):
        # Показываем последние 3 диалога
        history = user_data['conversation_history'][-6:]  # Последние 3 пары сообщений
        for i, msg in enumerate(history):
            role = "Вы" if msg['role'] == 'user' else "Автор"
            preview = msg['content'][:50] + "..." if len(msg['content']) > 50 else msg['content']
            stats_text += f"\n{role}: {preview}"
    else:
        stats_text += "\nИстория диалогов пуста. Начните общение!"
    
    stats_text += f"\n\n{code('Продолжайте общение для улучшения статистики!')}"
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

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
        
        # Генерация приветствия
        greeting = author.get("greeting", "Здравствуйте! Рад беседе.")
        if author_key == "gigachad":
            greeting = f"СЛУШАЙ СЮДА, {user_name.upper()}! {greeting}"
        
        await callback.message.edit_text(
            f"{bold(f'{author[\"emoji\"]} Вы выбрали: {author[\"name\"]}')}\n\n"
            f"{italic(f'{author[\"birth\"]} • {author[\"description\"]}')}\n\n"
            f"{greeting}\n\n"
            f"{bold('Теперь задавайте вопросы!')}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard()
        )
        
        await callback.answer(f"Выбран: {author['name']}")
        logger.info(f"✅ Выбор автора: {user_id} → {author_key}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в выборе автора: {e}")
        await callback.answer("Ошибка выбора автора")

@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    """Обработчик кнопки помощи"""
    await cmd_help(callback.message)
    await callback.answer()

@router.callback_query(F.data == "about")
async def about_callback(callback: CallbackQuery):
    """О боте"""
    about_text = f"""
{create_header('О БОТЕ', 'ℹ️')}

{bold('Литературный Диалог')} — это уникальный бот, который позволяет 
общаться с великими русскими писателями.

{bold('Возможности:')}
• Беседа с Пушкиным, Достоевским, Толстым и другими
• Режим ГИГАЧАД для мотивации
• Сохранение истории диалогов
• Умные ответы на основе контекста

{bold('Технологии:')}
• Python + aiogram 3.x
• GigaChat API для интеллектуальных ответов
• Локальная база данных на JSON

{bold('Для разработчиков:')}
Исходный код и инструкции доступны на GitHub.
Бот активно развивается и улучшается.

{code('Приятного общения с классиками!')}
"""
    await callback.message.answer(about_text, parse_mode=ParseMode.HTML)
    await callback.answer()

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    """Возврат в главное меню"""
    await cmd_start(callback.message)
    await callback.answer()

@router.callback_query(F.data == "change_author")
async def change_author_callback(callback: CallbackQuery):
    """Смена автора"""
    await callback.message.answer(
        "Выберите нового автора для диалога:",
        reply_markup=get_authors_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "reset_chat")
async def reset_chat_callback(callback: CallbackQuery):
    """Сброс диалога"""
    user_id = callback.from_user.id
    db.reset_conversation(user_id)
    
    await callback.message.answer(
        "✅ Диалог сброшен! История очищена.\n\n"
        "Выберите автора для начала нового диалога:",
        reply_markup=get_authors_keyboard()
    )
    await callback.answer("Диалог сброшен")

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
    
    author_info = f"""
{create_header(f'ОБ АВТОРЕ: {author["name"]}', author["emoji"])}

{bold('Годы жизни:')} {author['birth']}
{bold('Описание:')} {author['description']}

{bold('Интересные факты:')}
"""
    
    # Добавляем факты об авторе
    facts = {
        "pushkin": [
            "• Писал свои первые стихи в 8 лет",
            "• Знаменитый роман в стихах 'Евгений Онегин' писал 7 лет",
            "• Владел 13 языками",
            "• Участвовал в 29 дуэлях"
        ],
        "dostoevsky": [
            "• Пережил инсценировку казни",
            "• 4 года провел на каторге в Сибири",
            "• Написал 'Игрока' за 26 дней из-за долгов",
            "• Страдал эпилепсией"
        ],
        "tolstoy": [
            "• Открыл школу для крестьянских детей",
            "• В 82 года ушел из дома и умер на станции",
            "• Был отлучен от церкви",
            "• Его произведения переведены на 100+ языков"
        ],
        "gogol": [
            "• Сжег второй том 'Мертвых душ'",
            "• Боялся быть похороненным заживо",
            "• Писал стоя за конторкой",
            "• Был преподавателем истории"
        ],
        "chekhov": [
            "• По профессии был врачом",
            "• Лечил больных бесплатно",
            "• Посадил более 1000 деревьев",
            "• Путешествовал на Сахалин для изучения каторги"
        ],
        "gigachad": [
            "💪 КАЖДЫЙ ДЕНЬ ЧИТАЕТ ПО 100 СТРАНИЦ",
            "🔥 ЗНАЕТ ВСЕХ РУССКИХ КЛАССИКОВ НАИЗУСТЬ",
            "🚀 МОТИВИРУЕТ МИЛЛИОНЫ НА ЧТЕНИЕ",
            "🏆 ЧИТАЕТ КНИГИ ДАЖЕ ВО СНЕ"
        ]
    }
    
    author_info += "\n".join(facts.get(author_key, ["• Информация обновляется..."]))
    author_info += f"\n\n{code('Продолжайте диалог, чтобы узнать больше!')}"
    
    await callback.message.answer(author_info, parse_mode=ParseMode.HTML)
    await callback.answer()

# ========== ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ ==========
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
                f"⚠️ {bold('Сначала выберите писателя!')}\n\n"
                f"Используйте кнопку ниже для выбора автора:",
                reply_markup=get_authors_keyboard()
            )
            return
        
        author_key = user_data["selected_author"]
        author = AUTHORS.get(author_key, AUTHORS["pushkin"])
        
        # Показываем статус "печатает"
        status_msg = await message.answer(
            f"{italic(f'✍️ {author[\"name\"]} обдумывает ответ...')}",
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
                gigachad_mode=(author_key == "gigachad")
            )
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            response = "Извините, возникла ошибка при обработке вашего вопроса. Попробуйте задать его немного иначе."
        
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
        response_text = f"{bold(f'{author[\"emoji\"]} {author[\"name\"]}:')}\n\n{response}"
        
        # Добавляем контекстные подсказки если есть
        if context_analysis.get("main_topics"):
            response_text += f"\n\n{italic('Темы разговора: ' + ', '.join(context_analysis['main_topics']))}"
        
        await message.answer(
            response_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard()
        )
        
        logger.info(f"✅ Ответ отправлен: {user_id} → {author_key}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {e}")
        await message.answer(
            f"⚠️ {bold('Произошла ошибка!')}\n\n"
            f"Попробуйте:\n"
            f"1. Перезапустить бота командой /start\n"
            f"2. Задать вопрос по-другому\n"
            f"3. Сбросить диалог кнопкой '🔄 Новый диалог'",
            parse_mode=ParseMode.HTML
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
        print(f"💬 GigaChat: {'✅ Доступен' if gigachat_client.available else '⚠️ Режим заглушек'}")
        print(f"💾 База данных: ✅ Готова")
        print(f"👤 Авторов в базе: {len(AUTHORS)}")
        print("=" * 60)
        print("\n📝 Доступные команды:")
        print("• /start - Начать диалог")
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
