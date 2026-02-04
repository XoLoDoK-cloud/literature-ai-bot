# main.py
import os
import asyncio
import logging
import atexit
import signal
import time
from typing import Set, Any, Dict

from aiohttp import web

from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

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
# 🔒 Single-instance lock (защита от двойного polling)
# =========================
LOCK_PATH = os.getenv("BOT_LOCK_PATH", "/tmp/literature_bot.lock")
LOCK_STALE_SECONDS = int(os.getenv("BOT_LOCK_STALE_SECONDS", "1800"))  # 30 минут


def acquire_single_instance_lock() -> int:
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    try:
        fd = os.open(LOCK_PATH, flags)
        payload = f"pid={os.getpid()}\nstarted={int(time.time())}\n"
        os.write(fd, payload.encode("utf-8"))
        return fd
    except FileExistsError:
        try:
            age = time.time() - os.path.getmtime(LOCK_PATH)
            if age > LOCK_STALE_SECONDS:
                logger.warning("🧹 Lock старый (%.0fs). Удаляю...", age)
                try:
                    os.remove(LOCK_PATH)
                except Exception:
                    pass
                fd = os.open(LOCK_PATH, flags)
                payload = f"pid={os.getpid()}\nstarted={int(time.time())}\n"
                os.write(fd, payload.encode("utf-8"))
                return fd
        except Exception:
            pass

        raise RuntimeError(
            "Бот уже запущен в другом процессе (TelegramConflictError). "
            "Останови второй запуск/деплой или дождись завершения старого процесса."
        )


def release_single_instance_lock(fd: int) -> None:
    try:
        os.close(fd)
    except Exception:
        pass
    try:
        os.remove(LOCK_PATH)
    except Exception:
        pass


# =========================
# 🛠 Админ-настройки
# =========================
def _admins_from_env() -> Set[int]:
    raw = (os.getenv("ADMIN_IDS", "") or "").strip()
    if not raw:
        return set()
    out: Set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def is_admin(user_id: int) -> bool:
    return int(user_id) in _admins_from_env()


# =========================
# 💾 Простая локальная "БД" на JSON (users + stats)
# =========================
def _data_dir() -> str:
    path = os.path.join(os.getcwd(), "data")
    os.makedirs(path, exist_ok=True)
    return path


def _load_json(path: str, default: Any):
    try:
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, obj: Any) -> None:
    import json
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ---------- users ----------
def _users_path() -> str:
    return os.path.join(_data_dir(), "users.json")


def track_user(user_id: int) -> None:
    p = _users_path()
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


def get_all_users() -> list[int]:
    data = _load_json(_users_path(), {"users": []})
    out: list[int] = []
    for x in data.get("users", []):
        try:
            out.append(int(x))
        except Exception:
            pass
    return sorted(list(set(out)))


# ---------- stats ----------
def _stats_path() -> str:
    return os.path.join(_data_dir(), "stats.json")


def _stats_default() -> Dict[str, Any]:
    return {
        "users_last_seen": {},     # user_id -> unix_ts
        "usernames": {},           # user_id -> username (без @)
        "messages_total": 0,
        "messages_by_user": {},    # user_id -> count
        "commands": {},            # "/start" -> count
        "authors_selected": {},    # "pushkin" -> count
    }


def _load_stats() -> Dict[str, Any]:
    return _load_json(_stats_path(), _stats_default())


def _save_stats(stats: Dict[str, Any]) -> None:
    _save_json(_stats_path(), stats)


def mark_seen(user_id: int, username: str | None = None) -> None:
    stats = _load_stats()

    stats.setdefault("users_last_seen", {})
    stats.setdefault("usernames", {})

    uid = str(int(user_id))
    stats["users_last_seen"][uid] = int(time.time())

    if username:
        stats["usernames"][uid] = username

    _save_stats(stats)


def inc_message(user_id: int) -> None:
    stats = _load_stats()

    stats["messages_total"] = int(stats.get("messages_total", 0)) + 1

    stats.setdefault("messages_by_user", {})
    uid = str(int(user_id))
    stats["messages_by_user"][uid] = int(stats["messages_by_user"].get(uid, 0)) + 1

    _save_stats(stats)


