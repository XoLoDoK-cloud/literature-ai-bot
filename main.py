import asyncio
import logging
from datetime import datetime
from typing import Dict

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

from gemini_service import gemini_service
import os
from dotenv import load_dotenv

# ========== НАСТРОЙКА ==========

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Загрузка переменных
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN не найден!")
    exit(1)

# Инициализация
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# ========== ДАННЫЕ ==========

AUTHORS = {
    "pushkin": {
        "name": "Александр Пушкин",
        "emoji": "🖋️",
        "description": "Великий русский поэт (1799-1837)",
        "works": "Евгений Онегин, Капитанская дочка"
    },
    "dostoevsky": {
        "name": "Фёдор Достоевский",
        "emoji": "📚", 
        "description": "Русский писатель и философ (1821-1881)",
        "works": "Преступление и наказание, Идиот"
    },
    "tolstoy": {
        "name": "Лев Толстой",
        "emoji": "✍️",
        "description": "Русский писатель и мыслитель (1828-1910)",
        "works": "Война и мир, Анна Каренина"
    },
    "gogol": {
        "name": "Николай Гоголь", 
        "emoji": "👻",
        "description": "Русский прозаик и драматург (1809-1852)",
        "works": "Мёртвые души, Ревизор"
    },
    "chekhov": {
        "name": "Антон Чехов",
        "emoji": "🏥",
        "description": "Русский писатель и врач (1860-1904)",
        "works": "Вишнёвый сад, Чайка"
    }
}

# ========== СОСТОЯНИЕ ==========

# Храним данные пользователей
class UserData:
    def __init__(self):
        self.selected_author = None
        self.conversation_history = []
        self.message_count = 0

user_storage: Dict[int, UserData] = {}

def get_user_data(user_id: int) -> UserData:
    """Получить или создать данные пользователя"""
    if user_id not in user_storage:
        user_storage[user_id] = UserData()
    return user_storage[user_id]

# ========== КЛАВИАТУРЫ ==========

