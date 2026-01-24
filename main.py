import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import db
from authors import get_author, list_author_keys
from inline_keyboards import get_authors_keyboard, get_chat_keyboard
from gigachat_client import gigachat_client
from rate_limit import RateLimitConfig, InMemoryRateLimiter, AntiFloodMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    db.reset_compare(user_id)

    user_name = message.from_user.first_name if message.from_user else "Друг"
    text = (
        f"✨ <b>ЛИТЕРАТУРНЫЙ ДИАЛОГ</b> ✨\n\n"
        f"👋 <b>Привет, {user_name}!</b>\n\n"
        "🎭 Выбери автора и задавай вопросы — отвечу в его стиле.\n\n"
        "👇 <b>Выберите автора:</b>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_authors_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "❓ <b>Помощь</b>\n\n"
        "1) Выбери автора\n"
        "2) Пиши вопрос обычным сообщением\n"
        "3) Кнопки снизу: смена автора / новый диалог / сравнение / очистка\n",
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "change_author")
async def change_author(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.reset_compare(user_id)
    await callback.message.edit_text(
        "👥 <b>Выберите автора:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "reset_chat")
async def reset_chat(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.reset_dialog(user_id, keep_author=True)
    await callback.message.edit_text(
        "🔄 <b>Диалог очищен.</b>\n\nМожешь продолжать общение.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard()
    )
    await callback.answer("Готово")


@router.callback_query(F.data == "clear_all")
async def clear_all(callback: CallbackQuery):
    """
    Полная очистка: никаких кнопок, только /start
    """
    user_id = callback.from_user.id
    db.clear_all(user_id)

    await callback.message.edit_text(
        "🧹 <b>Чат полностью очищен.</b>\n\n"
        "Чтобы начать заново, нажмите:\n\n"
        "<code>/start</code>",
        parse_mode=ParseMode.HTML
        # reply_markup НЕ ДАЁМ -> кнопок не будет
    )
    await callback.answer("Очищено")


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    await cmd_start(callback.message)
    await callback.answer()


@router.callback_query(F.data == "compare_authors")
async def cb_compare_authors(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)

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
    user_id = callback.from_user.id
    author_key = callback.data.split("_", 1)[1]

    if author_key not in list_author_keys():
        await callback.answer("Автор не найден", show_alert=True)
        return

    user_data = db.get_user_data(user_id)
    mode = user_data.get("mode")

    # ----- режим сравнения -----
    if mode == "compare_first":
        db.set_compare_first_author(user_id, author_key)
        db.set_mode(user_id, "compare_second")

        await callback.message.edit_text(
            f"🆚 <b>СРАВНЕНИЕ АВТОРОВ</b>\n\n"
            f"Первый выбран: <b>{get_author(author_key).get('name', author_key)}</b>\n\n"
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

        narrator = user_data.get("selected_author")
        db.reset_compare(user_id)

        await callback.message.edit_text("✨ <i>Сравниваю…</i>", parse_mode=ParseMode.HTML)

        try:
            compare_text = await gigachat_client.compare_authors(
                narrator_author_key=narrator,
                a1=first,
                a2=second
            )
        except Exception as e:
            logger.exception("Ошибка сравнения: %s", e)
            compare_text = "⚠️ Не получилось сравнить авторов. Попробуйте ещё раз."

        await callback.message.edit_text(
            compare_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard()
        )
        await callback.answer("Готово")
        return

    # ----- обычный выбор автора -----
    user_data["selected_author"] = author_key
    db.save_user_data(user_id, user_data)

    author = get_author(author_key)
    await callback.message.edit_text(
        f"{author.get('name', author_key)}\n\n"
        f"💬 {author.get('greeting','Здравствуйте!')}\n\n"
        f"<i>Задавайте вопросы — отвечу в своём стиле!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard()
    )
    await callback.answer("Выбран")


@router.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_text = (message.text or "").strip()
    if not user_text:
        return

    user_data = db.get_user_data(user_id)

    # если пользователь в режиме сравнения — просим выбрать кнопками
    if user_data.get("mode") in ("compare_first", "compare_second"):
        await message.answer(
            "🆚 Вы в режиме сравнения. Выберите автора кнопками 👇",
            parse_mode=ParseMode.HTML,
            reply_markup=get_authors_keyboard()
        )
        return

    author_key = user_data.get("selected_author")
    if not author_key:
        await message.answer(
            "❌ <b>Сначала выберите автора!</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_authors_keyboard()
        )
        return

    author = get_author(author_key)
    thinking = await message.answer(
        f"<i>✨ {author.get('name', author_key)} обдумывает ответ...</i>",
        parse_mode=ParseMode.HTML
    )

    try:
        response = await gigachat_client.generate_response(
            author_key=author_key,
            user_message=user_text,
            conversation_history=user_data.get("conversation_history", [])
        )

        try:
            await thinking.delete()
        except Exception:
            pass

        await message.answer(
            f"{author.get('name', author_key)}\n\n{response}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard()
        )

        db.update_conversation(user_id, author_key, user_text, response)

    except Exception as e:
        logger.exception("Ошибка: %s", e)
        try:
            await thinking.delete()
        except Exception:
            pass
        await message.answer(
            "⚠️ <b>Произошла ошибка.</b>\nПопробуйте ещё раз или нажмите /start",
            parse_mode=ParseMode.HTML
        )


async def main():
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN пуст. Добавь BOT_TOKEN в переменные окружения / .env")

    bot = Bot(token=BOT_TOKEN)  # aiogram v3: parse_mode сюда не передаём
    dp = Dispatcher()

    # антифлуд
    limiter = InMemoryRateLimiter(RateLimitConfig())
    dp.message.middleware(AntiFloodMiddleware(limiter))

    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
