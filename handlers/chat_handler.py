from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ParseMode

from keyboards.inline_keyboards import get_chat_keyboard, AUTHORS
from services.database import db
from services.gemini_client import gemini_client

router = Router()

@router.message(F.text)
async def handle_message(message: Message):
    """Обработка текстовых сообщений"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    
    # Проверяем, выбран ли автор
    author_key = user_data.get("selected_author")
    if not author_key or author_key not in AUTHORS:
        await message.answer(
            "⚠️ <b>Сначала выберите писателя!</b>\n\n"
            "Используйте команду /start для выбора автора.",
            parse_mode=ParseMode.HTML
        )
        return
    
    author = AUTHORS[author_key]
    
    # Показываем статус "печатает"
    typing_msg = await message.answer(
        f"✍️ <i>{author['name']} обдумывает ответ...</i>",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Получаем историю диалога
        history = user_data.get("conversation_history", [])
        
        # Форматируем историю для Gemini
        formatted_history = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "assistant"
            formatted_history.append({"role": role, "content": msg["content"]})
        
        # Генерируем ответ через Gemini
        response = await gemini_client.generate_author_response(
            author_key=author_key,
            author_name=author["name"],
            user_message=message.text,
            conversation_history=formatted_history
        )
        
        # Обновляем историю в базе данных
        db.update_conversation(user_id, author_key, message.text, response)
        
        # Удаляем сообщение "печатает"
        await typing_msg.delete()
        
        # ===== ИСПРАВЛЕНИЕ: Отделяем ответ персонажа от интерфейса =====
        
        # 1. Сначала отправляем ответ персонажа
        await message.answer(
            f"<b>{author['emoji']} {author['name']}:</b>\n\n{response}",
            parse_mode=ParseMode.HTML
        )
        
        # 2. Отдельным сообщением отправляем инструкцию с кнопками
        await message.answer(
            "👇 <b>Что дальше?</b>",
            reply_markup=get_chat_keyboard(),
            parse_mode=ParseMode.HTML
        )
        # ===== КОНЕЦ ИСПРАВЛЕНИЯ =====
        
    except Exception as e:
        # Удаляем сообщение "печатает" в случае ошибки
        try:
            await typing_msg.delete()
        except:
            pass
        
        await message.answer(
            "❌ <b>Произошла ошибка</b>\n\n"
            "Попробуйте:\n"
            "1. Перезапустить бота: /start\n"
            "2. Задать вопрос иначе\n"
            "3. Подождать несколько минут",
            parse_mode=ParseMode.HTML
        )
