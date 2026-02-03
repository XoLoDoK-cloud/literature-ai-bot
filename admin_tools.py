# admin_tools.py
import os
import json
import time
import asyncio
from typing import Set, List, Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

ADMIN_ROUTER = Router()

_START_TS = time.time()


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _data_dir() -> str:
    # Сохраняем рядом с проектом в папку data
    base = os.path.join(os.getcwd(), "data")
    _ensure_dir(base)
    return base


def _load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, obj) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _admins_from_env() -> Set[int]:
    """
    ADMIN_IDS пример: "123,456,789"
    """
    raw = os.getenv("ADMIN_IDS", "").strip()
    if not raw:
        return set()
    out = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


def is_admin(user_id: int) -> bool:
    return user_id in _admins_from_env()


def _users_path() -> str:
    return os.path.join(_data_dir(), "admin_users.json")


def _banned_path() -> str:
    return os.path.join(_data_dir(), "admin_banned.json")


def get_all_users() -> List[int]:
    data = _load_json(_users_path(), {"users": []})
    users = data.get("users", [])
    # фильтр на int
    res = []
    for u in users:
        try:
            res.append(int(u))
        except Exception:
            pass
    # уникальные
    return sorted(list(set(res)))


def track_user(user_id: int) -> None:
    """
    Вызывай при любом действии пользователя (/start, сообщения, нажатия кнопок).
    Тогда база для рассылки будет полной.
    """
    users = set(get_all_users())
    if user_id not in users:
        users.add(user_id)
        _save_json(_users_path(), {"users": sorted(list(users))})


def get_banned() -> Set[int]:
    data = _load_json(_banned_path(), {"banned": []})
    res = set()
    for u in data.get("banned", []):
        try:
            res.add(int(u))
        except Exception:
            pass
    return res


def ban_user(user_id: int) -> None:
    banned = get_banned()
    banned.add(int(user_id))
    _save_json(_banned_path(), {"banned": sorted(list(banned))})


def unban_user(user_id: int) -> None:
    banned = get_banned()
    banned.discard(int(user_id))
    _save_json(_banned_path(), {"banned": sorted(list(banned))})


def is_banned(user_id: int) -> bool:
    return int(user_id) in get_banned()


def admin_keyboard():
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats"),
        InlineKeyboardButton(text="📣 Рассылка", callback_data="adm_broadcast_help"),
    )
    kb.row(
        InlineKeyboardButton(text="🚫 Бан", callback_data="adm_ban_help"),
        InlineKeyboardButton(text="✅ Разбан", callback_data="adm_unban_help"),
    )
    kb.row(InlineKeyboardButton(text="🆔 Кто я", callback_data="adm_whoami"))
    return kb.as_markup()


def _uptime_text() -> str:
    sec = int(time.time() - _START_TS)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


async def _send_safe(bot, chat_id: int, text: str):
    try:
        await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
        return True
    except (TelegramForbiddenError, TelegramBadRequest):
        return False
    except Exception:
        return False


# ----------------------------
# Команды
# ----------------------------
@ADMIN_ROUTER.message(Command("whoami"))
async def cmd_whoami(message: Message):
    track_user(message.from_user.id)
    await message.answer(f"🆔 Ваш ID: <code>{message.from_user.id}</code>", parse_mode=ParseMode.HTML)


@ADMIN_ROUTER.message(Command("admin"))
async def cmd_admin(message: Message):
    track_user(message.from_user.id)
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет доступа к админ-командам.")
        return

    await message.answer(
        "🛠 <b>Админ-панель</b>\n"
        "Команды:\n"
        "• /stats\n"
        "• /broadcast ТЕКСТ\n"
        "• /ban USER_ID\n"
        "• /unban USER_ID\n"
        "• /whoami\n",
        parse_mode=ParseMode.HTML,
        reply_markup=admin_keyboard()
    )


@ADMIN_ROUTER.message(Command("stats"))
async def cmd_stats(message: Message):
    track_user(message.from_user.id)
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа.")
        return

    users = get_all_users()
    banned = get_banned()

    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей (замечено ботом): <b>{len(users)}</b>\n"
        f"🚫 В бане: <b>{len(banned)}</b>\n"
        f"⏱ Аптайм: <b>{_uptime_text()}</b>\n\n"
        "<i>Важно:</i> база рассылки пополняется, когда пользователь хоть раз нажал /start, написал сообщение или нажал кнопку.",
        parse_mode=ParseMode.HTML
    )


