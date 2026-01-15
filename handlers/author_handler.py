from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.enums import ParseMode

from keyboards.inline_keyboards import get_authors_keyboard, get_chat_keyboard, AUTHORS
from services.database import db

router = Router()

@router.callback_query(F.data.startswith("author_"))
async def select_author(callback: CallbackQuery):
    """Выбор автора"""
    author_key = callback.data.split("_")[1]
    
    if author_key not in AUTHORS:
        await callback.answer("Автор не найден")
        return
    
    author = AUTHORS[author_key]
    user_id = callback.from_user.id
    
    # Получаем данные пользователя
    user_data = db.get_user_data(user_id)
    user_data["selected_author"] = author_key
    db.save_user_data(user_id, user_data)
    
    # Приветствия
    greetings = {
        "pushkin": "Друзья мои, прекрасен наш союз! О чём желаете побеседовать?",
        "dostoevsky": "Здравствуйте. Что тревожит вашу душу?",
        "tolstoy": "Здравствуйте, друг мой. О чём поговорим?",
        "gogol": "А, вот и вы! Ну что, обсудим странности бытия?",
        "chekhov": "Здравствуйте. Рассказывайте, я слушаю."
    }
    
    greeting = greetings.get(author_key, f"Здравствуйте! Я {author['name']}. Рад нашей беседе.")
    
    await callback.message.edit_text(
        f"<b>{author['emoji']} Вы выбрали: {author['name']}</b>\n\n"
        f"<i>{author['description']}</i>\n\n"
        f"<blockquote>{greeting}</blockquote>\n\n"
        f"<b>Теперь задавайте вопросы!</b>",
        reply_markup=get_chat_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer(f"Вы выбрали {author['name']}")

@router.callback_query(F.data == "change_author")
async def change_author(callback: CallbackQuery):
    """Смена автора"""
    await callback.message.edit_text(
        "👥 <b>Выберите нового писателя:</b>",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "reset_chat")
async def reset_chat(callback: CallbackQuery):
    """Сброс диалога"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    author_key = user_data.get("selected_author", "pushkin")
    
    if author_key in AUTHORS:
        author = AUTHORS[author_key]
        
        # Сбрасываем диалог
        db.reset_conversation(user_id)
        
        await callback.message.answer(
            f"🔄 <b>Диалог с {author['name']} сброшен!</b>\n\n"
            "История очищена. Задавайте вопросы заново.",
            reply_markup=get_chat_keyboard(),
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer("Диалог сброшен")

@router.callback_query(F.data == "about_author")
async def about_author(callback: CallbackQuery):
    """Информация о текущем авторе"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    author_key = user_data.get("selected_author")
    
    if not author_key or author_key not in AUTHORS:
        await callback.answer("Сначала выберите автора")
        return
    
    author = AUTHORS[author_key]
    
    # Отправляем информацию ОТДЕЛЬНЫМ сообщением
    await callback.message.answer(
        f"<b>{author['name']}</b>\n"
        f"<i>{author['description']}</i>\n\n"
        "Задавайте вопросы о жизни и творчестве этого писателя.",
        reply_markup=get_chat_keyboard(),  # Возвращаем кнопки управления
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    """Помощь через callback"""
    from handlers.start_handler import help_command
    await help_command(callback.message)
    await callback.answer()
