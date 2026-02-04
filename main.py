import os
import asyncio
import logging

from aiohttp import web

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import db
from authors import get_author, list_author_keys
from inline_keyboards import (
    get_groups_keyboard,
    get_authors_keyboard,
    get_chat_keyboard,
    get_cowrite_mode_keyboard,
)
from gigachat_client import gigachat_client
from rate_limit import RateLimitConfig, InMemoryRateLimiter, AntiFloodMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# =========================
# 🛠 Админ-настройки (кнопки видны только админам)
# =========================
def _admins_from_env() -> set[int]:
    raw = (os.getenv("ADMIN_IDS", "") or "").strip()
    if not raw:
        return set()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def is_admin(user_id: int) -> bool:
    return int(user_id) in _admins_from_env()


def _data_dir() -> str:
    path = os.path.join(os.getcwd(), "data")
    os.makedirs(path, exist_ok=True)
    return path


def _load_json(path: str, default):
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, obj) -> None:
    import json
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def track_user(user_id: int) -> None:
    p = os.path.join(_data_dir(), "users.json")
    data = _load_json(p, {"users": []})
    users = set()
    for x in data.get("users", []):
        try:
            users.add(int(x))
        except Exception:
            pass
    if int(user_id) not in users:
        users.add(int(user_id))
        _save_json(p, {"users": sorted(list(users))})


def _banned_path() -> str:
    return os.path.join(_data_dir(), "banned.json")


def get_banned() -> set[int]:
    data = _load_json(_banned_path(), {"banned": []})
    out = set()
    for x in data.get("banned", []):
        try:
            out.add(int(x))
        except Exception:
            pass
    return out


def is_banned(user_id: int) -> bool:
    return int(user_id) in get_banned()


def ban_user(user_id: int) -> None:
    banned = get_banned()
    banned.add(int(user_id))
    _save_json(_banned_path(), {"banned": sorted(list(banned))})


def unban_user(user_id: int) -> None:
    banned = get_banned()
    banned.discard(int(user_id))
    _save_json(_banned_path(), {"banned": sorted(list(banned))})


def get_all_users() -> list[int]:
    p = os.path.join(_data_dir(), "users.json")
    data = _load_json(p, {"users": []})
    out = []
    for x in data.get("users", []):
        try:
            out.append(int(x))
        except Exception:
            pass
    return sorted(list(set(out)))


def get_admin_keyboard():
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="📣 Рассылка", callback_data="admin_broadcast_help"),
    )
    kb.row(
        InlineKeyboardButton(text="🚫 Бан", callback_data="admin_ban_help"),
        InlineKeyboardButton(text="✅ Разбан", callback_data="admin_unban_help"),
    )
    kb.row(InlineKeyboardButton(text="🆔 Мой ID", callback_data="admin_whoami"))
    return kb.as_markup()


# =========================
# 🌐 Мини-сервер, чтобы хостинг видел открытый порт
# =========================
async def start_web_server() -> None:
    """
    Для Render/Railway Web Service: нужно слушать PORT, иначе будет Port scan timeout.
    Этот сервер отвечает 200 OK на / и /health.
    """
    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "10000"))  # Render обычно даёт PORT, иначе 10000
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    logger.info("🌐 Web server started on 0.0.0.0:%s", port)


