import asyncio
import logging
import sys
from keyboards.inline_keyboards import get_authors_keyboard, get_author_gallery_keyboard
from keyboards.quiz_keyboards import get_quiz_start_keyboard, get_quiz_question_keyboard
from services.daily_quotes import daily_quotes
from services.statistics import stats_service
from services.quiz_service import quiz_service
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import BOT_TOKEN, GIGACHAT_CREDENTIALS
from services.gigachat_client import GigaChatClient

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ========== ИНИЦИАЛИЗАЦИЯ КЛИЕНТОВ ==========

# GigaChat клиент
gigachat_client = GigaChatClient(GIGACHAT_CREDENTIALS)

# База данных (пока простой словарь)
user_storage = {}

def get_user_data(user_id: int) -> dict:
    """Получает данные пользователя"""
    if user_id not in user_storage:
        user_storage[user_id] = {
            "selected_author": None,
            "gigachad_mode": False,
            "conversation_history": [],
            "message_count": 0
        }
    return user_storage[user_id]

# ========== КЛАВИАТУРЫ ==========

def get_authors_keyboard():
    """Клавиатура выбора автора"""
    builder = InlineKeyboardBuilder()
    
    authors = [
        ("🖋️ Пушкин", "pushkin"),
        ("📚 Достоевский", "dostoevsky"),
        ("✍️ Толстой", "tolstoy"),
        ("👻 Гоголь", "gogol"),
        ("🏥 Чехов", "chekhov"),
        ("💪 ГИГАЧАД", "gigachad")
    ]
    
    for text, data in authors:
        builder.button(text=text, callback_data=f"author_{data}")
    
    builder.adjust(2)
    
    # Добавляем кнопки управления
    builder.row(
        builder.button(text="❓ Помощь", callback_data="help"),
        builder.button(text="📊 Статистика", callback_data="stats")
    )
    
    return builder.as_markup()

def get_chat_keyboard(user_id: int):
    """Клавиатура во время диалога"""
    builder = InlineKeyboardBuilder()
    
    user_data = get_user_data(user_id)
    gigachad_mode = user_data.get("gigachad_mode", False)
    
    buttons = [
        ("👥 Сменить автора", "change_author"),
        ("🔄 Сбросить чат", "reset_chat"),
        ("📖 Об авторе", "about_author"),
        ("📋 Список авторов", "list_authors")
    ]
    
    for text, data in buttons:
        builder.button(text=text, callback_data=data)
    
    builder.adjust(2)
    
    # Кнопка режима Гигачад
    if gigachad_mode:
        builder.row(
            builder.button(text="👑 Гигачад ВКЛ", callback_data="toggle_gigachad")
        )
    else:
        builder.row(
            builder.button(text="💪 Включить Гигачад", callback_data="toggle_gigachad")
        )
    
    return builder.as_markup()

# ========== ОБРАБОТЧИКИ ==========

router = Router()

@router.message(CommandStart())
async def start_cmd(message: Message):
    """Обработчик /start"""
    await message.answer(
        "📚 <b>Добро пожаловать в Литературный Диалог!</b>\n\n"
        "Выберите писателя для беседы:\n\n"
        "<i>Теперь с поддержкой GigaChat и режимом 💪 ГИГАЧАД!</i>",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("gigachad"))
