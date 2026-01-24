import asyncio
import logging
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import db
from gigachat_client import gigachat_client

from rate_limit import RateLimitConfig, InMemoryRateLimiter, AntiFloodMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# Авторы (ключи должны совпадать с knowledge_base.py и gigachat_client.py)
AUTHORS = {
    "pushkin": {"name": "🖋️ Александр Пушкин", "greeting": "Здравствуйте! Рад нашей беседе. Что желаете узнать?"},
    "dostoevsky": {"name": "📚 Фёдор Достоевский", "greeting": "Здравствуйте. Что тревожит вашу душу?"},
    "tolstoy": {"name": "✍️ Лев Толстой", "greeting": "Здравствуйте, друг мой. Поговорим о важном?"},
    "gogol": {"name": "👻 Николай Гоголь", "greeting": "А, вот и вы! Любопытно, что вы хотите узнать?"},
    "chekhov": {"name": "🏥 Антон Чехов", "greeting": "Здравствуйте. Рассказывайте. Краткость — сестра таланта."},
    "gigachad": {"name": "💪 ГИГАЧАД", "greeting": "СЛУШАЙ СЮДА! Готов прокачать твой мозг классикой! 🔥"}
}


def get_authors_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    buttons.append([
        InlineKeyboardButton(text="🖋️ Пушкин", callback_data="author_pushkin"),
        InlineKeyboardButton(text="📚 Достоевский", callback_data="author_dostoevsky"),
        InlineKeyboardButton(text="✍️ Толстой", callback_data="author_tolstoy"),
    ])
    buttons.append([
        InlineKeyboardButton(text="👻 Гоголь", callback_data="author_gogol"),
        InlineKeyboardButton(text="🏥 Чехов", callback_data="author_chekhov"),
        InlineKeyboardButton(text="💪 ГИГАЧАД", callback_data="author_gigachad"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_chat_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Сменить автора", callback_data="change_author"),
            InlineKeyboardButton(text="🔄 Новый диалог", callback_data="reset_chat"),
        ],
        [
            InlineKeyboardButton(text="🆚 Сравнить авторов", callback_data="compare_authors"),
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_name = message.from_user.first_name if message.from_user else "Друг"
    welcome_text = f"""
✨ <b>ЛИТЕРАТУРНЫЙ ДИАЛОГ</b> ✨

👋 <b>Привет, {user_name}!</b>

💬 <b>Выберите писателя и задайте ему любой вопрос.</b>

👇 <b>Выберите автора для диалога:</b>
"""
    # сброс режимов сравнения
    db.reset_compare(message.from_user.id)
    await message.answer(welcome_text, parse_mode=ParseMode.HTML, reply_markup=get_authors_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
📚 <b>ПОМОЩЬ ПО БОТУ</b>

1) Выбери автора
2) Пиши вопросы
3) Кнопки:
   • 👥 смена автора
   • 🔄 новый диалог
   • 🆚 сравнение авторов

<i>Бот использует ИИ + базу знаний (RAG).</i>
"""
    await message.answer(help_text, parse_mode=ParseMode.HTML)


@router.message(Command("authors"))
async def cmd_authors(message: Message):
    db.reset_compare(message.from_user.id)
    await message.answer(
        "👥 <b>ВСЕ ПИСАТЕЛИ</b>\n\nВыберите автора:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard()
    )


@router.callback_query(F.data == "compare_authors")
async def cb_compare_authors(callback: CallbackQuery):
    """
    Начинаем режим сравнения: сначала выбираем первого автора.
    """
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)

    # если у пользователя не выбран "голос" автора — попросим сначала выбрать
    if not user_data.get("selected_author"):
        await callback.message.edit_text(
            "❌ Сначала выбери автора для диалога (он будет «голосом» сравнения).\n\nВыбери автора:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_authors_keyboard()
        )
        await callback.answer()
        return

    db.set_mode(user_id, "compare_first")
    db.set_compare_first_author(user_id, None)

    await callback.message.edit_text(
        "🆚 <b>СРАВНЕНИЕ АВТОРОВ</b>\n\nВыбери <b>первого</b> автора:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("author_"))
async def author_selected(callback: CallbackQuery):
    author_key = callback.data.split("_", 1)[1]
    user_id = callback.from_user.id

    if author_key not in AUTHORS:
        await callback.answer("Автор не найден")
        return

    user_data = db.get_user_data(user_id)
    mode = user_data.get("mode")

    # ----- РЕЖИМ СРАВНЕНИЯ -----
    if mode == "compare_first":
        db.set_compare_first_author(user_id, author_key)
        db.set_mode(user_id, "compare_second")

        await callback.message.edit_text(
            f"🆚 <b>СРАВНЕНИЕ АВТОРОВ</b>\n\n"
            f"Первый выбран: <b>{AUTHORS[author_key]['name']}</b>\n\n"
            f"Теперь выбери <b>второго</b> автора:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_authors_keyboard()
        )
        await callback.answer("Первый выбран")
        return

    if mode == "compare_second":
        first = user_data.get("compare_first_author")
        second = author_key

        if not first:
            # вдруг потерялось состояние
            db.set_mode(user_id, "compare_first")
            await callback.message.edit_text(
                "⚠️ Потерял выбор первого автора. Выбери первого автора заново:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_authors_keyboard()
            )
            await callback.answer()
            return

        if first == second:
            await callback.answer("Нужно выбрать двух разных авторов", show_alert=True)
            return

        # выходим из режима сравнения
        db.reset_compare(user_id)

        narrator = user_data.get("selected_author")  # кто “говорит” стиль
        thinking = await callback.message.edit_text(
            "✨ <i>Сравниваю…</i>",
            parse_mode=ParseMode.HTML
        )

        try:
            compare_text = await gigachat_client.compare_authors(narrator_author_key=narrator, a1=first, a2=second)
        except Exception as e:
            logger.error(f"Ошибка сравнения: {e}")
            compare_text = "⚠️ Не получилось сравнить авторов. Попробуйте ещё раз."

        # показываем результат
        await thinking.edit_text(
            compare_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard()
        )
        await callback.answer("Готово")
        return

    # ----- ОБЫЧНЫЙ ВЫБОР АВТОРА -----
    user_data["selected_author"] = author_key
    db.save_user_data(user_id, user_data)

    author = AUTHORS[author_key]
    await callback.message.edit_text(
        f"{author['name']}\n\n💬 {author['greeting']}\n\n<i>Задавайте вопросы — отвечу в своём стиле!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard()
    )
    await callback.answer(f"Выбран: {author['name']}")


@router.callback_query(F.data == "change_author")
async def change_author(callback: CallbackQuery):
    db.reset_compare(callback.from_user.id)
    await callback.message.edit_text(
        "👥 <b>ВЫБЕРИТЕ НОВОГО АВТОРА:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "reset_chat")
async def reset_chat(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)

    user_data["conversation_history"] = []
    user_data["selected_author"] = None
    user_data["mode"] = None
    user_data["compare_first_author"] = None
    db.save_user_data(user_id, user_data)

    await callback.message.edit_text(
        "🔄 <b>Диалог сброшен!</b>\n\nВыберите нового автора:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard()
    )
    await callback.answer("Диалог сброшен")


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    db.reset_compare(callback.from_user.id)
    await cmd_start(callback.message)
    await callback.answer()


@router.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)

    # если пользователь в режиме сравнения — просим завершить кнопками
    if user_data.get("mode") in ("compare_first", "compare_second"):
        await message.answer(
            "🆚 Вы в режиме сравнения. Выберите автора кнопками 👇",
            parse_mode=ParseMode.HTML,
            reply_markup=get_authors_keyboard()
        )
        return

    if not user_data.get("selected_author"):
        await message.answer(
            "❌ <b>Сначала выберите автора!</b>\n\nИспользуйте кнопки ниже:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_authors_keyboard()
        )
        return

    author_key = user_data["selected_author"]
    author = AUTHORS.get(author_key)
    user_text = message.text

    thinking_msg = await message.answer(
        f"<i>✨ {author['name']} обдумывает ответ...</i>",
        parse_mode=ParseMode.HTML
    )

    try:
        response = await gigachat_client.generate_response(
            author_key=author_key,
            user_message=user_text,
            conversation_history=user_data.get("conversation_history", [])
        )

        try:
            await thinking_msg.delete()
        except Exception:
            pass

        response_text = f"{author['name']}\n\n{response}\n\n<code>💭 Продолжайте диалог или используйте кнопки</code>"

        await message.answer(
            response_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard()
        )

        db.update_conversation(user_id, author_key, user_text, response)

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(
            "⚠️ <b>Произошла ошибка!</b>\n\nПопробуйте:\n1) /start\n2) переформулировать вопрос",
            parse_mode=ParseMode.HTML
        )


async def main():
    print("=" * 50)
    print("🚀 ЗАПУСК ЛИТЕРАТУРНОГО БОТА")
    print("=" * 50)

    # aiogram v3: parse_mode НЕ передаём в Bot()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # антифлуд (если у тебя уже есть rate_limit.py)
    limiter = InMemoryRateLimiter(RateLimitConfig())
    dp.message.middleware(AntiFloodMiddleware(limiter))

    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Бот запущен! Ожидает сообщений...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