def authors_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора автора"""
    buttons = []
    for key, info in AUTHORS.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{info['emoji']} {info['name']}",
                callback_data=f"select_{key}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def chat_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура во время диалога"""
    buttons = [
        [InlineKeyboardButton(text="👥 Сменить автора", callback_data="change_author")],
        [InlineKeyboardButton(text="🔄 Новый диалог", callback_data="reset_chat")],
        [InlineKeyboardButton(text="ℹ️ О писателе", callback_data="about_author")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ========== КОМАНДЫ ==========

@dp.message(CommandStart())
async def start_command(message: types.Message):
    """Команда /start"""
    user_data = get_user_data(message.from_user.id)
    
    welcome = f"""
<b>📚 Литературный Диалог</b>

👋 Привет, {message.from_user.first_name}!

Я могу представить любого русского классика.
Выберите писателя и задайте ему любой вопрос.

<b>Доступные писатели:</b>
"""
    
    for info in AUTHORS.values():
        welcome += f"\n{info['emoji']} <b>{info['name']}</b>"
        welcome += f"\n<i>{info['description']}</i>"
    
    welcome += "\n\n👇 <b>Выберите автора:</b>"
    
    await message.answer(welcome, reply_markup=authors_keyboard())
    logger.info(f"Пользователь {message.from_user.id} запустил бота")

@dp.message(Command("help"))
async def help_command(message: types.Message):
    """Команда /help"""
    help_text = """
<b>📖 Помощь по боту</b>

<b>Как использовать:</b>
1. Выберите писателя
2. Задавайте вопросы
3. Получайте ответы от его лица

<b>Примеры вопросов:</b>
• Расскажи о своём детстве
• Какое твоё самое известное произведение?
• Что ты думаешь о современности?
• Кто был твоим кумиром?

<b>Команды:</b>
/start - Начать диалог
/help - Эта справка
/authors - Список писателей
/reset - Сбросить диалог

<b>Технологии:</b>
Бот использует искусственный интеллект Google Gemini.
Ответы основаны на реальных фактах о писателях.
"""
    await message.answer(help_text)

@dp.message(Command("authors"))
async def authors_command(message: types.Message):
    """Команда /authors"""
    await message.answer(
        "👥 <b>Выберите писателя для диалога:</b>",
        reply_markup=authors_keyboard()
    )

@dp.message(Command("reset"))
async def reset_command(message: types.Message):
    """Команда /reset"""
    user_data = get_user_data(message.from_user.id)
    user_data.conversation_history = []
    user_data.message_count = 0
    
    await message.answer(
        "🔄 <b>Диалог сброшен!</b>\n\n"
        "История очищена. Выберите автора для нового разговора.",
        reply_markup=authors_keyboard()
    )

# ========== CALLBACK ОБРАБОТЧИКИ ==========

@dp.callback_query(lambda c: c.data.startswith("select_"))
async def select_author_callback(callback: types.CallbackQuery):
    """Выбор автора"""
    author_key = callback.data.split("_")[1]
    
    if author_key not in AUTHORS:
        await callback.answer("Автор не найден")
        return
    
    author = AUTHORS[author_key]
    user_data = get_user_data(callback.from_user.id)
    
    # Сохраняем выбор
    user_data.selected_author = author_key
    user_data.conversation_history = []
    
    # Приветствие от автора
    greetings = {
        "pushkin": "Друзья мои, прекрасен наш союз! Чем могу служить?",
        "dostoevsky": "Здравствуйте. Что тревожит вашу душу?",
        "tolstoy": "Здравствуйте, друг мой. О чём поговорим?",
        "gogol": "А, вот и вы! Ну что, поговорим о странностях жизни?",
        "chekhov": "Здравствуйте. Рассказывайте, я слушаю."
    }
    
    greeting = greetings.get(author_key, "Здравствуйте! Рад нашей беседе.")
    
    await callback.message.edit_text(
        f"<b>{author['emoji']} Вы выбрали: {author['name']}</b>\n\n"
        f"<i>{author['description']}</i>\n"
        f"<i>Известные работы: {author['works']}</i>\n\n"
        f"<blockquote>{greeting}</blockquote>\n\n"
        f"<b>Теперь задавайте вопросы!</b>\n\n"
        f"<code>💡 Совет: Будьте конкретны в вопросах</code>",
        reply_markup=chat_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "change_author")
async def change_author_callback(callback: types.CallbackQuery):
    """Смена автора"""
    await callback.message.edit_text(
        "👥 <b>Выберите нового писателя:</b>\n\n"
        "С кем хотите побеседовать?",
        reply_markup=authors_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "reset_chat")
async def reset_chat_callback(callback: types.CallbackQuery):
    """Сброс диалога"""
    user_data = get_user_data(callback.from_user.id)
    user_data.conversation_history = []
    
    author_key = user_data.selected_author or "pushkin"
    author = AUTHORS.get(author_key, AUTHORS["pushkin"])
    
    await callback.message.answer(
        f"🔄 <b>Диалог с {author['name']} сброшен!</b>\n\n"
        "Начинаем разговор заново. Задавайте вопросы.",
        reply_markup=chat_keyboard()
    )
    await callback.answer("Диалог сброшен")

@dp.callback_query(lambda c: c.data == "about_author")
async def about_author_callback(callback: types.CallbackQuery):
    """Информация об авторе"""
    user_data = get_user_data(callback.from_user.id)
    
    if not user_data.selected_author:
        await callback.answer("Сначала выберите автора")
        return
    
    author_key = user_data.selected_author
    author = AUTHORS.get(author_key)
    
    # Детальная информация
    author_details = {
        "pushkin": """
<b>Александр Сергеевич Пушкин (1799-1837)</b>

<i>Основные произведения:</i>
• Евгений Онегин (роман в стихах)
• Капитанская дочка (исторический роман)
• Пиковая дама (повесть)
• Борис Годунов (трагедия)

<i>Интересные факты:</i>
• Родился в Москве, в дворянской семье
• Учился в Царскосельском лицее
• Был сослан за вольнодумные стихи
• Женился на Наталье Гончаровой
• Погиб на дуэли с Дантесом
""",
        "dostoevsky": """
<b>Фёдор Михайлович Достоевский (1821-1881)</b>

<i>Основные произведения:</i>
• Преступление и наказание
• Идиот
• Братья Карамазовы
• Бесы

<i>Интересные факты:</i>
• Был приговорён к смертной казни, помилован в последний момент
• 4 года провёл на каторге в Сибири
• Страдал эпилепсией
• Играл в рулетку, имел долги
• Редактировал журналы "Время" и "Эпоха"
"""
    }
    
    detail = author_details.get(author_key, 
        f"<b>{author['name']}</b>\n\n"
        f"{author['description']}\n"
        f"Известные работы: {author['works']}"
    )
    
    await callback.message.answer(detail)
    await callback.answer()

# ========== ОБРАБОТКА СООБЩЕНИЙ ==========

@dp.message()
async def handle_message(message: types.Message):
    """Обработка всех сообщений"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    # Проверяем выбор автора
    if not user_data.selected_author:
        await message.answer(
            "⚠️ <b>Сначала выберите писателя!</b>\n\n"
            "Используйте /start для выбора.",
            reply_markup=authors_keyboard()
        )
        return
    
    author_key = user_data.selected_author
    author = AUTHORS[author_key]
    
    # Показываем "печатает"
    typing_msg = await message.answer(
        f"✍️ <i>{author['name']} обдумывает ответ...</i>"
    )
    
    try:
        # Генерируем ответ через Gemini
        response = await gemini_service.generate_response(
            author_key=author_key,
            author_name=author["name"],
            user_message=message.text
        )
        
        # Удаляем статус
        await typing_msg.delete()
        
        # Сохраняем в историю
        user_data.conversation_history.append({
            "role": "user",
            "content": message.text
        })
        user_data.conversation_history.append({
            "role": "assistant", 
            "content": response
        })
        user_data.message_count += 1
        
        # Отправляем ответ
        await message.answer(
            f"<b>{author['emoji']} {author['name']}:</b>\n\n"
            f"<blockquote>{response}</blockquote>\n\n"
            f"<i>Задайте следующий вопрос или используйте меню:</i>",
            reply_markup=chat_keyboard()
        )
        
        logger.info(f"Пользователь {user_id} получил ответ от {author['name']}")
        
    except Exception as e:
        # Удаляем статус в случае ошибки
        try:
            await typing_msg.delete()
        except:
            pass
        
        await message.answer(
            f"❌ <b>Ошибка:</b>\n"
            f"{str(e)[:100]}\n\n"
            f"Попробуйте задать вопрос иначе или /reset",
        )
        logger.error(f"Ошибка обработки сообщения: {e}")

# ========== ЗАПУСК ==========

async def main():
    """Основная функция"""
    print("=" * 50)
    print("📚 ЛИТЕРАТУРНЫЙ БОТ")
    print("=" * 50)
    print(f"🤖 Токен: {BOT_TOKEN[:15]}...")
    print(f"⚡ Gemini: {'✅' if gemini_service.available else '❌'}")
    print("=" * 50)
    print("✅ Бот запущен! Ожидаем сообщений...")
    print("=" * 50)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ Бот остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
