# ========== main.py ==========
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

# Получаем токены из .env
BOT_TOKEN = os.getenv("BOT_TOKEN")
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")

# Проверяем токены
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не найден в .env файле!")
    print("Создайте файл .env с BOT_TOKEN=ваш_токен")
    exit(1)

if not GIGACHAT_CREDENTIALS:
    print("⚠️ ВНИМАНИЕ: GIGACHAT_CREDENTIALS не найден")
    print("Бот будет работать без GigaChat (только заглушки)")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Импорты из наших модулей с обработкой ошибок
try:
    from database import db
    from gigachat_client import GigaChatClient
except ImportError as e:
    logger.error(f"❌ Ошибка импорта модулей: {e}")
    logger.error("Создаем заглушки...")
    
    # Создаем простую заглушку для базы данных
    class SimpleDB:
        def get_user_data(self, user_id):
            return {"user_id": user_id, "selected_author": None, "conversation_history": []}
        def save_user_data(self, user_id, data):
            pass
        def update_conversation(self, user_id, author_key, user_message, bot_response):
            pass
        def reset_conversation(self, user_id):
            pass
    
    db = SimpleDB()
    
    # Заглушка для GigaChatClient
    class SimpleGigaChat:
        def __init__(self, *args, **kwargs):
            self.available = False
        async def generate_response(self, *args, **kwargs):
            return "GigaChat временно недоступен. Используйте режим заглушек."

# Инициализация клиентов
try:
    gigachat_client = GigaChatClient(GIGACHAT_CREDENTIALS)
except:
    gigachat_client = SimpleGigaChat()

# Создаем роутер
router = Router()

# ========== ДАННЫЕ О ПИСАТЕЛЯХ ==========
AUTHORS = {
    "pushkin": {
        "name": "Александр Пушкин",
        "emoji": "🖋️",
        "birth": "1799-1837",
        "description": "Великий русский поэт, драматург и прозаик"
    },
    "dostoevsky": {
        "name": "Фёдор Достоевский", 
        "emoji": "📚",
        "birth": "1821-1881",
        "description": "Великий русский писатель, мыслитель и философ"
    },
    "tolstoy": {
        "name": "Лев Толстой",
        "emoji": "✍️", 
        "birth": "1828-1910",
        "description": "Великий русский писатель и мыслитель"
    },
    "gogol": {
        "name": "Николай Гоголь",
        "emoji": "👻",
        "birth": "1809-1852",
        "description": "Русский прозаик, драматург, поэт"
    },
    "chekhov": {
        "name": "Антон Чехов",
        "emoji": "🏥",
        "birth": "1860-1904", 
        "description": "Русский писатель, драматург, врач"
    },
    "gigachad": {
        "name": "Гигачад",
        "emoji": "💪",
        "birth": "Легенда",
        "description": "Мотивационный литературный эксперт"
    }
}

# ========== ПРОСТАЯ КЛАВИАТУРА ==========
def get_simple_authors_keyboard():
    """Простая клавиатура для выбора автора"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = [
        [InlineKeyboardButton(text="🖋️ Пушкин", callback_data="author_pushkin")],
        [InlineKeyboardButton(text="📚 Достоевский", callback_data="author_dostoevsky")],
        [InlineKeyboardButton(text="✍️ Толстой", callback_data="author_tolstoy")],
        [InlineKeyboardButton(text="👻 Гоголь", callback_data="author_gogol")],
        [InlineKeyboardButton(text="🏥 Чехов", callback_data="author_chekhov")],
        [InlineKeyboardButton(text="💪 Гигачад", callback_data="author_gigachad")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ========== КОМАНДЫ ==========
@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    try:
        user_id = message.from_user.id
        
        # Создаем или получаем данные пользователя
        user_data = db.get_user_data(user_id)
        user_data["username"] = message.from_user.username
        user_data["first_name"] = message.from_user.first_name
        db.save_user_data(user_id, user_data)
        
        welcome_text = f"""
🎭 <b>ЛИТЕРАТУРНЫЙ ДИАЛОГ</b>

👋 Привет, {message.from_user.first_name}!

Я могу представить любого русского классика.
Выберите писателя и задайте ему любой вопрос.

👇 <b>Выберите автора для диалога:</b>
"""
        
        await message.answer(
            welcome_text,
            reply_markup=get_simple_authors_keyboard(),
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"✅ Старт: {user_id} (@{message.from_user.username})")
        
    except Exception as e:
        logger.error(f"❌ Ошибка в /start: {e}")
        await message.answer("Произошла ошибка. Попробуйте позже.")

@router.message(Command("test"))
async def cmd_test(message: Message):
    """Тестовая команда для проверки работы бота"""
    await message.answer(f"""