@ADMIN_ROUTER.message(Command("ban"))
async def cmd_ban(message: Message):
    track_user(message.from_user.id)
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа.")
        return

    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: <code>/ban USER_ID</code>", parse_mode=ParseMode.HTML)
        return

    uid = int(parts[1])
    ban_user(uid)
    await message.answer(f"🚫 Пользователь <code>{uid}</code> забанен.", parse_mode=ParseMode.HTML)


@ADMIN_ROUTER.message(Command("unban"))
async def cmd_unban(message: Message):
    track_user(message.from_user.id)
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа.")
        return

    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: <code>/unban USER_ID</code>", parse_mode=ParseMode.HTML)
        return

    uid = int(parts[1])
    unban_user(uid)
    await message.answer(f"✅ Пользователь <code>{uid}</code> разбанен.", parse_mode=ParseMode.HTML)


@ADMIN_ROUTER.message(Command("broadcast"))
async def cmd_broadcast(message: Message):
    track_user(message.from_user.id)
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа.")
        return

    text = (message.text or "")
    payload = text.replace("/broadcast", "", 1).strip()
    if not payload:
        await message.answer("Использование: <code>/broadcast ТЕКСТ</code>", parse_mode=ParseMode.HTML)
        return

    users = get_all_users()
    banned = get_banned()

    # Рассылка с небольшой паузой, чтобы не словить лимиты
    ok = 0
    fail = 0

    await message.answer(f"📣 Начинаю рассылку… Пользователей: {len(users)}", parse_mode=ParseMode.HTML)

    for uid in users:
        if uid in banned:
            continue
        sent = await _send_safe(message.bot, uid, f"📣 <b>Сообщение от администратора</b>\n\n{payload}")
        if sent:
            ok += 1
        else:
            fail += 1
        await asyncio.sleep(0.05)  # 50мс

    await message.answer(
        "✅ <b>Рассылка завершена</b>\n\n"
        f"Отправлено: <b>{ok}</b>\n"
        f"Не доставлено: <b>{fail}</b>",
        parse_mode=ParseMode.HTML
    )


# ----------------------------
# Админ-кнопки (inline)
# ----------------------------
@ADMIN_ROUTER.callback_query(F.data == "adm_stats")
async def cb_adm_stats(callback: CallbackQuery):
    track_user(callback.from_user.id)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    users = get_all_users()
    banned = get_banned()
    await callback.message.answer(
        "📊 <b>Статистика</b>\n\n"
        f"👥 Пользователей: <b>{len(users)}</b>\n"
        f"🚫 В бане: <b>{len(banned)}</b>\n"
        f"⏱ Аптайм: <b>{_uptime_text()}</b>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@ADMIN_ROUTER.callback_query(F.data == "adm_broadcast_help")
async def cb_adm_broadcast_help(callback: CallbackQuery):
    track_user(callback.from_user.id)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer(
        "📣 <b>Рассылка</b>\n\n"
        "Команда:\n"
        "<code>/broadcast ТЕКСТ</code>\n\n"
        "Пример:\n"
        "<code>/broadcast Завтра добавлю новых авторов и режимы!</code>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@ADMIN_ROUTER.callback_query(F.data == "adm_ban_help")
async def cb_adm_ban_help(callback: CallbackQuery):
    track_user(callback.from_user.id)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer(
        "🚫 <b>Бан</b>\n\n"
        "Команда:\n"
        "<code>/ban USER_ID</code>\n\n"
        "Чтобы узнать USER_ID, пользователь может написать:\n"
        "<code>/whoami</code>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@ADMIN_ROUTER.callback_query(F.data == "adm_unban_help")
async def cb_adm_unban_help(callback: CallbackQuery):
    track_user(callback.from_user.id)
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.answer(
        "✅ <b>Разбан</b>\n\n"
        "Команда:\n"
        "<code>/unban USER_ID</code>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@ADMIN_ROUTER.callback_query(F.data == "adm_whoami")
async def cb_adm_whoami(callback: CallbackQuery):
    track_user(callback.from_user.id)
    await callback.message.answer(f"🆔 Ваш ID: <code>{callback.from_user.id}</code>", parse_mode=ParseMode.HTML)
    await callback.answer()
