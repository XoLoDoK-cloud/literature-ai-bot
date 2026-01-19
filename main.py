# ========== main.py ==========
import asyncio
import logging
import sys
import random
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode

from config import BOT_TOKEN, GIGACHAT_CREDENTIALS
from database import db
from gigachat_client import GigaChatClient
from keyboards import get_main_menu_keyboard, get_authors_keyboard, get_chat_keyboard

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Инициализация клиентов
gigachat_client = GigaChatClient(GIGACHAT_CREDENTIALS)

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

# ========== КОМАНДЫ ==========
@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start"""
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
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    logger.info(f"👤 Старт: {user_id} (@{message.from_user.username})")

@router.message(Command("gigachad"))
async def cmd_gigachad(message: Message):
    """Быстрая команда для режима Гигачада"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    
    # Устанавливаем Гигачада как автора
    user_data["selected_author"] = "gigachad"
    user_data["gigachad_mode"] = True
    user_data["conversation_history"] = []
    db.save_user_data(user_id, user_data)
    
    author = AUTHORS["gigachad"]
    
    await message.answer(
        f"💪 <b>РЕЖИМ ГИГАЧАД АКТИВИРОВАН!</b>\n\n"
        f"<i>{author['description']}</i>\n\n"
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

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
<b>📖 ПОМОЩЬ ПО БОТУ</b>

<b>Основные команды:</b>
/start - Выбор автора
/gigachad - Режим Гигачада
/authors - Список писателей
/reset - Сбросить диалог
/stats - Статистика

<b>💡 Как работает:</b>
• Выбираете автора
• Задаете вопросы в свободной форме
• Получаете ответы от лица автора
• История диалога сохраняется

<b>👑 Доступные авторы:</b>
• Александр Пушкин
• Фёдор Достоевский
• Лев Толстой
• Николай Гоголь
• Антон Чехов
• Гигачад (мотивационный режим)

<b>⚙️ Технологии:</b>
• GigaChat AI (российская нейросеть)
• Сохранение истории диалога
"""
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@router.message(Command("authors"))
async def cmd_authors(message: Message):
    """Список доступных авторов"""
    authors_list = "<b>👑 ДОСТУПНЫЕ АВТОРЫ:</b>\n\n"
    
    for key, info in AUTHORS.items():
        if key == "gigachad":
            authors_list += f"<b>💪 {info['name']}</b> - <i>мотивационный режим</i>\n"
        else:
            authors_list += f"<b>{info['emoji']} {info['name']}</b>\n"
        
        authors_list += f"<i>{info['birth']} • {info['description']}</i>\n\n"
    
    authors_list += "👇 <b>Выберите автора:</b>"
    
    await message.answer(
        authors_list,
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("reset"))
async def cmd_reset(message: Message):
    """Сброс диалога"""
    user_id = message.from_user.id
    db.reset_conversation(user_id)
    
    await message.answer(
        "🔄 <b>Диалог сброшен!</b>\n\n"
        "История разговора очищена. Выберите автора для нового диалога.",
        reply_markup=get_authors_keyboard()
    )
    
    logger.info(f"🔄 Сброс диалога: {user_id}")

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    """Статистика бота"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    
    stats_text = f"""
<b>📊 ВАША СТАТИСТИКА</b>

👤 <b>Пользователь:</b> {user_data.get('first_name', 'Читатель')}
💬 <b>Сообщений:</b> {user_data.get('message_count', 0)}
📅 <b>На сайте с:</b> {datetime.fromisoformat(user_data['created_at']).strftime('%d.%m.%Y')}
"""
    
    if user_data.get("selected_author"):
        author = AUTHORS.get(user_data["selected_author"], AUTHORS["pushkin"])
        stats_text += f"🎭 <b>Текущий автор:</b> {author['emoji']} {author['name']}\n"
    
    # Считаем количество уникальных авторов
    author_counts = {}
    for msg in user_data.get("conversation_history", []):
        if msg["role"] == "assistant":
            # Анализируем текст для определения автора
            text = msg["content"].lower()
            if "пушкин" in text or "александр" in text:
                author_counts["pushkin"] = author_counts.get("pushkin", 0) + 1
            elif "достоевск" in text:
                author_counts["dostoevsky"] = author_counts.get("dostoevsky", 0) + 1
            elif "толст" in text:
                author_counts["tolstoy"] = author_counts.get("tolstoy", 0) + 1
            elif "гогол" in text:
                author_counts["gogol"] = author_counts.get("gogol", 0) + 1
            elif "чехов" in text:
                author_counts["chekhov"] = author_counts.get("chekhov", 0) + 1
            elif "гигачад" in text.lower() or "gigachad" in text.lower():
                author_counts["gigachad"] = author_counts.get("gigachad", 0) + 1
    
    if author_counts:
        stats_text += f"\n<b>🎭 АКТИВНОСТЬ ПО АВТОРАМ:</b>\n"
        for author_key, count in sorted(author_counts.items(), key=lambda x: x[1], reverse=True):
            author = AUTHORS.get(author_key, {"name": author_key, "emoji": "📖"})
            stats_text += f"{author['emoji']} {author['name']}: {count} сообщ.\n"
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

# ========== CALLBACK ОБРАБОТЧИКИ ==========
@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    """Главное меню"""
    await callback.message.edit_text(
        "🎭 <b>ГЛАВНОЕ МЕНЮ</b>\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "select_author")
async def select_author_callback(callback: CallbackQuery):
    """Выбор автора"""
    await callback.message.edit_text(
        "👥 <b>ВЫБЕРИТЕ АВТОРА:</b>\n\n"
        "С кем хотите побеседовать?",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data.startswith("author_"))
async def author_selected_callback(callback: CallbackQuery):
    """Выбор конкретного автора"""
    author_key = callback.data.split("_")[1]
    
    if author_key not in AUTHORS:
        await callback.answer("Автор не найден")
        return
    
    author = AUTHORS[author_key]
    user_id = callback.from_user.id
    
    # Сохраняем выбор в базе
    user_data = db.get_user_data(user_id)
    user_data["selected_author"] = author_key
    user_data["conversation_history"] = []  # Начинаем новый диалог
    db.save_user_data(user_id, user_data)
    
    # Приветствия
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
        user_data["gigachad_mode"] = True
        db.save_user_data(user_id, user_data)
        
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
        user_data["gigachad_mode"] = False
        db.save_user_data(user_id, user_data)
        
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

@router.callback_query(F.data == "change_author")
async def change_author_callback(callback: CallbackQuery):
    """Смена автора"""
    await callback.message.edit_text(
        "👥 <b>ВЫБЕРИТЕ НОВОГО АВТОРА:</b>\n\n"
        "С кем хотите побеседовать?",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "reset_chat")
async def reset_chat_callback(callback: CallbackQuery):
    """Сброс диалога"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    
    db.reset_conversation(user_id)
    
    author_key = user_data.get("selected_author", "pushkin")
    author = AUTHORS.get(author_key, AUTHORS["pushkin"])
    
    await callback.message.edit_text(
        f"🔄 <b>Диалог с {author['name']} сброшен!</b>\n\n"
        "История очищена. Можете начать заново.",
        reply_markup=get_chat_keyboard(include_gigachad_mode=(author_key=="gigachad")),
        parse_mode=ParseMode.HTML
    )
    await callback.answer("Диалог сброшен! 🔄")

@router.callback_query(F.data == "about_author")
async def about_author_callback(callback: CallbackQuery):
    """Информация о текущем авторе"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    author_key = user_data.get("selected_author")
    
    if not author_key:
        await callback.answer("Сначала выберите автора")
        return
    
    author = AUTHORS.get(author_key, AUTHORS["pushkin"])
    
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

@router.callback_query(F.data == "list_authors")
async def list_authors_callback(callback: CallbackQuery):
    """Список авторов"""
    await cmd_authors(callback.message)
    await callback.answer()

@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    """Помощь"""
    await cmd_help(callback.message)
    await callback.answer()

@router.callback_query(F.data == "stats")
async def stats_callback(callback: CallbackQuery):
    """Статистика"""
    await cmd_stats(callback.message)
    await callback.answer()

@router.callback_query(F.data == "toggle_gigachad_style")
async def toggle_gigachad_callback(callback: CallbackQuery):
    """Переключение режима Гигачада"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    
    current_mode = user_data.get("gigachad_mode", False)
    user_data["gigachad_mode"] = not current_mode
    db.save_user_data(user_id, user_data)
    
    if not current_mode:
        await callback.message.answer(
            "💪 <b>РЕЖИМ ГИГАЧАД АКТИВИРОВАН!</b>\n\n"
            "Теперь все ответы будут мотивационными и уверенными!",
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.message.answer(
            "👌 <b>РЕЖИМ ГИГАЧАД ОТКЛЮЧЁН</b>\n\n"
            "Возвращаемся к обычному стилю общения.",
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()

# ========== ОБРАБОТЧИК СООБЩЕНИЙ ==========
@router.message(F.text)
async def handle_message(message: Message):
    """Обработка всех текстовых сообщений"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    
    # Проверяем, выбран ли автор
    if not user_data.get("selected_author"):
        await message.answer(
            "⚠️ <b>Сначала выберите писателя!</b>\n\n"
            "Используйте кнопку ниже для выбора автора.",
            reply_markup=get_authors_keyboard()
        )
        return
    
    author_key = user_data["selected_author"]
    author = AUTHORS.get(author_key, AUTHORS["pushkin"])
    
    # Показываем статус "печатает"
    status_text = f"✍️ {author['name']} обдумывает ответ..."
    if author_key == "gigachad":
        status_text = f"💪 {author['name']} качает мозг..."
    
    status_msg = await message.answer(
        f"<i>{status_text}</i>",
        parse_mode=ParseMode.HTML
    )
    
    try:
        # Получаем историю диалога
        conversation_history = user_data.get("conversation_history", [])
        
        # Генерируем ответ
        response = await gigachat_client.generate_response(
            author_key=author_key,
            author_name=author['name'],
            user_message=message.text,
            conversation_history=conversation_history,
            gigachad_mode=user_data.get("gigachad_mode", False),
            what_if_mode=user_data.get("what_if_mode", False)
        )
        
        # ОБНОВЛЯЕМ БАЗУ ДАННЫХ - это ключевое исправление!
        db.update_conversation(
            user_id=user_id,
            author_key=author_key,
            user_message=message.text,
            bot_response=response
        )
        
        # Обновляем локальные данные
        user_data = db.get_user_data(user_id)
        
        # Удаляем статус
        await status_msg.delete()
        
        # Форматируем ответ в зависимости от автора
        if author_key == "gigachad" or user_data.get("gigachad_mode", False):
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
        except:
            pass
        
        error_text = f"""
⚠️ <b>ОШИБКА:</b>

Не удалось получить ответ от автора.

Попробуйте:
1. Переформулировать вопрос
2. Использовать /reset для сброса диалога
3. Подождать несколько минут

<code>Техническая информация: {str(e)[:100]}</code>
"""
        await message.answer(error_text, parse_mode=ParseMode.HTML)
        logger.error(f"Ошибка обработки сообщения {user_id}: {e}")

# ========== ЗАПУСК БОТА ==========
async def main():
    """Запуск бота"""
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    
    # Информация о запуске
    logger.info("=" * 60)
    logger.info("🚀 ЗАПУСК ЛИТЕРАТУРНОГО БОТА")
    logger.info(f"🤖 Бот: {BOT_TOKEN[:15]}...")
    logger.info(f"🔑 GigaChat: {'✅ Активен' if gigachat_client.available else '❌ Недоступен'}")
    logger.info("💾 База данных: JSON файлы")
    logger.info("=" * 60)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
