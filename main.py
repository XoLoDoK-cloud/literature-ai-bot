# main.py
import asyncio
import logging
import os
from aiohttp import web

from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, Update

from config import BOT_TOKEN
from database import db
from authors import get_author, list_author_keys
from inline_keyboards import (
    get_main_menu_keyboard,
    get_authors_keyboard,
    get_chat_keyboard,
)
from gigachat_client import gigachat_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

WEBHOOK_PATH = "/webhook"


# ----------------- helpers -----------------
def _safe_author_name(author_key: str | None) -> str:
    if not author_key:
        return "—"
    a = get_author(author_key) or {}
    return a.get("name") or f"👤 {author_key}"


def _render_stats(stats: dict) -> str:
    fav_name = _safe_author_name(stats.get("favorite_author"))
    return (
        "📊 <b>Моя статистика</b>\n\n"
        f"💬 Сообщений от тебя: <b>{stats.get('total_user_messages', 0)}</b>\n"
        f"🤖 Ответов бота: <b>{stats.get('total_assistant_messages', 0)}</b>\n"
        f"🔄 Сбросов диалога: <b>{stats.get('total_dialog_resets', 0)}</b>\n"
        f"⭐ Любимый автор: <b>{fav_name}</b>\n"
    )


def _get_base_url() -> str | None:
    # Render Web Service
    host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if host:
        return f"https://{host}"

    # Ручной вариант (если деплоишь не на Render)
    manual = os.getenv("WEBHOOK_BASE_URL")
    if manual:
        return manual.rstrip("/")

    return None


# ----------------- commands -----------------
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_name = message.from_user.first_name if message.from_user else "Друг"
    text = (
        f"✨ <b>ЛИТЕРАТУРНЫЙ ДИАЛОГ</b> ✨\n\n"
        f"👋 <b>Привет, {user_name}!</b>\n\n"
        "🎭 Выбери писателя и задавай вопросы — я отвечу в его стиле.\n\n"
        "Нажми: <b>🎭 Выбрать автора</b>\n"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "❓ <b>Помощь</b>\n\n"
        "1) Выбери автора\n"
        "2) Пиши вопросы обычным сообщением\n"
        "3) Используй кнопки: сменить автора / сброс / статистика\n\n"
        "💡 Если ИИ недоступен — бот ответит фактами из базы знаний.\n"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_main_menu_keyboard())


@router.message(Command("authors"))
async def cmd_authors(message: Message):
    await message.answer(
        "👥 <b>Выберите автора</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard(),
    )