def inc_command(cmd: str) -> None:
    stats = _load_stats()
    stats.setdefault("commands", {})
    stats["commands"][cmd] = int(stats["commands"].get(cmd, 0)) + 1
    _save_stats(stats)


def inc_author_selected(author_key: str) -> None:
    stats = _load_stats()
    stats.setdefault("authors_selected", {})
    stats["authors_selected"][author_key] = int(stats["authors_selected"].get(author_key, 0)) + 1
    _save_stats(stats)


def _count_active(stats: Dict[str, Any], seconds: int) -> int:
    now = int(time.time())
    last_seen = stats.get("users_last_seen", {}) or {}
    c = 0
    for _uid, ts in last_seen.items():
        try:
            if now - int(ts) <= seconds:
                c += 1
        except Exception:
            pass
    return c


def _top_items(d: Dict[str, Any], n: int = 5) -> list[tuple[str, int]]:
    items = []
    for k, v in (d or {}).items():
        try:
            items.append((str(k), int(v)))
        except Exception:
            pass
    items.sort(key=lambda x: x[1], reverse=True)
    return items[:n]


def format_admin_stats() -> str:
    users = get_all_users()
    stats = _load_stats()

    active_24h = _count_active(stats, 24 * 3600)
    active_7d = _count_active(stats, 7 * 24 * 3600)
    active_30d = _count_active(stats, 30 * 24 * 3600)

    top_auth = _top_items(stats.get("authors_selected", {}), 6)
    top_cmds = _top_items(stats.get("commands", {}), 6)
    top_users = _top_items(stats.get("messages_by_user", {}), 5)

    lines = []
    lines.append("📊 <b>Статистика бота</b>\n")
    lines.append(f"👥 Пользователей всего: <b>{len(users)}</b>")
    lines.append(f"🟢 Активные за 24ч: <b>{active_24h}</b>")
    lines.append(f"🟡 Активные за 7д: <b>{active_7d}</b>")
    lines.append(f"🔵 Активные за 30д: <b>{active_30d}</b>")
    lines.append(f"💬 Сообщений всего: <b>{int(stats.get('messages_total', 0))}</b>")

    usernames = stats.get("usernames", {}) or {}

    if top_users:
        lines.append("\n🔥 <b>Самые активные пользователи</b>")
        for uid, cnt in top_users:
            uname = usernames.get(uid)
            if uname:
                title = f"@{uname} (<code>{uid}</code>)"
            else:
                title = f"Без ника (<code>{uid}</code>)"
            lines.append(f"• {title} — <b>{cnt}</b> сообщений")

    if top_auth:
        lines.append("\n🏆 <b>Топ авторов (выбор)</b>")
        for k, cnt in top_auth:
            name = (get_author(k) or {}).get("name", k)
            lines.append(f"• {name}: <b>{cnt}</b>")

    if top_cmds:
        lines.append("\n⌨️ <b>Топ команд</b>")
        for k, cnt in top_cmds:
            lines.append(f"• <code>{k}</code>: <b>{cnt}</b>")

    return "\n".join(lines)


def get_admin_keyboard():
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="📣 Рассылка", callback_data="admin_broadcast_help"),
    )
    kb.row(InlineKeyboardButton(text="🆔 Мой ID", callback_data="admin_whoami"))
    return kb.as_markup()


