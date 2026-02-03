# admin_tools.py
import os
import json
import time
import asyncio
from typing import Set

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

ADMIN_ROUTER = Router()
START_TS = time.time()


# =========================
# ВСПОМОГАТЕЛЬНОЕ
# =========================
def _data_dir():
    path = os.path.join(os.getcwd(), "data")
    os.makedirs(path, exist_ok=True)
    return path


def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _admins() -> Set[int]:
    raw = os.getenv("ADMIN_IDS", "")
    return {int(x) for x in raw.split(",") if x.strip().isdigit()}


def is_admin(user_id: int) -> bool:
    return user_id in _admins()


# =========================
# ПОЛЬЗОВАТЕЛИ / БАН
# =========================
def users_path():
    return os.path.join(_data_dir(), "users.json")


def banned_path():
    return os.path.join(_data_dir(), "banned.json")


def track_user(user_id: int):
    data = _load(users_path(), {"users": []})
    if user_id not in data["users"]:
        data["users"].append(user_id)
        _save(users_path(), data)


def all_users():
    return _load(users_path(), {"users": []})["users"]


def banned_users():
    return set(_load(banned_path(), {"banned": []})["banned"])


def ban_user(uid: int):
    data = _load(banned_path(), {"banned": []})
    if uid not in data["banned"]:
        data["banned"].append(uid)
        _save(banned_path(), data)


def unban_user(uid: int):
    data = _load(banned_path(), {"banned": []})
    if uid in data["banned"]:
        data["banned"].remove(uid)
        _save(banned_path(), data)


def is_banned(uid: int) -> bool:
    return uid in banned_users()


# =========================
# АДМИН-КОМАНДЫ
# =========================
@ADMIN_ROUTER.message(Command("whoami"))
async def whoami(message: Message):
    track_user(message.from_user.id)
    await message.answer(
        f"🆔 Ваш ID: <code>{message.from_user.id}</code>",
        parse_mode=ParseMode.HTML
    )


@ADMIN_ROUTER.message(Command("admin"))
async def admin_panel(message: Message):
    track_user(message.from_user.id)
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return

    await message.answer(
        "🛠 <b>АДМИН-ПАНЕЛЬ</b>\n\n"
        "Команды:\n"
        "/stats — статистика\n"
        "/broadcast ТЕКСТ — рассылка\n"
        "/ban USER_ID — бан\n"
        "/unban USER_ID — разбан\n"
        "/whoami — узнать ID",
        parse_mode=ParseMode.HTML
    )


@ADMIN_ROUTER.message(Command("stats"))
async def stats(message: Message):
    track_user(message.from_user.id)
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return

    uptime = int(time.time() - START_TS)
    await message.answer(
        "📊 <b>СТАТИСТИКА</b>\n\n"
        f"👥 Пользователей: <b>{len(all_users())}</b>\n"
        f"🚫 В бане: <b>{len(banned_users())}</b>\n"
        f"⏱ Аптайм: <b>{uptime // 3600}ч {(uptime % 3600) // 60}м</b>",
        parse_mode=ParseMode.HTML
    )


@ADMIN_ROUTER.message(Command("ban"))
async def ban(message: Message):
    track_user(message.from_user.id)
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /ban USER_ID")
        return

    ban_user(int(parts[1]))
    await message.answer("🚫 Пользователь заблокирован")


@ADMIN_ROUTER.message(Command("unban"))
async def unban(message: Message):
    track_user(message.from_user.id)
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return

    parts = message.text.split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /unban USER_ID")
        return

    unban_user(int(parts[1]))
    await message.answer("✅ Пользователь разблокирован")


@ADMIN_ROUTER.message(Command("broadcast"))
async def broadcast(message: Message):
    track_user(message.from_user.id)
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Нет доступа")
        return

    text = message.text.replace("/broadcast", "", 1).strip()
    if not text:
        await message.answer("Использование: /broadcast ТЕКСТ")
        return

    ok, fail = 0, 0
    for uid in all_users():
        if is_banned(uid):
            continue
        try:
            await message.bot.send_message(
                uid,
                f"📣 <b>Сообщение от администратора</b>\n\n{text}",
                parse_mode=ParseMode.HTML
            )
            ok += 1
            await asyncio.sleep(0.05)
        except (TelegramForbiddenError, TelegramBadRequest):
            fail += 1

    await message.answer(
        f"✅ Рассылка завершена\n\n"
        f"Отправлено: {ok}\n"
        f"Ошибок: {fail}"
    )