✅ <b>Бот работает!</b>

🤖 <b>Статус:</b>
• Бот: {"✅ Активен" if BOT_TOKEN else "❌ Не найден"}
• GigaChat: {"✅ Доступен" if gigachat_client.available else "⚠️ Заглушки"}
• База данных: {"✅ Готова" if db else "❌ Ошибка"}

👤 <b>Ваши данные:</b>
• ID: {message.from_user.id}
• Имя: {message.from_user.first_name}
• Username: @{message.from_user.username}

📊 <b>Команды:</b>
• /start - Начать
• /help - Помощь
• /authors - Авторы
• /gigachad - Режим Гигачад
""", parse_mode=ParseMode.HTML)

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
<b>📖 ПОМОЩЬ ПО БОТУ</b>

<b>Основные команды:</b>
/start - Выбор автора
/test - Проверка работы бота
/gigachad - Режим Гигачада
/authors - Список писателей
/reset - Сбросить диалог

<b>Как использовать:</b>
1. Нажмите /start
2. Выберите автора из списка
3. Задавайте вопросы в свободной форме
4. Получайте ответы от лица автора

<b>Если бот не отвечает:</b>
1. Проверьте файл .env с токенами
2. Убедитесь, что все файлы на месте
3. Напишите /test для проверки
"""
    await message.answer(help_text, parse_mode=ParseMode.HTML)

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
        
        # Сохраняем выбор в базе
        user_data = db.get_user_data(user_id)
        user_data["selected_author"] = author_key
        user_data["conversation_history"] = []
        db.save_user_data(user_id, user_data)
        
        # Приветствия
        greetings = {
            "pushkin": "Здравствуйте! Рад нашей беседе.",
            "dostoevsky": "Здравствуйте. Что тревожит вашу душу?",
            "tolstoy": "Здравствуйте, друг мой.",
            "gogol": "А, вот и вы!",
            "chekhov": "Здравствуйте. Рассказывайте.",
            "gigachad": f"Слушай сюда, {callback.from_user.first_name}! 💪"
        }
        
        greeting = greetings.get(author_key, "Здравствуйте!")
        
        await callback.message.edit_text(
            f"<b>{author['emoji']} Вы выбрали: {author['name']}</b>\n\n"
            f"<i>{author['birth']} • {author['description']}</i>\n\n"
            f"<blockquote>{greeting}</blockquote>\n\n"
            f"<b>Теперь задавайте вопросы!</b>",
            parse_mode=ParseMode.HTML
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

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    """Возврат в главное меню"""
    await cmd_start(callback.message)
    await callback.answer()

# ========== ОБРАБОТЧИК СООБЩЕНИЙ ==========
@router.message(F.text)
async def handle_message(message: Message):
    """Обработка всех текстовых сообщений"""
    try:
        user_id = message.from_user.id
        user_data = db.get_user_data(user_id)
        
        # Проверяем, выбран ли автор
        if not user_data.get("selected_author"):
            await message.answer(
                "⚠️ <b>Сначала выберите писателя!</b>\n\n"
                "Используйте /start для выбора автора.",
                reply_markup=get_simple_authors_keyboard()
            )
            return
        
        author_key = user_data["selected_author"]
        author = AUTHORS.get(author_key, AUTHORS["pushkin"])
        
        # Показываем статус
        status_msg = await message.answer(
            f"<i>✍️ {author['name']} обдумывает ответ...</i>",
            parse_mode=ParseMode.HTML
        )
        
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
            logger.error(f"Ошибка GigaChat: {e}")
            response = "Извините, возникла ошибка. Попробуйте другой вопрос."
        
        # Обновляем базу данных
        db.update_conversation(
            user_id=user_id,
            author_key=author_key,
            user_message=message.text,
            bot_response=response
        )
        
        # Удаляем статус
        await status_msg.delete()
        
        # Отправляем ответ
        await message.answer(
            f"<b>{author['emoji']} {author['name']}:</b>\n\n"
            f"<blockquote>{response}</blockquote>",
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"✅ Сообщение: {user_id} → {author_key}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки сообщения: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")

# ========== ЗАПУСК БОТА ==========
async def main():
    """Запуск бота"""
    try:
        bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        dp = Dispatcher()
        dp.include_router(router)
        
        # Информация о запуске
        print("=" * 60)
        print("🚀 ЗАПУСК ЛИТЕРАТУРНОГО БОТА")
        print(f"🤖 Бот: {BOT_TOKEN[:15]}...")
        print(f"🔑 GigaChat: {'✅ Активен' if gigachat_client.available else '❌ Недоступен'}")
        print("=" * 60)
        
        await bot.delete_webhook(drop_pending_updates=True)
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