# =========================
# ✅ Админ callback-кнопки
# =========================
@router.callback_query(F.data == "admin_whoami")
async def cb_admin_whoami(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_user(user_id)
    mark_seen(user_id, callback.from_user.username)
    await callback.answer()
    await callback.message.answer(f"🆔 Ваш ID: <code>{user_id}</code>", parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_user(user_id)
    mark_seen(user_id, callback.from_user.username)

    if not is_admin(user_id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(format_admin_stats(), parse_mode=ParseMode.HTML)


@router.callback_query(F.data == "admin_broadcast_help")
async def cb_admin_broadcast_help(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_user(user_id)
    mark_seen(user_id, callback.from_user.username)

    if not is_admin(user_id):
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return

    await callback.answer()
    await callback.message.answer(
        "📣 <b>Рассылка</b>\n\n"
        "Команда:\n"
        "<code>/broadcast ТЕКСТ</code>\n\n"
        "Пример:\n"
        "<code>/broadcast Всем привет! Завтра обновление бота.</code>",
        parse_mode=ParseMode.HTML,
    )


# =========================
# Админ-команды (без ban/unban)
# =========================
@router.message(Command("whoami"))
async def cmd_whoami(message: Message):
    user_id = message.from_user.id
    track_user(user_id)
    mark_seen(user_id, message.from_user.username)
    inc_command("/whoami")
    await message.answer(f"🆔 Ваш ID: <code>{user_id}</code>", parse_mode=ParseMode.HTML)


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    user_id = message.from_user.id
    track_user(user_id)
    mark_seen(user_id, message.from_user.username)
    inc_command("/admin")

    if not is_admin(user_id):
        await message.answer("⛔ У вас нет доступа к админ-командам.")
        return

    await message.answer(
        "🛠 <b>Админ-панель</b>\n\n"
        "• <code>/stats</code> — статистика\n"
        "• <code>/broadcast ТЕКСТ</code> — рассылка\n"
        "• <code>/whoami</code> — ваш ID\n",
        parse_mode=ParseMode.HTML,
        reply_markup=get_admin_keyboard(),
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    user_id = message.from_user.id
    track_user(user_id)
    mark_seen(user_id, message.from_user.username)
    inc_command("/stats")

    if not is_admin(user_id):
        await message.answer("⛔ Нет доступа.")
        return

    await message.answer(format_admin_stats(), parse_mode=ParseMode.HTML)


@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    user_id = message.from_user.id
    track_user(user_id)
    mark_seen(user_id, message.from_user.username)
    inc_command("/broadcast")

    if not is_admin(user_id):
        await message.answer("⛔ Нет доступа.")
        return

    payload = (message.text or "").replace("/broadcast", "", 1).strip()
    if not payload:
        await message.answer("Использование: <code>/broadcast ТЕКСТ</code>", parse_mode=ParseMode.HTML)
        return

    users = get_all_users()
    ok = 0
    fail = 0

    await message.answer(
        f"📣 Начинаю рассылку… Пользователей: <b>{len(users)}</b>",
        parse_mode=ParseMode.HTML,
    )

    for uid in users:
        try:
            await message.bot.send_message(
                uid,
                f"📣 <b>Сообщение от администратора</b>\n\n{payload}",
                parse_mode=ParseMode.HTML,
            )
            ok += 1
            await asyncio.sleep(0.05)
        except Exception:
            fail += 1

    await message.answer(
        "✅ <b>Рассылка завершена</b>\n\n"
        f"Отправлено: <b>{ok}</b>\n"
        f"Не доставлено: <b>{fail}</b>",
        parse_mode=ParseMode.HTML,
    )


# =========================
# 🌐 Мини-сервер для Render/Railway
# =========================
async def start_web_server() -> None:
    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    logger.info("🌐 Web server started on 0.0.0.0:%s", port)


# =========================
# 🤖 Основные команды/кнопки
# =========================
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    track_user(user_id)
    mark_seen(user_id, message.from_user.username)
    inc_command("/start")

    db.reset_compare(user_id)
    db.set_mode(user_id, None)

    user_name = message.from_user.first_name if message.from_user else "Друг"
    text = (
        f"✨ <b>ЛИТЕРАТУРНЫЙ ДИАЛОГ</b> ✨\n\n"
        f"👋 <b>Привет, {user_name}!</b>\n\n"
        "📚 Сначала выбери <b>эпоху</b>, затем автора.\n"
        "🎭 Пиши вопросы — отвечу в стиле писателя.\n"
        "✍️ Можно писать произведение вместе.\n\n"
        "👇 <b>Выберите эпоху:</b>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML, reply_markup=get_groups_keyboard())

    if is_admin(user_id):
        await message.answer(
            "🛠 <b>Админ-панель</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_admin_keyboard(),
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    user_id = message.from_user.id
    track_user(user_id)
    mark_seen(user_id, message.from_user.username)
    inc_command("/help")

    await message.answer(
        "❓ <b>Помощь</b>\n\n"
        "1) Выбери эпоху\n"
        "2) Выбери автора\n"
        "3) Пиши вопрос\n\n"
        "Команда: /start — начать заново.",
        parse_mode=ParseMode.HTML,
    )


@router.callback_query(F.data == "groups_menu")
async def cb_groups_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_user(user_id)
    mark_seen(user_id, callback.from_user.username)

    db.reset_compare(user_id)
    db.set_mode(user_id, None)

    await callback.message.edit_text(
        "👇 <b>Выберите эпоху:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_groups_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("group_"))
async def cb_group_selected(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_user(user_id)
    mark_seen(user_id, callback.from_user.username)

    group_key = callback.data.split("_", 1)[1]
    await callback.message.edit_text(
        "👥 <b>Выберите автора:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard(group_key),
    )
    await callback.answer()


@router.callback_query(F.data == "change_author")
async def cb_change_author(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_user(user_id)
    mark_seen(user_id, callback.from_user.username)

    db.reset_compare(user_id)
    db.set_mode(user_id, None)

    await callback.message.edit_text(
        "👇 <b>Выберите эпоху:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_groups_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "reset_chat")
async def cb_reset_chat(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_user(user_id)
    mark_seen(user_id, callback.from_user.username)

    db.reset_dialog(user_id, keep_author=True)
    db.set_mode(user_id, None)

    await callback.message.edit_text(
        "🔄 <b>Диалог очищен.</b>\n\nМожешь продолжать общение.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard(),
    )
    await callback.answer("Готово")


@router.callback_query(F.data == "clear_all")
async def cb_clear_all(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_user(user_id)
    mark_seen(user_id, callback.from_user.username)

    db.clear_all(user_id)

    await callback.message.edit_text(
        "🧹 <b>Чат полностью очищен.</b>\n\n"
        "Чтобы начать заново, нажмите:\n\n"
        "<code>/start</code>",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Очищено")


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_user(user_id)
    mark_seen(user_id, callback.from_user.username)

    await cmd_start(callback.message)
    await callback.answer()


@router.callback_query(F.data == "cowrite")
async def cb_cowrite_start(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_user(user_id)
    mark_seen(user_id, callback.from_user.username)

    user_data = db.get_user_data(user_id)

    if not user_data.get("selected_author"):
        await callback.message.edit_text(
            "❌ Сначала выбери автора.\n\n👇 Выберите эпоху:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard(),
        )
        await callback.answer()
        return

    db.reset_compare(user_id)

    await callback.message.edit_text(
        "✍️ <b>СОАВТОРСТВО</b>\n\n"
        "Что будем писать вместе?",
        parse_mode=ParseMode.HTML,
        reply_markup=get_cowrite_mode_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.in_({"cowrite_prose", "cowrite_poem"}))
async def cb_cowrite_mode_selected(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_user(user_id)
    mark_seen(user_id, callback.from_user.username)

    mode = callback.data
    db.set_mode(user_id, mode)

    genre = "рассказ" if mode == "cowrite_prose" else "стихотворение"
    await callback.message.edit_text(
        "✍️ <b>Начинаем!</b>\n\n"
        f"Жанр: <b>{genre}</b>\n\n"
        "Напиши <b>первый фрагмент</b> — я продолжу.\n"
        "<i>Подсказка: 2–6 строк достаточно.</i>",
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("Режим включён")


@router.callback_query(F.data == "compare_authors")
async def cb_compare_authors(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_user(user_id)
    mark_seen(user_id, callback.from_user.username)

    user_data = db.get_user_data(user_id)

    if not user_data.get("selected_author"):
        await callback.message.edit_text(
            "❌ Сначала выбери автора для диалога.\n\n👇 Выберите эпоху:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard(),
        )
        await callback.answer()
        return

    db.set_mode(user_id, "compare_first")
    db.set_compare_first_author(user_id, None)

    await callback.message.edit_text(
        "🆚 <b>СРАВНЕНИЕ АВТОРОВ</b>\n\nВыберите эпоху первого автора:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_groups_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("author_"))
async def cb_author_selected(callback: CallbackQuery):
    user_id = callback.from_user.id
    track_user(user_id)
    mark_seen(user_id, callback.from_user.username)

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
            "🆚 <b>СРАВНЕНИЕ АВТОРОВ</b>\n\n"
            f"Первый выбран: <b>{get_author(author_key).get('name', author_key)}</b>\n\n"
            "Теперь выберите эпоху второго автора:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard(),
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
                reply_markup=get_groups_keyboard(),
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
                a2=second,
            )
        except Exception as e:
            logger.exception("Ошибка сравнения: %s", e)
            compare_text = "⚠️ Не получилось сравнить авторов. Попробуйте ещё раз."

        await callback.message.edit_text(
            compare_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard(),
        )
        await callback.answer("Готово")
        return

    # обычный выбор автора
    user_data["selected_author"] = author_key
    db.save_user_data(user_id, user_data)
    db.set_mode(user_id, None)
    db.reset_compare(user_id)

    inc_author_selected(author_key)

    author = get_author(author_key)
    await callback.message.edit_text(
        f"{author.get('name', author_key)}\n\n"
        f"💬 {author.get('greeting', 'Здравствуйте!')}\n\n"
        "<i>Задавайте вопросы — отвечу в своём стиле!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard(),
    )
    await callback.answer("Выбран")


@router.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    track_user(user_id)
    mark_seen(user_id, message.from_user.username)
    inc_message(user_id)

    user_text = (message.text or "").strip()
    if not user_text:
        return

    user_data = db.get_user_data(user_id)
    mode = user_data.get("mode")

    if mode in ("compare_first", "compare_second"):
        await message.answer(
            "🆚 Вы в режиме сравнения. Выбирайте авторов кнопками 👇",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard(),
        )
        return

    author_key = user_data.get("selected_author")
    if not author_key:
        await message.answer(
            "❌ <b>Сначала выберите автора!</b>\n\n👇 Выберите эпоху:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard(),
        )
        return

    author = get_author(author_key)

    # Соавторство
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
            parse_mode=ParseMode.HTML,
        )

        try:
            response = await gigachat_client.generate_response(
                author_key=author_key,
                user_message=prompt,
                conversation_history=[],
            )
            try:
                await thinking.delete()
            except Exception:
                pass

            await message.answer(
                f"{author.get('name', author_key)}:\n\n{response}\n\n"
                "<i>Твоя очередь — допиши следующий фрагмент ✍️</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=get_chat_keyboard(),
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
                reply_markup=get_chat_keyboard(),
            )
            return

    # Обычный чат
    thinking = await message.answer(
        f"<i>✨ {author.get('name', author_key)} обдумывает ответ...</i>",
        parse_mode=ParseMode.HTML,
    )

    try:
        response = await gigachat_client.generate_response(
            author_key=author_key,
            user_message=user_text,
            conversation_history=user_data.get("conversation_history", []),
        )
        try:
            await thinking.delete()
        except Exception:
            pass

        await message.answer(
            f"{author.get('name', author_key)}\n\n{response}",
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard(),
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
            parse_mode=ParseMode.HTML,
        )


# =========================
# 🌐 Мини-сервер для Render/Railway
# =========================
async def start_web_server() -> None:
    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()

    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    logger.info("🌐 Web server started on 0.0.0.0:%s", port)


# =========================
# 🚀 Запуск
# =========================
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN пуст. Добавь BOT_TOKEN в переменные окружения / .env")

    lock_fd = None
    try:
        lock_fd = acquire_single_instance_lock()
    except Exception as e:
        logger.error(str(e))
        return

    def _cleanup(*_args):
        if lock_fd is not None:
            release_single_instance_lock(lock_fd)

    atexit.register(_cleanup)
    for _sig in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
        if _sig is not None:
            try:
                signal.signal(_sig, lambda *_: (_cleanup(), os._exit(0)))
            except Exception:
                pass

    await start_web_server()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    limiter = InMemoryRateLimiter(RateLimitConfig())
    dp.message.middleware(AntiFloodMiddleware(limiter))

    dp.include_router(router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception:
        pass

    logger.info("🤖 Start polling...")
    try:
        await dp.start_polling(bot)
    finally:
        _cleanup()


if __name__ == "__main__":
    asyncio.run(main())