async def gigachad_cmd(message: Message):
    """Быстрая команда для Гигачада"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    user_data["selected_author"] = "gigachad"
    user_data["gigachad_mode"] = True
    user_data["conversation_history"] = []
    
    await message.answer(
        "💪 <b>РЕЖИМ ГИГАЧАД АКТИВИРОВАН!</b>\n\n"
        "<i>Мотивационные ответы на литературные темы</i>\n\n"
        "🔥 <b>Задавайте вопросы:</b>\n"
        "• О литературе и книгах\n"
        "• О саморазвитии\n"
        "• О жизни и философии\n\n"
        "<code>Получайте мощные мотивирующие ответы! 🚀</code>",
        reply_markup=get_chat_keyboard(user_id),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data.startswith("author_"))
async def select_author(callback: CallbackQuery):
    """Выбор автора"""
    author_key = callback.data.split("_")[1]
    
    author_names = {
        "pushkin": ("Александр Пушкин", "Приветствую вас! О чём желаете побеседовать?"),
        "dostoevsky": ("Фёдор Достоевский", "Здравствуйте. Что тревожит вашу душу?"),
        "tolstoy": ("Лев Толстой", "Здравствуйте. Говорите правду — я слушаю."),
        "gogol": ("Николай Гоголь", "А, вот и вы! Что привело вас в мой мир?"),
        "chekhov": ("Антон Чехов", "Здравствуйте. Рассказывайте."),
        "gigachad": ("💪 ГИГАЧАД", f"СЛУШАЙ СЮДА, {callback.from_user.first_name.upper()}! Готов к вопросам! 💪")
    }
    
    author_name, greeting = author_names.get(author_key, ("Писатель", "Рад беседе!"))
    
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    user_data["selected_author"] = author_key
    user_data["conversation_history"] = []
    
    await callback.message.edit_text(
        f"✅ <b>Выбран: {author_name}</b>\n\n{greeting}\n\n"
        f"<i>Задавайте любые вопросы:</i>",
        reply_markup=get_chat_keyboard(user_id),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.message(F.text)
async def handle_message(message: Message):
    """Обработка текстовых сообщений"""
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    author_key = user_data.get("selected_author")
    
    if not author_key:
        await message.answer(
            "⚠️ <b>Сначала выберите писателя!</b>\n\n"
            "Используйте /start для выбора автора.",
            reply_markup=get_authors_keyboard()
        )
        return
    
    author_names = {
        "pushkin": "Пушкин",
        "dostoevsky": "Достоевский",
        "tolstoy": "Толстой",
        "gogol": "Гоголь",
        "chekhov": "Чехов",
        "gigachad": "💪 ГИГАЧАД"
    }
    
    author_name = author_names.get(author_key, "Писатель")
    
    # Показываем статус
    status_msg = await message.answer(f"✍️ <i>{author_name} обдумывает ответ...</i>", parse_mode=ParseMode.HTML)
    
    # Генерируем ответ
    response = await gigachat_client.generate_response(
        author_key=author_key,
        author_name=author_name,
        user_message=message.text,
        conversation_history=user_data.get("conversation_history", []),
        gigachad_mode=user_data.get("gigachad_mode", False)
    )
    
    # Обновляем историю
    user_data["conversation_history"].append({
        "role": "user",
        "content": message.text
    })
    user_data["conversation_history"].append({
        "role": "assistant",
        "content": response
    })
    user_data["message_count"] += 1
    
    # Ограничиваем историю
    if len(user_data["conversation_history"]) > 10:
        user_data["conversation_history"] = user_data["conversation_history"][-10:]
    
    # Удаляем статус и отправляем ответ
    await status_msg.delete()
    
    if author_key == "gigachad" or user_data.get("gigachad_mode"):
        await message.answer(
            f"<b>💪 {author_name}:</b>\n\n{response}\n\n"
            f"<i>Следующий вопрос? Жги! 🔥</i>",
            reply_markup=get_chat_keyboard(user_id),
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer(
            f"<b>{author_name}:</b>\n\n{response}\n\n"
            f"<i>Продолжим беседу?</i>",
            reply_markup=get_chat_keyboard(user_id),
            parse_mode=ParseMode.HTML
        )

@router.callback_query(F.data == "toggle_gigachad")
async def toggle_gigachad(callback: CallbackQuery):
    """Переключение режима Гигачад"""
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    
    current_mode = user_data.get("gigachad_mode", False)
    user_data["gigachad_mode"] = not current_mode
    
    if not current_mode:
        await callback.message.answer(
            "👑 <b>РЕЖИМ ГИГАЧАД ВКЛЮЧЁН!</b>\n\n"
            "Теперь все ответы будут мотивационными и уверенными!",
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.message.answer(
            "👌 <b>Режим Гигачад отключён</b>\n\n"
            "Возвращаемся к обычному стилю.",
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()

# После существующих обработчиков добавляем:

@router.callback_query(F.data == "authors_gallery")
async def show_authors_gallery(callback: CallbackQuery):
    """Показывает галерею портретов авторов"""
    await callback.message.edit_text(
        "🖼️ <b>ГАЛЕРЕЯ ПОРТРЕТОВ АВТОРОВ</b>\n\n"
        "Нажмите на кнопку ниже, чтобы увидеть портрет писателя:",
        reply_markup=get_author_gallery_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "back_to_authors")
async def back_to_authors(callback: CallbackQuery):
    """Возврат к выбору авторов"""
    await callback.message.edit_text(
        "📚 <b>ВЫБЕРИТЕ СОБЕСЕДНИКА:</b>\n\n"
        "С кем хотите побеседовать сегодня?",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "quiz_start")
async def start_quiz_menu(callback: CallbackQuery):
    """Меню выбора викторины"""
    await callback.message.answer(
        "🎯 <b>ЛИТЕРАТУРНАЯ ВИКТОРИНА</b>\n\n"
        "Проверьте свои знания о русской классике!\n\n"
        "<b>Выберите сложность:</b>",
        reply_markup=get_quiz_start_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data.startswith("quiz_"))
async def handle_quiz(callback: CallbackQuery):
    """Обработчик викторины"""
    action = callback.data
    
    if action in ["quiz_easy", "quiz_medium", "quiz_hard"]:
        difficulty = action.split("_")[1]
        question = quiz_service.start_quiz(callback.from_user.id, difficulty)
        
        if question:
            await callback.message.answer(
                f"🎯 <b>ВОПРОС {question['number']}/{question['total']}</b>\n"
                f"<i>Сложность: {question['difficulty'].upper()}</i>\n\n"
                f"<b>{question['question']}</b>\n",
                reply_markup=get_quiz_question_keyboard(question['options']),
                parse_mode=ParseMode.HTML
            )
        else:
            await callback.message.answer("❌ Не удалось начать викторину")
    
    elif action.startswith("quiz_answer_"):
        answer_index = int(action.split("_")[2])
        is_correct, correct_answer = quiz_service.answer_question(callback.from_user.id, answer_index)
        
        if is_correct:
            await callback.answer("✅ Правильно!", show_alert=True)
        else:
            await callback.answer(f"❌ Неправильно! Правильный ответ: {correct_answer}", show_alert=True)
        
        # Получаем следующий вопрос
        next_question = quiz_service.get_current_question(callback.from_user.id)
        
        if next_question:
            await callback.message.answer(
                f"🎯 <b>ВОПРОС {next_question['number']}/{next_question['total']}</b>\n\n"
                f"<b>{next_question['question']}</b>\n",
                reply_markup=get_quiz_question_keyboard(next_question['options']),
                parse_mode=ParseMode.HTML
            )
        else:
            # Викторина завершена
            results = quiz_service.finish_quiz(callback.from_user.id)
            
            results_text = f"""
