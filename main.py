# main.py
import asyncio
import logging
import time
from typing import Dict, Tuple

from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from config import BOT_TOKEN
from authors import AUTHORS, get_author, list_author_keys
from database import db
from gigachat_client import gigachat_client
from inline_keyboards import (
    get_main_menu_keyboard,
    get_authors_keyboard,
    get_chat_keyboard,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# ---------------- Anti-flood / Rate limit ----------------
# Простая token-bucket защита на пользователя:
# capacity=5 токенов, refill=1 токен/сек, cost=1 токен/сообщение
_RATE: Dict[int, Tuple[float, float]] = {}  # user_id -> (tokens, last_ts)
RATE_CAPACITY = 5.0
RATE_REFILL_PER_SEC = 1.0
RATE_COST = 1.0


def rate_allow(user_id: int) -> bool:
    now = time.time()
    tokens, last = _RATE.get(user_id, (RATE_CAPACITY, now))
    # пополняем
    tokens = min(RATE_CAPACITY, tokens + (now - last) * RATE_REFILL_PER_SEC)
    if tokens >= RATE_COST:
        tokens -= RATE_COST
        _RATE[user_id] = (tokens, now)
        return True
    _RATE[user_id] = (tokens, now)
    return False


# ---------------- Helpers ----------------

def format_author_name(author_key: str) -> str:
    a = get_author(author_key)
    return a.get("name", author_key)


def pretty_stats_text(stats: dict) -> str:
    fav = stats.get("favorite_author")
    selected = stats.get("selected_author")

    fav_text = format_author_name(fav) if fav else "—"
    selected_text = format_author_name(selected) if selected else "—"

    return (
        "📊 <b>ВАША СТАТИСТИКА</b>\n\n"
        f"✉️ Сообщений от вас: <b>{stats.get('total_user_messages', 0)}</b>\n"
        f"🤖 Ответов бота: <b>{stats.get('total_assistant_messages', 0)}</b>\n"
        f"🔄 Сбросов диалога: <b>{stats.get('total_dialog_resets', 0)}</b>\n\n"
        f"⭐ Любимый автор: <b>{fav_text}</b>\n"
        f"🎭 Текущий автор: <b>{selected_text}</b>\n"
    )


# ---------------- Commands ----------------

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_name = message.from_user.first_name if message.from_user else "Друг"
    await db.ensure_user(message.from_user.id)

    welcome_text = (
        "✨ <b>ЛИТЕРАТУРНЫЙ ДИАЛОГ</b> ✨\n\n"
        f"👋 <b>Привет, {user_name}!</b>\n\n"
        "💬 <b>Выберите писателя и задайте ему любой вопрос.</b>\n\n"
        "👇 <b>Главное меню:</b>"
    )

    await message.answer(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📚 <b>ПОМОЩЬ</b>\n\n"
        "1) Выберите автора\n"
        "2) Задавайте вопросы\n"
        "3) Используйте кнопки управления\n\n"
        "💡 Бот использует ИИ (GigaChat) + базу знаний по писателям.\n"
        "Если ИИ недоступен — попробует ответить фактами из базы."
    )
    await message.answer(help_text, parse_mode=ParseMode.HTML, reply_markup=get_main_menu_keyboard())


@router.message(Command("authors"))
async def cmd_authors(message: Message):
    await message.answer(
        "👥 <b>ВЫБЕРИТЕ АВТОРА</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard(),
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    stats = await db.get_stats(message.from_user.id)
    await message.answer(pretty_stats_text(stats), parse_mode=ParseMode.HTML, reply_markup=get_main_menu_keyboard())


# ---------------- Callbacks: menu ----------------

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await cmd_start(callback.message)
    await callback.answer()


@router.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "📚 <b>ПОМОЩЬ</b>\n\n"
        "• 🎭 Выбрать автора — начать диалог\n"
        "• 🔄 Сбросить диалог — очистить историю\n"
        "• 📊 Статистика — посмотреть активность\n\n"
        "Пишите любой вопрос текстом — отвечу от лица автора 🙂",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "about")
async def cb_about(callback: CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ <b>О БОТЕ</b>\n\n"
        "Это литературный Telegram-бот на <b>aiogram 3</b>.\n"
        "Отвечает в стиле русских классиков.\n\n"
        "⚙️ Фишки:\n"
        "• ИИ (GigaChat) + база знаний\n"
        "• SQLite-хранилище истории и статистики\n"
        "• Антифлуд\n"
        "• Кэш ответов\n",
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "select_author")
async def cb_select_author(callback: CallbackQuery):
    await callback.message.edit_text(
        "👥 <b>ВЫБЕРИТЕ АВТОРА</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "list_authors")
async def cb_list_authors(callback: CallbackQuery):
    lines = ["📚 <b>ВСЕ ПИСАТЕЛИ</b>\n"]
    for k in list_author_keys():
        lines.append(f"• {get_author(k).get('name', k)}")
    lines.append("\nНажмите «🎭 Выбрать автора», чтобы начать диалог.")
    await callback.message.edit_text(
        "\n".join(lines),
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "stats")
async def cb_stats(callback: CallbackQuery):
    stats = await db.get_stats(callback.from_user.id)
    await callback.message.edit_text(
        pretty_stats_text(stats),
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_keyboard(),
    )
    await callback.answer()


# ---------------- Callbacks: author selection & dialog management ----------------

@router.callback_query(F.data.startswith("author_"))
async def cb_author_selected(callback: CallbackQuery):
    author_key = callback.data.split("_", 1)[1]
    if author_key not in AUTHORS:
        await callback.answer("Автор не найден")
        return

    await db.set_selected_author(callback.from_user.id, author_key)
    author = get_author(author_key)

    await callback.message.edit_text(
        f"{author['name']}\n\n💬 {author['greeting']}\n\n<i>Задавайте вопросы — отвечу в своём стиле!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard(),
    )
    await callback.answer(f"Выбран: {author['name']}")


@router.callback_query(F.data == "change_author")
async def cb_change_author(callback: CallbackQuery):
    await callback.message.edit_text(
        "👥 <b>ВЫБЕРИТЕ НОВОГО АВТОРА</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "reset_chat")
async def cb_reset_chat(callback: CallbackQuery):
    await db.reset_dialog(callback.from_user.id)
    await db.set_selected_author(callback.from_user.id, None)
    await callback.message.edit_text(
        "🔄 <b>Диалог сброшен!</b>\n\nВыберите автора:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard(),
    )
    await callback.answer("Диалог сброшен")


# ---------------- Messages ----------------

@router.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id

    # антифлуд
    if not rate_allow(user_id):
        await message.answer("🛑 Слишком быстро 🙂 Подожди секунду и попробуй ещё раз.")
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
    user_text = message.text.strip()

    thinking_msg = await message.answer(
        f"<i>✨ {author['name']} обдумывает ответ...</i>",
        parse_mode=ParseMode.HTML,
    )

    try:
        history = await db.get_conversation_history(user_id, limit_pairs=4)

        response = await gigachat_client.generate_response(
            author_key=author_key,
            user_message=user_text,
            conversation_history=history,
            cache_ttl_seconds=3600,
        )

        await thinking_msg.delete()

        # сохраняем
        await db.add_message(user_id, author_key, "user", user_text)
        await db.add_message(user_id, author_key, "assistant", response)

        response_text = (
            f"{author['name']}\n\n{response}\n\n"
            "<code>💭 Продолжайте диалог или используйте кнопки</code>"
        )
        await message.answer(
            response_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard(),
        )

    except Exception as e:
        logger.exception(f"Ошибка обработки сообщения: {e}")
        try:
            await thinking_msg.delete()
        except Exception:
            pass
        await message.answer(
            "⚠️ <b>Произошла ошибка!</b>\n\n"
            "Попробуйте:\n"
            "1) /start\n"
            "2) переформулировать вопрос",
            parse_mode=ParseMode.HTML,
            reply_markup=get_main_menu_keyboard(),
        )


# ---------------- Startup ----------------

async def main():
    print("=" * 50)
    print("🚀 ЗАПУСК ЛИТЕРАТУРНОГО БОТА")
    print("=" * 50)

    await db.init()
    # периодически чистим протухший кэш (можно редко — тут разово при старте)
    await db.cache_cleanup()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    print("✅ Бот запущен! Ожидает сообщений...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