# =========================
# 🤖 Команды / UI
# =========================
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    track_user(user_id)

    if is_banned(user_id) and not is_admin(user_id):
        await message.answer("🚫 Вы заблокированы администратором.")
        return
    db.reset_compare(user_id)

    user_name = message.from_user.first_name if message.from_user else "Друг"
    text = (
        f"✨ <b>ЛИТЕРАТУРНЫЙ ДИАЛОГ</b> ✨\n\n"
        f"👋 <b>Привет, {user_name}!</b>\n\n"
        "📚 Сначала выбери <b>сборник/эпоху</b>, затем автора.\n"
        "🎭 Пиши вопросы — отвечу в стиле писателя.\n"
        "✍️ Можно писать произведение вместе.\n\n"
        "👇 <b>Выберите эпоху:</b>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_groups_keyboard())

    # Админ-кнопки видны только тебе (ID берётся из переменной окружения ADMIN_IDS)
    if is_admin(user_id):
        await message.answer(
            "🛠 <b>Админ-панель</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "❓ <b>Помощь</b>\n\n"
        "1) Выбери эпоху\n"
        "2) Выбери автора\n"
        "3) Пиши вопрос\n\n"
        "Команда: /start — начать заново.",
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "groups_menu")
async def groups_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.reset_compare(user_id)
    db.set_mode(user_id, None)

    await callback.message.edit_text(
        "👇 <b>Выберите эпоху:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_groups_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("group_"))
async def group_selected(callback: CallbackQuery):
    group_key = callback.data.split("_", 1)[1]
    await callback.message.edit_text(
        "👥 <b>Выберите автора:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard(group_key)
    )
    await callback.answer()


@router.callback_query(F.data == "change_author")
async def change_author(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.reset_compare(user_id)
    db.set_mode(user_id, None)

    await callback.message.edit_text(
        "👇 <b>Выберите эпоху:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_groups_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "reset_chat")
async def reset_chat(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.reset_dialog(user_id, keep_author=True)
    db.set_mode(user_id, None)

    await callback.message.edit_text(
        "🔄 <b>Диалог очищен.</b>\n\nМожешь продолжать общение.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard()
    )
    await callback.answer("Готово")


@router.callback_query(F.data == "clear_all")
async def clear_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.clear_all(user_id)

    await callback.message.edit_text(
        "🧹 <b>Чат полностью очищен.</b>\n\n"
        "Чтобы начать заново, нажмите:\n\n"
        "<code>/start</code>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer("Очищено")


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.reset_compare(user_id)
    db.set_mode(user_id, None)

    await cmd_start(callback.message)
    await callback.answer()


@router.callback_query(F.data == "cowrite")
async def cowrite_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)

    if not user_data.get("selected_author"):
        await callback.message.edit_text(
            "❌ Сначала выбери автора.\n\n👇 Выберите эпоху:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        await callback.answer()
        return

    db.reset_compare(user_id)

    await callback.message.edit_text(
        "✍️ <b>СОАВТОРСТВО</b>\n\n"
        "Что будем писать вместе?",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cowrite_mode_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.in_({"cowrite_prose", "cowrite_poem"}))
async def cowrite_mode_selected(callback: CallbackQuery):
    user_id = callback.from_user.id
    mode = callback.data
    db.set_mode(user_id, mode)

    genre = "рассказ" if mode == "cowrite_prose" else "стихотворение"
    await callback.message.edit_text(
        "✍️ <b>Начинаем!</b>\n\n"
        f"Жанр: <b>{genre}</b>\n\n"
        "Напиши <b>первый фрагмент</b> — я продолжу.\n"
        "<i>Подсказка: 2–6 строк достаточно.</i>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer("Режим включён")


@router.callback_query(F.data == "compare_authors")
async def cb_compare_authors(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)

    if not user_data.get("selected_author"):
        await callback.message.edit_text(
            "❌ Сначала выбери автора для диалога.\n\n👇 Выберите эпоху:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        await callback.answer()
        return

    db.set_mode(user_id, "compare_first")
    db.set_compare_first_author(user_id, None)

    await callback.message.edit_text(
        "🆚 <b>СРАВНЕНИЕ АВТОРОВ</b>\n\nВыберите эпоху первого автора:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_groups_keyboard()
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

    if mode == "compare_first":
        db.set_compare_first_author(user_id, author_key)
        db.set_mode(user_id, "compare_second")

        await callback.message.edit_text(
            f"🆚 <b>СРАВНЕНИЕ АВТОРОВ</b>\n\n"
            f"Первый выбран: <b>{get_author(author_key).get('name', author_key)}</b>\n\n"
            f"Теперь выберите эпоху второго автора:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        await callback.answer("Первый выбран")
        return

    if mode == "compare_second":
        first = user_data.get("compare_first_author")
        second = author_key

        if not first:
            db.set_mode(user_id, "compare_first")
            await callback.message.edit_text(
                "⚠️ Потерял выбор первого автора. Выберите эпоху первого автора заново:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_groups_keyboard()
            )
            await callback.answer()
            return

        if first == second:
            await callback.answer("Нужно выбрать двух разных авторов", show_alert=True)
            return

        narrator = user_data.get("selected_author")
        db.reset_compare(user_id)
        db.set_mode(user_id, None)

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

    # обычный выбор автора
    user_data["selected_author"] = author_key
    db.save_user_data(user_id, user_data)
    db.set_mode(user_id, None)
    db.reset_compare(user_id)

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
    track_user(user_id)

    if is_banned(user_id) and not is_admin(user_id):
        await message.answer("🚫 Вы заблокированы администратором.", parse_mode=ParseMode.HTML)
        return
    user_text = (message.text or "").strip()
    if not user_text:
        return

    user_data = db.get_user_data(user_id)
    mode = user_data.get("mode")

    if mode in ("compare_first", "compare_second"):
        await message.answer(
            "🆚 Вы в режиме сравнения. Выбирайте авторов кнопками 👇",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        return

    author_key = user_data.get("selected_author")
    if not author_key:
        await message.answer(
            "❌ <b>Сначала выберите автора!</b>\n\n👇 Выберите эпоху:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        return

    author = get_author(author_key)

    # соавторство
    if mode in ("cowrite_prose", "cowrite_poem"):
        genre = "рассказ" if mode == "cowrite_prose" else "стихотворение"
        prompt = (
            f"Мы пишем {genre} ВМЕСТЕ.\n"
            "Пользователь написал фрагмент ниже.\n\n"
            "Твоя задача:\n"
            "- органично ПРОДОЛЖИТЬ текст\n"
            "- сохранить стиль выбранного автора\n"
            "- НЕ завершать полностью произведение\n"
            "- оставить пространство для продолжения пользователю\n\n"
            f"ФРАГМЕНТ ПОЛЬЗОВАТЕЛЯ:\n{user_text}"
        )

        thinking = await message.answer(
            f"<i>✍️ {author.get('name', author_key)} продолжает...</i>",
            parse_mode=ParseMode.HTML
        )

        try:
            response = await gigachat_client.generate_response(
                author_key=author_key,
                user_message=prompt,
                conversation_history=[]
            )
            try:
                await thinking.delete()
            except Exception:
                pass

            await message.answer(
                f"{author.get('name', author_key)}:\n\n{response}\n\n"
                "<i>Твоя очередь — допиши следующий фрагмент ✍️</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=get_chat_keyboard()
            )
            db.update_conversation(user_id, author_key, user_text, response)
            return

        except Exception as e:
            logger.exception("Ошибка соавторства: %s", e)
            try:
                await thinking.delete()
            except Exception:
                pass
            await message.answer(
                "⚠️ Не получилось продолжить текст. Попробуйте ещё раз.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_chat_keyboard()
            )
            return

    # обычный чат
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

    # 1) стартуем web-сервер (порт)
    await start_web_server()

    # 2) стартуем бота
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    limiter = InMemoryRateLimiter(RateLimitConfig())
    dp.message.middleware(AntiFloodMiddleware(limiter))

    dp.include_router(router)

    # 🔥 Это лечит "webhook is active"
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("🤖 Start polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
import os
import asyncio
import logging

from aiohttp import web

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.enums import ParseMode

from config import BOT_TOKEN
from database import db
from authors import get_author, list_author_keys
from inline_keyboards import (
    get_groups_keyboard,
    get_authors_keyboard,
    get_chat_keyboard,
    get_cowrite_mode_keyboard,
)
from gigachat_client import gigachat_client
from rate_limit import RateLimitConfig, InMemoryRateLimiter, AntiFloodMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# =========================
# 🛠 Админ-команды (видны только админам)
# =========================
@router.message(Command("whoami"))
async def cmd_whoami(message: Message):
    user_id = message.from_user.id
    track_user(user_id)
    await message.answer(f"🆔 Ваш ID: <code>{user_id}</code>", parse_mode=ParseMode.HTML)


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    user_id = message.from_user.id
    track_user(user_id)
    if not is_admin(user_id):
        await message.answer("⛔ У вас нет доступа к админ-командам.")
        return

    await message.answer(
        "🛠 <b>Админ-панель</b>\n\n"
        "• <code>/stats</code> — статистика\n"
        "• <code>/broadcast ТЕКСТ</code> — рассылка\n"
        "• <code>/ban USER_ID</code> — бан\n"
        "• <code>/unban USER_ID</code> — разбан\n"
        "• <code>/whoami</code> — ваш ID\n",
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_keyboard()
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    user_id = message.from_user.id
    track_user(user_id)
    if not is_admin(user_id):
        await message.answer("⛔ Нет доступа.")
        return

    users = get_all_users()
    banned = get_banned()
    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{len(users)}</b>\n"
        f"🚫 В бане: <b>{len(banned)}</b>\n\n"
        "<i>База пополняется, когда пользователь пишет боту или нажимает /start.</i>",
        parse_mode=ParseMode.HTML
    )


@router.message(Command("ban"))
async def cmd_ban(message: Message):
    user_id = message.from_user.id
    track_user(user_id)
    if not is_admin(user_id):
        await message.answer("⛔ Нет доступа.")
        return

    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: <code>/ban USER_ID</code>", parse_mode=ParseMode.HTML)
        return

    target = int(parts[1])
    ban_user(target)
    await message.answer(f"🚫 Пользователь <code>{target}</code> забанен.", parse_mode=ParseMode.HTML)


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    user_id = message.from_user.id
    track_user(user_id)
    if not is_admin(user_id):
        await message.answer("⛔ Нет доступа.")
        return

    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: <code>/unban USER_ID</code>", parse_mode=ParseMode.HTML)
        return

    target = int(parts[1])
    unban_user(target)
    await message.answer(f"✅ Пользователь <code>{target}</code> разбанен.", parse_mode=ParseMode.HTML)


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    user_id = message.from_user.id
    track_user(user_id)
    if not is_admin(user_id):
        await message.answer("⛔ Нет доступа.")
        return

    payload = (message.text or "").replace("/broadcast", "", 1).strip()
    if not payload:
        await message.answer("Использование: <code>/broadcast ТЕКСТ</code>", parse_mode=ParseMode.HTML)
        return

    users = get_all_users()
    banned = get_banned()

    ok = 0
    fail = 0

    await message.answer(f"📣 Начинаю рассылку… Пользователей: <b>{len(users)}</b>", parse_mode=ParseMode.HTML)

    for uid in users:
        if uid in banned:
            continue
        try:
            await message.bot.send_message(uid, f"📣 <b>Сообщение от администратора</b>\n\n{payload}", parse_mode=ParseMode.HTML)
            ok += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1

    await message.answer(
        "✅ <b>Рассылка завершена</b>\n\n"
        f"Отправлено: <b>{ok}</b>\n"
        f"Не доставлено: <b>{fail}</b>",
        parse_mode=ParseMode.HTML
    )



# =========================
# 🛠 Админ-настройки (кнопки видны только админам)
# =========================
def _admins_from_env() -> set[int]:
    raw = (os.getenv("ADMIN_IDS", "") or "").strip()
    if not raw:
        return set()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def is_admin(user_id: int) -> bool:
    return int(user_id) in _admins_from_env()


def _data_dir() -> str:
    path = os.path.join(os.getcwd(), "data")
    os.makedirs(path, exist_ok=True)
    return path


def _load_json(path: str, default):
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, obj) -> None:
    import json
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def track_user(user_id: int) -> None:
    p = os.path.join(_data_dir(), "users.json")
    data = _load_json(p, {"users": []})
    users = set()
    for x in data.get("users", []):
        try:
            users.add(int(x))
        except Exception:
            pass
    if int(user_id) not in users:
        users.add(int(user_id))
        _save_json(p, {"users": sorted(list(users))})


def _banned_path() -> str:
    return os.path.join(_data_dir(), "banned.json")


def get_banned() -> set[int]:
    data = _load_json(_banned_path(), {"banned": []})
    out = set()
    for x in data.get("banned", []):
        try:
            out.add(int(x))
        except Exception:
            pass
    return out


def is_banned(user_id: int) -> bool:
    return int(user_id) in get_banned()


def ban_user(user_id: int) -> None:
    banned = get_banned()
    banned.add(int(user_id))
    _save_json(_banned_path(), {"banned": sorted(list(banned))})


def unban_user(user_id: int) -> None:
    banned = get_banned()
    banned.discard(int(user_id))
    _save_json(_banned_path(), {"banned": sorted(list(banned))})


def get_all_users() -> list[int]:
    p = os.path.join(_data_dir(), "users.json")
    data = _load_json(p, {"users": []})
    out = []
    for x in data.get("users", []):
        try:
            out.append(int(x))
        except Exception:
            pass
    return sorted(list(set(out)))


def get_admin_keyboard():
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="📣 Рассылка", callback_data="admin_broadcast_help"),
    )
    kb.row(
        InlineKeyboardButton(text="🚫 Бан", callback_data="admin_ban_help"),
        InlineKeyboardButton(text="✅ Разбан", callback_data="admin_unban_help"),
    )
    kb.row(InlineKeyboardButton(text="🆔 Мой ID", callback_data="admin_whoami"))
    return kb.as_markup()


# =========================
# 🌐 Мини-сервер, чтобы хостинг видел открытый порт
# =========================
async def start_web_server() -> None:
    """
    Для Render/Railway Web Service: нужно слушать PORT, иначе будет Port scan timeout.
    Этот сервер отвечает 200 OK на / и /health.
    """
    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "10000"))  # Render обычно даёт PORT, иначе 10000
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    logger.info("🌐 Web server started on 0.0.0.0:%s", port)


# =========================
# 🤖 Команды / UI
# =========================
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    track_user(user_id)

    if is_banned(user_id) and not is_admin(user_id):
        await message.answer("🚫 Вы заблокированы администратором.")
        return
    db.reset_compare(user_id)

    user_name = message.from_user.first_name if message.from_user else "Друг"
    text = (
        f"✨ <b>ЛИТЕРАТУРНЫЙ ДИАЛОГ</b> ✨\n\n"
        f"👋 <b>Привет, {user_name}!</b>\n\n"
        "📚 Сначала выбери <b>сборник/эпоху</b>, затем автора.\n"
        "🎭 Пиши вопросы — отвечу в стиле писателя.\n"
        "✍️ Можно писать произведение вместе.\n\n"
        "👇 <b>Выберите эпоху:</b>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_groups_keyboard())

    # Админ-кнопки видны только тебе (ID берётся из переменной окружения ADMIN_IDS)
    if is_admin(user_id):
        await message.answer(
            "🛠 <b>Админ-панель</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard()
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "❓ <b>Помощь</b>\n\n"
        "1) Выбери эпоху\n"
        "2) Выбери автора\n"
        "3) Пиши вопрос\n\n"
        "Команда: /start — начать заново.",
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "groups_menu")
async def groups_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.reset_compare(user_id)
    db.set_mode(user_id, None)

    await callback.message.edit_text(
        "👇 <b>Выберите эпоху:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_groups_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("group_"))
async def group_selected(callback: CallbackQuery):
    group_key = callback.data.split("_", 1)[1]
    await callback.message.edit_text(
        "👥 <b>Выберите автора:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard(group_key)
    )
    await callback.answer()


@router.callback_query(F.data == "change_author")
async def change_author(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.reset_compare(user_id)
    db.set_mode(user_id, None)

    await callback.message.edit_text(
        "👇 <b>Выберите эпоху:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_groups_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "reset_chat")
async def reset_chat(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.reset_dialog(user_id, keep_author=True)
    db.set_mode(user_id, None)

    await callback.message.edit_text(
        "🔄 <b>Диалог очищен.</b>\n\nМожешь продолжать общение.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard()
    )
    await callback.answer("Готово")


@router.callback_query(F.data == "clear_all")
async def clear_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.clear_all(user_id)

    await callback.message.edit_text(
        "🧹 <b>Чат полностью очищен.</b>\n\n"
        "Чтобы начать заново, нажмите:\n\n"
        "<code>/start</code>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer("Очищено")


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.reset_compare(user_id)
    db.set_mode(user_id, None)

    await cmd_start(callback.message)
    await callback.answer()


@router.callback_query(F.data == "cowrite")
async def cowrite_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)

    if not user_data.get("selected_author"):
        await callback.message.edit_text(
            "❌ Сначала выбери автора.\n\n👇 Выберите эпоху:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        await callback.answer()
        return

    db.reset_compare(user_id)

    await callback.message.edit_text(
        "✍️ <b>СОАВТОРСТВО</b>\n\n"
        "Что будем писать вместе?",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cowrite_mode_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.in_({"cowrite_prose", "cowrite_poem"}))
async def cowrite_mode_selected(callback: CallbackQuery):
    user_id = callback.from_user.id
    mode = callback.data
    db.set_mode(user_id, mode)

    genre = "рассказ" if mode == "cowrite_prose" else "стихотворение"
    await callback.message.edit_text(
        "✍️ <b>Начинаем!</b>\n\n"
        f"Жанр: <b>{genre}</b>\n\n"
        "Напиши <b>первый фрагмент</b> — я продолжу.\n"
        "<i>Подсказка: 2–6 строк достаточно.</i>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer("Режим включён")


@router.callback_query(F.data == "compare_authors")
async def cb_compare_authors(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)

    if not user_data.get("selected_author"):
        await callback.message.edit_text(
            "❌ Сначала выбери автора для диалога.\n\n👇 Выберите эпоху:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        await callback.answer()
        return

    db.set_mode(user_id, "compare_first")
    db.set_compare_first_author(user_id, None)

    await callback.message.edit_text(
        "🆚 <b>СРАВНЕНИЕ АВТОРОВ</b>\n\nВыберите эпоху первого автора:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_groups_keyboard()
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

    if mode == "compare_first":
        db.set_compare_first_author(user_id, author_key)
        db.set_mode(user_id, "compare_second")

        await callback.message.edit_text(
            f"🆚 <b>СРАВНЕНИЕ АВТОРОВ</b>\n\n"
            f"Первый выбран: <b>{get_author(author_key).get('name', author_key)}</b>\n\n"
            f"Теперь выберите эпоху второго автора:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        await callback.answer("Первый выбран")
        return

    if mode == "compare_second":
        first = user_data.get("compare_first_author")
        second = author_key

        if not first:
            db.set_mode(user_id, "compare_first")
            await callback.message.edit_text(
                "⚠️ Потерял выбор первого автора. Выберите эпоху первого автора заново:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_groups_keyboard()
            )
            await callback.answer()
            return

        if first == second:
            await callback.answer("Нужно выбрать двух разных авторов", show_alert=True)
            return

        narrator = user_data.get("selected_author")
        db.reset_compare(user_id)
        db.set_mode(user_id, None)

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

    # обычный выбор автора
    user_data["selected_author"] = author_key
    db.save_user_data(user_id, user_data)
    db.set_mode(user_id, None)
    db.reset_compare(user_id)

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
    track_user(user_id)

    if is_banned(user_id) and not is_admin(user_id):
        await message.answer("🚫 Вы заблокированы администратором.", parse_mode=ParseMode.HTML)
        return
    user_text = (message.text or "").strip()
    if not user_text:
        return

    user_data = db.get_user_data(user_id)
    mode = user_data.get("mode")

    if mode in ("compare_first", "compare_second"):
        await message.answer(
            "🆚 Вы в режиме сравнения. Выбирайте авторов кнопками 👇",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        return

    author_key = user_data.get("selected_author")
    if not author_key:
        await message.answer(
            "❌ <b>Сначала выберите автора!</b>\n\n👇 Выберите эпоху:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        return

    author = get_author(author_key)

    # соавторство
    if mode in ("cowrite_prose", "cowrite_poem"):
        genre = "рассказ" if mode == "cowrite_prose" else "стихотворение"
        prompt = (
            f"Мы пишем {genre} ВМЕСТЕ.\n"
            "Пользователь написал фрагмент ниже.\n\n"
            "Твоя задача:\n"
            "- органично ПРОДОЛЖИТЬ текст\n"
            "- сохранить стиль выбранного автора\n"
            "- НЕ завершать полностью произведение\n"
            "- оставить пространство для продолжения пользователю\n\n"
            f"ФРАГМЕНТ ПОЛЬЗОВАТЕЛЯ:\n{user_text}"
        )

        thinking = await message.answer(
            f"<i>✍️ {author.get('name', author_key)} продолжает...</i>",
            parse_mode=ParseMode.HTML
        )

        try:
            response = await gigachat_client.generate_response(
                author_key=author_key,
                user_message=prompt,
                conversation_history=[]
            )
            try:
                await thinking.delete()
            except Exception:
                pass

            await message.answer(
                f"{author.get('name', author_key)}:\n\n{response}\n\n"
                "<i>Твоя очередь — допиши следующий фрагмент ✍️</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=get_chat_keyboard()
            )
            db.update_conversation(user_id, author_key, user_text, response)
            return

        except Exception as e:
            logger.exception("Ошибка соавторства: %s", e)
            try:
                await thinking.delete()
            except Exception:
                pass
            await message.answer(
                "⚠️ Не получилось продолжить текст. Попробуйте ещё раз.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_chat_keyboard()
            )
            return

    # обычный чат
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

    # 1) стартуем web-сервер (порт)
    await start_web_server()

    # 2) стартуем бота
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    limiter = InMemoryRateLimiter(RateLimitConfig())
    dp.message.middleware(AntiFloodMiddleware(limiter))

    dp.include_router(router)

    # 🔥 Это лечит "webhook is active"
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("🤖 Start polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