# ----------------- menu callbacks -----------------
@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.in_({"select_author", "list_authors"}))
async def cb_select_author(callback: CallbackQuery):
    await callback.message.edit_text(
        "👥 <b>Выберите автора</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "❓ <b>Помощь</b>\n\n"
        "• Выбери автора\n"
        "• Пиши вопросы обычным сообщением\n"
        "• Кнопки снизу помогают управлять диалогом\n",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ <b>О боте</b>\n\n"
        "Литературный чат-бот: выбираешь автора и общаешься в его стиле.\n"
        "Использует GigaChat + базу знаний + кэш.\n",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


# ----------------- author selection -----------------
@router.callback_query(F.data.startswith("author_"))
async def author_selected(callback: CallbackQuery):
    author_key = callback.data.split("_", 1)[1]

    if author_key not in list_author_keys():
        await callback.answer("Автор не найден", show_alert=True)
        return

    author = get_author(author_key)
    user_id = callback.from_user.id

    # ✅ НОВЫЙ API БД (SQLite)
    await db.set_selected_author(user_id, author_key)

    await callback.message.edit_text(
        f"{author['name']}\n\n💬 {author['greeting']}\n\n<i>Задавайте вопросы — отвечу в своём стиле!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard(),
    )
    await callback.answer(f"Выбран: {author['name']}")


@router.callback_query(F.data == "change_author")
async def change_author(callback: CallbackQuery):
    await callback.message.edit_text(
        "👥 <b>Выберите автора</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard(),
    )
    await callback.answer()


# ----------------- stats / reset -----------------
@router.callback_query(F.data == "stats")
async def cb_stats(callback: CallbackQuery):
    stats = await db.get_stats(callback.from_user.id)
    await callback.message.edit_text(
        _render_stats(stats),
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "reset_chat")
async def reset_chat(callback: CallbackQuery):
    user_id = callback.from_user.id

    # запоминаем выбранного автора, чтобы не заставлять выбирать снова
    author_key = await db.get_selected_author(user_id)

    await db.reset_dialog(user_id)

    if author_key:
        await db.set_selected_author(user_id, author_key)

    await callback.message.edit_text(
        "🔄 <b>Диалог сброшен.</b>\n\nПродолжайте или смените автора.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard() if author_key else get_main_menu_keyboard(),
    )
    await callback.answer("Диалог сброшен")


# ----------------- message handler -----------------
@router.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    text = (message.text or "").strip()
    if not text:
        return

    author_key = await db.get_selected_author(user_id)
    if not author_key:
        await message.answer(
            "❌ <b>Сначала выберите автора!</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_authors_keyboard(),
        )
        return

    author = get_author(author_key)

    # сохраняем сообщение пользователя
    await db.add_message(user_id, author_key, "user", text)

    # история диалога из БД
    history = await db.get_conversation_history(user_id, limit_pairs=4)

    thinking = await message.answer(
        f"<i>✨ {author['name']} обдумывает ответ...</i>",
        parse_mode=ParseMode.HTML,
    )

    try:
        answer = await gigachat_client.generate_response(
            author_key=author_key,
            user_message=text,
            conversation_history=history,
        )

        # сохраняем ответ ассистента
        await db.add_message(user_id, author_key, "assistant", answer)

        await thinking.delete()

        await message.answer(
            f"{author['name']}\n\n{answer}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard(),
        )
    except Exception as e:
        logger.exception("Ошибка генерации ответа: %s", e)
        try:
            await thinking.delete()
        except Exception:
            pass
        await message.answer(
            "⚠️ <b>Произошла ошибка.</b>\nПопробуйте ещё раз или смените автора.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard(),
        )


# ----------------- webhook server -----------------
async def handle_webhook(request: web.Request) -> web.Response:
    update = Update.model_validate(await request.json())
    await request.app["dp"].feed_update(request.app["bot"], update)
    return web.Response(text="ok")


async def health(request: web.Request) -> web.Response:
    return web.Response(text="ok")


async def on_startup(app: web.Application):
    await db.init()

    bot: Bot = app["bot"]
    base_url = app.get("base_url")
    if base_url:
        webhook_url = base_url + WEBHOOK_PATH
        # ✅ это убирает polling-конфликты навсегда
        await bot.delete_webhook(drop_pending_updates=True)
        await bot.set_webhook(webhook_url)
        logger.info("✅ Webhook установлен: %s", webhook_url)
    else:
        logger.info("ℹ️ Webhook URL не найден — стартуем polling")


async def on_shutdown(app: web.Application):
    bot: Bot = app["bot"]
    try:
        await bot.delete_webhook()
    except Exception:
        pass


async def run_webhook(dp: Dispatcher, bot: Bot, base_url: str, port: int):
    app = web.Application()
    app["bot"] = bot
    app["dp"] = dp
    app["base_url"] = base_url

    app.router.add_get("/health", health)
    app.router.add_post(WEBHOOK_PATH, handle_webhook)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info("🚀 Бот запущен (webhook) на порту %s", port)
    await asyncio.Event().wait()


async def run_polling(dp: Dispatcher, bot: Bot):
    await db.init()
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass
    logger.info("🚀 Бот запущен (polling)")
    await dp.start_polling(bot)


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    base_url = _get_base_url()
    port = int(os.getenv("PORT", "10000"))

    if base_url:
        await run_webhook(dp, bot, base_url, port)
    else:
        await run_polling(dp, bot)


if __name__ == "__main__":
    asyncio.run(main())