🏆 <b>ВИКТОРИНА ЗАВЕРШЕНА!</b>
<code>{'═' * 35}</code>

📊 <b>Результаты:</b>
✅ Правильных ответов: {results['correct_answers']}/{results['total_questions']}
⭐ Набрано очков: {results['score']}
📈 Процент правильных: {results['percentage']:.1f}%

🎖️ <b>Оценка:</b> {results['grade']} {results['grade_emoji']}

<code>{'═' * 35}</code>
<code>Отличная работа! Продолжайте изучать классику! 📚</code>
"""
            await callback.message.answer(results_text, parse_mode=ParseMode.HTML)
    
    await callback.answer()

# Обновляем обработчик /stats
@router.message(Command("stats"))
async def command_stats(message: Message):
    """Показывает красивую статистику"""
    stats_text = stats_service.format_user_stats(
        message.from_user.id,
        message.from_user.first_name
    )
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

# Добавляем команду для цитаты дня
@router.message(Command("quote"))
async def command_quote(message: Message):
    """Показывает цитату дня"""
    quote = daily_quotes.get_random_quote()
    
    quote_text = f"""
📖 <b>ЦИТАТА ДНЯ</b>
<code>{'═' * 35}</code>

<blockquote>"{quote['text']}"</blockquote>

<code>{'═' * 35}</code>
<code>✨ Вдохновляйтесь и читайте больше!</code>
"""
    
    await message.answer(quote_text, parse_mode=ParseMode.HTML)
    
# Остальные обработчики (change_author, reset_chat, help, stats и т.д.)
# ... (можно добавить из предыдущего кода)

async def main():
    """Основная функция запуска"""
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    
    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК ЛИТЕРАТУРНОГО БОТА (GigaChat)")
    logger.info(f"🤖 Бот токен: {BOT_TOKEN[:15]}...")
    logger.info(f"🔑 GigaChat: {'✅' if gigachat_client.available else '❌'}")
    logger.info("=" * 50)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⏹️ Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
