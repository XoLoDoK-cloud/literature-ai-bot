# admin_tools.py
import os
import json
import time
import asyncio
from typing import Set, List

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

ADMIN_ROUTER = Router()
_START_TS = time.time()


def _data_dir() -> str:
    path = os.path.join(os.getcwd(), "data")
    os.makedirs(path, exist_ok=True)
    return path


def _load(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path: str, obj) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _admins_from_env() -> Set[int]:
    raw = os.getenv("ADMIN_IDS", "").strip()
    if not raw:
        return set()
    out = set()
    for p in raw.split(","):
        p = p.strip()
        if p.isdigit():
            out.add(int(p))
    return out


def is_admin(user_id: int) -> bool:
    return int(user_id) in _admins_from_env()


def _users_path() -> str:
    return os.path.join(_data_dir(), "users.json")


def _banned_path() -> str:
    return os.path.join(_data_dir(), "banned.json")


def track_user(user_id: int) -> None:
    data = _load(_users_path(), {"users": []})
    users = set(int(x) for x in data.get("users", []) if str(x).isdigit())
    if int(user_id) not in users:
        users.add(int(user_id))
        _save(_users_path(), {"users": sorted(list(users))})


def get_all_users() -> List[int]:
    data = _load(_users_path(), {"users": []})
    res = []
    for x in data.get("users", []):
        try:
            res.append(int(x))
        except Exception:
            pass
    return sorted(list(set(res)))


def get_banned() -> Set[int]:
    data = _load(_banned_path(), {"banned": []})
    res = set()
    for x in data.get("banned", []):
        try:
            res.add(int(x))
        except Exception:
            pass
    return res


def is_banned(user_id: int) -> bool:
    return int(user_id) in get_banned()


def ban_user(user_id: int) -> None:
    banned = get_banned()
    banned.add(int(user_id))
    _save(_banned_path(), {"banned": sorted(list(banned))})


def unban_user(user_id: int) -> None:
    banned = get_banned()
    banned.discard(int(user_id))
    _save(_banned_path(), {"banned": sorted(list(banned))})


def _uptime() -> str:
    sec = int(time.time() - _START_TS)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


async def _send_safe(bot, chat_id: int, text: str) -> bool:
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
        "🛠 <b>Админ-команды</b>\n\n"
        "• <code>/stats</code> — статистика\n"
        "• <code>/broadcast ТЕКСТ</code> — рассылка\n"
        "• <code>/ban USER_ID</code> — бан\n"
        "• <code>/unban USER_ID</code> — разбан\n"
        "• <code>/whoami</code> — узнать свой ID\n",
        parse_mode=ParseMode.HTML
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
        f"👥 Пользователей: <b>{len(users)}</b>\n"
        f"🚫 В бане: <b>{len(banned)}</b>\n"
        f"⏱ Аптайм: <b>{_uptime()}</b>",
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
        sent = await _send_safe(message.bot, uid, f"📣 <b>Сообщение от администратора</b>\n\n{payload}")
        if sent:
            ok += 1
        else:
            fail += 1
        await asyncio.sleep(0.05)

    await message.answer(
        "✅ <b>Рассылка завершена</b>\n\n"
        f"Отправлено: <b>{ok}</b>\n"
        f"Не доставлено: <b>{fail}</b>",
        parse_mode=ParseMode.HTML
    )
