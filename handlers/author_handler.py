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
    
    # Приветствия от разных авторов
    greetings = {
        "pushkin": "Друзья мои, прекрасен наш союз! О чём желаете побеседовать?",
        "dostoevsky": "Здравствуйте. Что тревожит вашу душу? Я готов выслушать.",
        "tolstoy": "Здравствуйте, друг мой. О чём вы хотели бы поговорить?",
        "gogol": "А, вот и вы! Ну что, обсудим странности бытия?",
        "chekhov": "Здравствуйте. Рассказывайте, я слушаю внимательно.",
        "esenin": "Здравствуйте, мой друг. О чём бы вы хотели поговорить?",
        "bulgakov": "Добрый день. Наконец-то цивилизованный разговор!",
        "akhmatova": "Здравствуйте. Что привело вас ко мне в этот час?"
    }
    
    greeting = greetings.get(author_key, f"Здравствуйте! Я {author['name']}. Рад нашей беседе.")
    
    await callback.message.edit_text(
        f"<b>{author['emoji']} Вы выбрали: {author['name']}</b>\n\n"
        f"<i>{author['description']}</i>\n\n"
        f"<blockquote>{greeting}</blockquote>\n\n"
        f"<b>Теперь задавайте вопросы!</b>\n\n"
        f"<code>💡 Совет: Задавайте конкретные вопросы для более точных ответов</code>",
        reply_markup=get_chat_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer(f"Вы выбрали {author['name']}")

@router.callback_query(F.data == "change_author")
async def change_author(callback: CallbackQuery):
    """Смена автора"""
    await callback.message.edit_text(
        "👥 <b>Выберите нового писателя для диалога:</b>\n\n"
        "С кем бы вы хотели побеседовать?",
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
            "История очищена. Вы можете начать разговор заново.\n\n"
            "Задавайте вопросы или выберите другого автора.",
            reply_markup=get_chat_keyboard(),
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.message.answer(
            "Сначала выберите автора для диалога.",
            reply_markup=get_authors_keyboard(),
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
    
    # Детальная информация об авторе
    author_details = {
        "pushkin": """
<b>Александр Сергеевич Пушкин</b>
<code>1799-1837</code>

<i>Основные произведения:</i>
• Евгений Онегин (роман в стихах)
• Капитанская дочка (исторический роман)  
• Пиковая дама (повесть)
• Борис Годунов (трагедия)
• Руслан и Людмила (поэма)

<i>Интересные факты:</i>
• Родился в Москве в дворянской семье
• Учился в Царскосельском лицее (1811-1817)
• Был сослан на юг за вольнодумные стихи
• Женился на Наталье Гончаровой (1831)
• Погиб на дуэли с Жоржем Дантесом (1837)
• Считается основоположником современного русского литературного языка
""",
        "dostoevsky": """
<b>Фёдор Михайлович Достоевский</b>
<code>1821-1881</code>

<i>Основные произведения:</i>
• Преступление и наказание (1866)
• Идиот (1869)
• Бесы (1872)
• Братья Карамазовы (1880)

<i>Интересные факты:</i>
• Был приговорён к смертной казни за участие в кружке Петрашевского
• В последний момент приговор заменили на 4 года каторги
• Страдал эпилепсией с детства
• Играл в рулетку, что привело к большим долгам
• Редактировал журналы "Время" и "Эпоха"
• Похоронен на Тихвинском кладбище в Санкт-Петербурге
"""
    }
    
    detail = author_details.get(author_key, 
        f"<b>{author['name']}</b>\n"
        f"<code>{author['description']}</code>\n\n"
        f"Вы можете задать вопросы о жизни и творчестве этого писателя."
    )
    
    await callback.message.answer(detail, parse_mode=ParseMode.HTML)
    await callback.answer()

@router.callback_query(F.data == "all_authors")
async def all_authors(callback: CallbackQuery):
    """Показать всех авторов"""
    await callback.message.answer(
        "👥 <b>Все доступные писатели:</b>\n\n"
        "Выберите автора для диалога:",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    """Помощь через callback"""
    from handlers.start_handler import help_command
    await help_command(callback.message)
    await callback.answer()

@router.callback_query(F.data == "stats")
async def stats_callback(callback: CallbackQuery):
    """Статистика"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    
    stats_text = f"""
<b>📊 Ваша статистика:</b>

💬 Сообщений в диалоге: <b>{len(user_data['conversation_history']) // 2}</b>
📚 Всего сообщений: <b>{user_data['message_count']}</b>
👤 Выбранный автор: <b>{AUTHORS.get(user_data.get('selected_author', ''), {}).get('name', 'не выбран')}</b>
📅 Дата регистрации: <b>{user_data['created_at'][:10]}</b>
"""
    
    await callback.message.answer(stats_text, parse_mode=ParseMode.HTML)
    await callback.answer()
