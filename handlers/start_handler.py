from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode

from keyboards.inline_keyboards import get_authors_keyboard, AUTHORS

router = Router()

@router.message(CommandStart())
async def start_command(message: Message):
    """Обработчик команды /start"""
    
    welcome_text = f"""
<b>📚 Литературный Диалог</b>

👋 Привет, {message.from_user.first_name}!

Я могу представить любого русского классика.
Выберите писателя и задайте ему любой вопрос.

👇 <b>Выберите автора для диалога:</b>
"""
    
    await message.answer(
        welcome_text,
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("help"))
async def help_command(message: Message):
    """Команда /help"""
    help_text = """
<b>📖 Помощь по боту</b>

<b>Как использовать:</b>
1. Выберите писателя из списка
2. Задавайте вопросы в свободной форме
3. Получайте ответы от лица автора

<b>Примеры вопросов:</b>
• "Расскажи о своём детстве"
• "Какое твоё самое известное произведение?"
• "Что ты думаешь о современных писателях?"

<b>Команды:</b>
/start - Начать диалог
/help - Эта справка  
/authors - Список писателей
/reset - Сбросить диалог
"""
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@router.message(Command("authors"))
async def authors_command(message: Message):
    """Команда /authors"""
    await message.answer(
        "👥 <b>Выберите писателя для диалога:</b>",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("reset"))
async def reset_command(message: Message):
    """Команда /reset"""
    from services.database import db
    db.reset_conversation(message.from_user.id)
    
    await message.answer(
        "🔄 <b>Диалог сброшен!</b>\n\n"
        "История разговора очищена. Выберите автора для нового диалога.",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
