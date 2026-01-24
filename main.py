import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import db
from gigachat_client import gigachat_client
from inline_keyboards import (
    get_main_menu_keyboard,
    get_authors_keyboard,
    get_chat_keyboard,
)
from authors import get_author, list_author_keys
from knowledge_base import get_writer_knowledge

from rate_limit import RateLimitConfig, InMemoryRateLimiter, AntiFloodMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


def _author_label(author_key: str) -> str:
    a = get_author(author_key) or {}
    return a.get("name") or author_key


def _render_stats(user_id: int) -> str:
    s = db.get_stats(user_id)
    fav = s.get("favorite_author")
    fav_name = _author_label(fav) if fav else "—"
    cur = s.get("selected_author")
    cur_name = _author_label(cur) if cur else "—"

    return (
        "📊 <b>Моя статистика</b>\n\n"
        f"💬 Сообщений от тебя: <b>{s.get('total_user_messages', 0)}</b>\n"
        f"🤖 Ответов бота: <b>{s.get('total_bot_messages', 0)}</b>\n"
        f"🔄 Сбросов диалога: <b>{s.get('dialog_resets', 0)}</b>\n"
        f"⭐ Любимый автор: <b>{fav_name}</b>\n"
        f"🎭 Сейчас выбран: <b>{cur_name}</b>\n"
    )


def _render_about_author(author_key: str) -> str:
    kb = get_writer_knowledge(author_key) or {}
    if not kb:
        return "ℹ️ Информации об этом авторе пока нет."

    name = kb.get("full_name") or author_key
    birth = kb.get("birth", {}) if isinstance(kb.get("birth"), dict) else {}
    death = kb.get("death", {}) if isinstance(kb.get("death"), dict) else {}
    works = kb.get("major_works", [])
    facts = kb.get("interesting_facts", [])

    lines = [f"ℹ️ <b>{name}</b>\n"]
    if birth:
        lines.append(f"🎂 Рождение: <b>{birth.get('date','')}</b> — {birth.get('place','')}".strip())
    if death:
        lines.append(f"🕯 Смерть: <b>{death.get('date','')}</b> — {death.get('place','')}".strip())

    if works:
        lines.append("\n📚 <b>Главные произведения:</b>")
        for w in works[:6]:
            lines.append(f"• {w}")

    if facts:
        lines.append("\n✨ <b>Интересные факты:</b>")
        for f in facts[:4]:
            lines.append(f"• {f}")

    return "\n".join(lines).strip()


@router.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "✨ <b>ЛИТЕРАТУРНЫЙ ДИАЛОГ</b> ✨\n\n"
        "🎭 Выбери автора и задавай вопросы — отвечу в его стиле.\n"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_main_menu_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "❓ <b>Помощь</b>\n\n"
        "1) Нажми «Выбрать автора»\n"
        "2) Пиши вопросы обычным сообщением\n"
        "3) Используй кнопки для смены автора и сброса диалога\n\n"
        "⚡ Антифлуд включён — не спамь сообщениями подряд.\n",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(),
    )


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "❓ <b>Помощь</b>\n\n"
        "• Выбери автора\n"
        "• Пиши вопрос\n"
        "• Кнопки снизу: смена автора / новый диалог / инфо / статистика\n",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ <b>О боте</b>\n\n"
        "Это литературный чат-бот: выбираешь автора и общаешься в его стиле.\n"
        "Работает через GigaChat и сохраняет историю диалога.\n",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.in_({"select_author", "all_authors", "list_authors", "change_author"}))
async def cb_list_authors(callback: CallbackQuery):
    await callback.message.edit_text(
        "👥 <b>Выберите автора</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🏠 <b>Главное меню</b>\n\nВыберите действие:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "stats")
async def cb_stats(callback: CallbackQuery):
    await callback.message.edit_text(
        _render_stats(callback.from_user.id),
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "reset_chat")
async def cb_reset(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.reset_dialog(user_id, keep_author=True)

    await callback.message.edit_text(
        "🔄 <b>Диалог сброшен.</b>\n\nПродолжайте или смените автора.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard(),
    )
    await callback.answer("Готово")


@router.callback_query(F.data == "about_author")
async def cb_about_author(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    author_key = user_data.get("selected_author")

    if not author_key:
        await callback.answer("Сначала выбери автора", show_alert=True)
        return

    await callback.message.edit_text(
        _render_about_author(author_key),
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("author_"))
async def cb_author_selected(callback: CallbackQuery):
    author_key = callback.data.split("_", 1)[1]
    if author_key not in list_author_keys():
        await callback.answer("Автор не найден", show_alert=True)
        return

    db.set_selected_author(callback.from_user.id, author_key)
    author = get_author(author_key)

    await callback.message.edit_text(
        f"{author.get('name', author_key)}\n\n💬 {author.get('greeting','Здравствуйте!')}\n\n"
        "<i>Задавайте вопросы — отвечу в своём стиле!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard(),
    )
    await callback.answer("Выбрано")


@router.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_text = (message.text or "").strip()
    if not user_text:
        return

    user_data = db.get_user_data(user_id)
    author_key = user_data.get("selected_author")

    if not author_key:
        await message.answer(
            "❌ <b>Сначала выберите автора!</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_authors_keyboard(),
        )
        return

    author = get_author(author_key) or {"name": author_key}

    # записываем сообщение пользователя (и статистику)
    db.record_user_message(user_id, author_key, user_text)

    thinking_msg = await message.answer(
        f"<i>✨ {author['name']} обдумывает ответ...</i>",
        parse_mode=ParseMode.HTML,
    )

    try:
        response = await gigachat_client.generate_response(
            author_key=author_key,
            user_message=user_text,
            conversation_history=user_data.get("conversation_history", []),
        )

        db.record_bot_message(user_id, author_key, response)

        try:
            await thinking_msg.delete()
        except Exception:
            pass

        await message.answer(
            f"{author['name']}\n\n{response}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard(),
        )

    except Exception as e:
        logger.exception("Ошибка обработки сообщения: %s", e)
        try:
            await thinking_msg.delete()
        except Exception:
            pass
        await message.answer(
            "⚠️ <b>Произошла ошибка.</b>\nПопробуйте ещё раз или смените автора.",
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard(),
        )


async def main():
    # aiogram v3: parse_mode сюда не передаём
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # ✅ антифлуд
    limiter = InMemoryRateLimiter(RateLimitConfig())
    dp.message.middleware(AntiFloodMiddleware(limiter))

    dp.include_router(router)

    # Для Render worker — polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Бот запущен (polling).")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
