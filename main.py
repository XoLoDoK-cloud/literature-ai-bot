import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from config import BOT_TOKEN
from database import db
from gigachat_client import gigachat_client

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# Данные о писателях (упрощенные)
AUTHORS = {
    "pushkin": {"name": "🖋️ Александр Пушкин", "greeting": "Здравствуйте! Рад нашей беседе. Что желаете узнать?"},
    "dostoevsky": {"name": "📚 Фёдор Достоевский", "greeting": "Здравствуйте. Что тревожит вашу душу?"},
    "tolstoy": {"name": "✍️ Лев Толстой", "greeting": "Здравствуйте, друг мой. Поговорим о важном?"},
    "gogol": {"name": "👻 Николай Гоголь", "greeting": "А, вот и вы! Любопытно, что вы хотите узнать?"},
    "chekhov": {"name": "🏥 Антон Чехов", "greeting": "Здравствуйте. Рассказывайте. Краткость — сестра таланта."},
    "gigachad": {"name": "💪 ГИГАЧАД", "greeting": "СЛУШАЙ СЮДА! Готов прокачать твой мозг классикой! 🔥"}
}

def get_authors_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора автора"""
    buttons = []
    
    # Первый ряд: 3 кнопки
    buttons.append([
        InlineKeyboardButton(text="🖋️ Пушкин", callback_data="author_pushkin"),
        InlineKeyboardButton(text="📚 Достоевский", callback_data="author_dostoevsky"),
        InlineKeyboardButton(text="✍️ Толстой", callback_data="author_tolstoy")
    ])
    
    # Второй ряд: 3 кнопки
    buttons.append([
        InlineKeyboardButton(text="👻 Гоголь", callback_data="author_gogol"),
        InlineKeyboardButton(text="🏥 Чехов", callback_data="author_chekhov"),
        InlineKeyboardButton(text="💪 ГИГАЧАД", callback_data="author_gigachad")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_chat_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура во время диалога"""
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Сменить автора", callback_data="change_author"),
            InlineKeyboardButton(text="🔄 Новый диалог", callback_data="reset_chat")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ========== КОМАНДЫ ==========
@router.message(CommandStart())
async def cmd_start(message: Message):
    """Запуск бота"""
    user_name = message.from_user.first_name if message.from_user else "Друг"
    
    welcome_text = f"""
✨ <b>ЛИТЕРАТУРНЫЙ ДИАЛОГ</b> ✨

👋 <b>Привет, {user_name}!</b>

💬 <b>Я могу представить любого русского классика.</b>
<b>Выберите писателя и задайте ему любой вопрос.</b>

👇 <b>Выберите автора для диалога:</b>
"""
    
    await message.answer(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard()
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Помощь"""
    help_text = """
📚 <b>ПОМОЩЬ ПО БОТУ</b>

✨ <b>Как использовать:</b>

1. <b>Выберите автора</b> из списка
2. <b>Задавайте вопросы</b> о:
   • Литературе и творчестве
   • Жизни и философии
   • Исторических событиях
   • Любых других темах

3. <b>Управляйте диалогом:</b>
   • 👥 Сменить автора — выбрать нового писателя
   • 🔄 Новый диалог — начать разговор заново
   • 🏠 Главное меню — вернуться к выбору автора

💡 <i>Бот использует ИИ GigaChat и базу знаний о писателях</i>
"""
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@router.message(Command("authors"))
async def cmd_authors(message: Message):
    """Список авторов"""
    await message.answer(
        "👥 <b>ВСЕ ПИСАТЕЛИ</b>\n\nВыберите автора для диалога:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard()
    )

# ========== ВЫБОР АВТОРА ==========
@router.callback_query(F.data.startswith("author_"))
async def author_selected(callback: CallbackQuery):
    """Выбор конкретного автора"""
    author_key = callback.data.split("_")[1]
    
    if author_key not in AUTHORS:
        await callback.answer("Автор не найден")
        return
    
    author = AUTHORS[author_key]
    user_id = callback.from_user.id
    
    # Сохраняем выбор
    user_data = db.get_user_data(user_id)
    user_data["selected_author"] = author_key
    db.save_user_data(user_id, user_data)
    
    # Приветственное сообщение
    await callback.message.edit_text(
        f"{author['name']}\n\n💬 {author['greeting']}\n\n<i>Задавайте вопросы — отвечу в своём стиле!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard()
    )
    
    await callback.answer(f"Выбран: {author['name']}")

# ========== УПРАВЛЕНИЕ ДИАЛОГОМ ==========
@router.callback_query(F.data == "change_author")
async def change_author(callback: CallbackQuery):
    """Смена автора"""
    await callback.message.edit_text(
        "👥 <b>ВЫБЕРИТЕ НОВОГО АВТОРА:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "reset_chat")
async def reset_chat(callback: CallbackQuery):
    """Сброс диалога"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    user_data["conversation_history"] = []
    user_data["selected_author"] = None
    db.save_user_data(user_id, user_data)
    
    await callback.message.edit_text(
        "🔄 <b>Диалог сброшен!</b>\n\nВыберите нового автора:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard()
    )
    await callback.answer("Диалог сброшен")

@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    """Главное меню"""
    await cmd_start(callback.message)
    await callback.answer()

# ========== ОБРАБОТКА СООБЩЕНИЙ ==========
@router.message(F.text)
async def handle_message(message: Message):
    """Обработка всех текстовых сообщений"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    
    # Проверяем, выбран ли автор
    if not user_data.get("selected_author"):
        await message.answer(
            "❌ <b>Сначала выберите автора!</b>\n\nИспользуйте кнопки ниже:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_authors_keyboard()
        )
        return
    
    # Получаем данные автора
    author_key = user_data["selected_author"]
    author = AUTHORS.get(author_key)
    
    user_text = message.text
    
    # Показываем "автор думает"
    thinking_msg = await message.answer(
        f"<i>✨ {author['name']} обдумывает ответ...</i>",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Генерируем ответ через GigaChat
        response = await gigachat_client.generate_response(
            author_key=author_key,
            user_message=user_text,
            conversation_history=user_data.get("conversation_history", [])
        )
        
        # Удаляем сообщение "думает"
        await thinking_msg.delete()
        
        # Отправляем ответ
        response_text = f"{author['name']}\n\n{response}\n\n<code>💭 Продолжайте диалог или используйте кнопки</code>"
        
        await message.answer(
            response_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard()
        )
        
        # Сохраняем в историю
        db.update_conversation(user_id, author_key, user_text, response)
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(
            "⚠️ <b>Произошла ошибка!</b>\n\nПопробуйте:\n1. Перезапустить бота /start\n2. Задать вопрос по-другому",
            parse_mode=ParseMode.HTML
        )

# ========== ЗАПУСК БОТА ==========
async def main():
    """Запуск бота"""
    print("=" * 50)
    print("🚀 ЗАПУСК ЛИТЕРАТУРНОГО БОТА")
    print("=" * 50)
    print(f"🤖 Бот: {'✅ Токен загружен' if BOT_TOKEN else '❌ Токен не найден'}")
    print(f"🧠 ИИ: {'✅ GigaChat доступен' if gigachat_client.client else '❌ GigaChat недоступен'}")
    print("=" * 50)
    print("\n🎯 Основные команды:")
    print("• /start - Начать диалог")
    print("• /help - Помощь")
    print("• /authors - Список писателей")
    print("=" * 50)
    
    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_router(router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    print("\n✅ Бот запущен! Ожидает сообщений...")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
