import os
import re
import asyncio
import logging

from aiohttp import web

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
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
    get_back_to_chat_keyboard,
)
from gigachat_client import gigachat_client
from rate_limit import RateLimitConfig, InMemoryRateLimiter, AntiFloodMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


# =========================
# 🌐 Мини-сервер, чтобы хостинг видел открытый порт
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
# 🔎 Нормализация текста для поиска совпадений
# =========================
def _norm(s: str) -> str:
    s = (s or "").lower().replace("ё", "е")
    s = re.sub(r"[«»\"'`]", " ", s)
    s = re.sub(r"[^a-zа-я0-9\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _contains_phrase(text_norm: str, phrase_norm: str) -> bool:
    # безопасная проверка "как фраза" (границы слов)
    # работает даже если в названии есть тире
    pattern = r"(?:^|\s)" + re.escape(phrase_norm) + r"(?:$|\s)"
    return re.search(pattern, text_norm) is not None or phrase_norm in text_norm


# =========================
# 🧠 Широкое распознавание автора по произведению/автору
# Максимально широко, но "без рисков":
# - НЕ выбираем автора автоматически
# - только предлагаем 1–3 кандидата кнопками
# =========================
AUTHOR_NAME_HINTS = {
    # фамилии/имена -> ключ автора
    "пушкин": "pushkin",
    "александр пушкин": "pushkin",
    "лермонтов": "lermontov",
    "гоголь": "gogol",
    "достоевск": "dostoevsky",
    "толстой": "tolstoy",
    "лев толстой": "tolstoy",
    "чехов": "chekhov",
    "тургенев": "turgenev",
    "ахматов": "akhmatova",
    "блок": "blok",
    "есенин": "yesenin",
    "маяковск": "mayakovsky",
    "цветаев": "tsvetaeva",
    "мандельштам": "mandelshtam",
    "пастернак": "pasternak",
    "булгаков": "bulgakov",
    "шолохов": "sholokhov",
    "солженицын": "solzhenitsyn",
    "бродск": "brodsky",
    "высоцк": "vysotsky",
    "филатов": "filatov",
    "пелевин": "pelevin",
    "улицкая": "ulitskaya",
}

# Название произведения -> автор
# Добавил много школьной программы + популярные варианты написания.
WORK_TO_AUTHOR = {
    # Пушкин
    "капитанская дочка": "pushkin",
    "евгений онегин": "pushkin",
    "пиковая дама": "pushkin",
    "борис годунов": "pushkin",
    "дубровский": "pushkin",
    "повести белкина": "pushkin",
    "сказка о рыбаке и рыбке": "pushkin",
    "сказка о царе салтане": "pushkin",
    "сказка о мертвой царевне и семи богатырях": "pushkin",
    "медный всадник": "pushkin",

    # Лермонтов
    "герой нашего времени": "lermontov",
    "мцыри": "lermontov",
    "демон": "lermontov",
    "парус": "lermontov",
    "бородино": "lermontov",

    # Гоголь
    "шинель": "gogol",
    "ревизор": "gogol",
    "мертвые души": "gogol",
    "повесть о том как поссорился иван иванович с иваном никифоровичем": "gogol",
    "нос": "gogol",
    "тартюф": "gogol",  # (на всякий) но это Мольер — чтобы не рисковать, ниже мы фильтруем сомнительные совпадения
    "вий": "gogol",
    "вечера на хуторе близ диканьки": "gogol",
    "тарас бульба": "gogol",

    # Достоевский
    "преступление и наказание": "dostoevsky",
    "братья карамазовы": "dostoevsky",
    "идиот": "dostoevsky",
    "бесы": "dostoevsky",
    "униженные и оскорбленные": "dostoevsky",
    "записки из подполья": "dostoevsky",

    # Толстой
    "война и мир": "tolstoy",
    "анна каренина": "tolstoy",
    "воскресение": "tolstoy",
    "детство": "tolstoy",
    "отрочество": "tolstoy",
    "юность": "tolstoy",
    "после бала": "tolstoy",
    "холстомер": "tolstoy",
    "кавказский пленник": "tolstoy",

    # Чехов
    "вишневый сад": "chekhov",
    "вишнёвый сад": "chekhov",
    "три сестры": "chekhov",
    "палата 6": "chekhov",
    "палата №6": "chekhov",
    "человек в футляре": "chekhov",
    "хамелеон": "chekhov",
    "толстый и тонкий": "chekhov",
    "дама с собачкой": "chekhov",

    # Тургенев
    "отцы и дети": "turgenev",
    "записки охотника": "turgenev",
    "дворянское гнездо": "turgenev",
    "ася": "turgenev",
    "му-му": "turgenev",

    # Ахматова
    "реквием": "akhmatova",
    "поэма без героя": "akhmatova",

    # Блок
    "двенадцать": "blok",
    "незнакомка": "blok",

    # Есенин
    "исповедь хулигана": "yesenin",
    "персидские мотивы": "yesenin",

    # Маяковский
    "облако в штанах": "mayakovsky",
    "флейта позвоночник": "mayakovsky",
    "флейта-позвоночник": "mayakovsky",

    # Цветаева
    "мне нравится что вы больны не мной": "tsvetaeva",  # часто ищут строкой
    "кто создан из камня кто создан из глины": "tsvetaeva",

    # Пастернак
    "доктор живаго": "pasternak",

    # Булгаков
    "мастер и маргарита": "bulgakov",
    "собачье сердце": "bulgakov",
    "белая гвардия": "bulgakov",

    # Шолохов
    "тихий дон": "sholokhov",
    "судьба человека": "sholokhov",

    # Солженицын
    "один день ивана денисовича": "solzhenitsyn",
    "архипелаг гулаг": "solzhenitsyn",

    # Филатов
    "про федота стрельца удалого молодца": "filatov",
    "про федота стрельца": "filatov",
}

# Сомнительные / пересекающиеся слова, чтобы не ловить "ложные" совпадения
# (например, очень короткие заголовки типа "Ася" могут совпадать случайно)
SHORT_TITLES_RISK = {"ася", "нос", "вий", "парус", "бородино"}


def guess_authors_from_text(user_text: str):
    """
    Возвращает список кандидатов:
    [{"author_key": "...", "reason": "...", "score": int}]
    """
    text_norm = _norm(user_text)
    candidates = {}

    # 1) По автору (фамилия в тексте) — самый надёжный сигнал
    for hint, akey in AUTHOR_NAME_HINTS.items():
        hint_norm = _norm(hint)
        if hint_norm and _contains_phrase(text_norm, hint_norm):
            candidates[akey] = max(candidates.get(akey, 0), 100)

    # 2) По произведению — широко, но аккуратно
    for title, akey in WORK_TO_AUTHOR.items():
        tnorm = _norm(title)
        if not tnorm:
            continue

        # если заголовок "опасно короткий" — требуем точное совпадение фразой
        if tnorm in SHORT_TITLES_RISK:
            if _contains_phrase(text_norm, tnorm):
                candidates[akey] = max(candidates.get(akey, 0), 80)
            continue

        # обычный случай: подстрока + длина заголовка
        if tnorm in text_norm:
            # чем длиннее и точнее заголовок — тем выше балл
            score = 60 + min(len(tnorm), 40)
            candidates[akey] = max(candidates.get(akey, 0), score)

    # соберём и отсортируем
    res = []
    for akey, score in candidates.items():
        name = get_author(akey).get("name", akey)
        # причина:
        reason = "узнал автора по фамилии/упоминанию" if score >= 100 else "похоже по названию произведения"
        res.append({"author_key": akey, "author_name": name, "reason": reason, "score": score})

    res.sort(key=lambda x: x["score"], reverse=True)

    # ограничим 3 лучшими, чтобы не шуметь
    return res[:3]


def build_quick_author_keyboard(candidates):
    """
    Клавиатура:
    ✅ Ответить как <Автор1>
    ✅ Ответить как <Автор2> (если есть)
    ...
    🔁 Выбрать автора вручную
    """
    kb = InlineKeyboardBuilder()

    for c in candidates:
        kb.row(
            InlineKeyboardButton(
                text=f"✅ Ответить как {c['author_name']}",
                callback_data=f"quick_author_{c['author_key']}"
            )
        )

    kb.row(InlineKeyboardButton(text="🔁 Выбрать автора вручную", callback_data="groups_menu"))
    kb.row(InlineKeyboardButton(text="🏠 В главное меню", callback_data="main_menu"))
    return kb.as_markup()


# =========================
# 🤖 Команды / UI
# =========================
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    db.reset_compare(user_id)
    db.set_mode(user_id, None)

    user_data = db.get_user_data(user_id)
    user_data.pop("pending_question", None)
    user_data.pop("dialog_first_author", None)
    user_data.pop("dialog_second_author", None)
    db.save_user_data(user_id, user_data)

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


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "❓ <b>Помощь</b>\n\n"
        "1) Выбери эпоху\n"
        "2) Выбери автора\n"
        "3) Пиши вопрос\n\n"
        "Кнопки внизу открывают режимы:\n"
        "📝 Разбор текста / 🎓 ЕГЭ / 💬 Диалог авторов\n\n"
        "Команда: /start — начать заново.",
        parse_mode=ParseMode.HTML
    )


# =========================
# 🔘 Навигация по эпохам/авторам
# =========================
@router.callback_query(F.data == "groups_menu")
async def groups_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.reset_compare(user_id)
    db.set_mode(user_id, None)

    user_data = db.get_user_data(user_id)
    user_data.pop("pending_question", None)
    user_data.pop("dialog_first_author", None)
    user_data.pop("dialog_second_author", None)
    db.save_user_data(user_id, user_data)

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

    user_data = db.get_user_data(user_id)
    user_data.pop("pending_question", None)
    user_data.pop("dialog_first_author", None)
    user_data.pop("dialog_second_author", None)
    db.save_user_data(user_id, user_data)

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

    user_data = db.get_user_data(user_id)
    user_data.pop("pending_question", None)
    user_data.pop("dialog_first_author", None)
    user_data.pop("dialog_second_author", None)
    db.save_user_data(user_id, user_data)

    await cmd_start(callback.message)
    await callback.answer()


# =========================
# ✅ НОВОЕ: быстрый выбор автора по вопросу
# =========================
@router.callback_query(F.data.startswith("quick_author_"))
async def quick_author_selected(callback: CallbackQuery):
    user_id = callback.from_user.id
    author_key = callback.data.split("quick_author_", 1)[1]

    if author_key not in list_author_keys():
        await callback.answer("Автор не найден", show_alert=True)
        return

    user_data = db.get_user_data(user_id)
    user_data["selected_author"] = author_key
    pending = user_data.pop("pending_question", None)
    db.save_user_data(user_id, user_data)
    db.set_mode(user_id, None)

    author = get_author(author_key)

    # Если есть сохранённый вопрос — сразу отвечаем на него
    if pending:
        thinking = await callback.message.answer(
            f"<i>✨ {author.get('name', author_key)} отвечает на ваш вопрос…</i>",
            parse_mode=ParseMode.HTML
        )
        try:
            response = await gigachat_client.generate_response(
                author_key=author_key,
                user_message=pending,
                conversation_history=user_data.get("conversation_history", [])
            )
            try:
                await thinking.delete()
            except Exception:
                pass

            await callback.message.answer(
                f"{author.get('name', author_key)}\n\n{response}",
                parse_mode=ParseMode.HTML,
                reply_markup=get_chat_keyboard()
            )
            db.update_conversation(user_id, author_key, pending, response)
        except Exception as e:
            logger.exception("Ошибка quick-ответа: %s", e)
            try:
                await thinking.delete()
            except Exception:
                pass
            await callback.message.answer(
                "⚠️ Не получилось ответить. Попробуйте ещё раз.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_chat_keyboard()
            )

        await callback.answer("Готово")
        return

    # Иначе просто подтверждаем выбор
    await callback.message.answer(
        f"✅ Выбран автор: <b>{author.get('name', author_key)}</b>\n\n"
        "Теперь напиши вопрос — отвечу в его стиле.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard()
    )
    await callback.answer("Выбрано")


# =========================
# ✍️ Соавторство
# =========================
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


# =========================
# 🆚 Сравнение авторов (как было)
# =========================
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


# =========================
# ✅ НОВОЕ: Режимы 1/2/3
# =========================
@router.callback_query(F.data == "mode_analysis")
async def mode_analysis(callback: CallbackQuery):
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

    db.set_mode(user_id, "analysis_text")

    await callback.message.edit_text(
        "📝 <b>ЛИТЕРАТУРНЫЙ РАЗБОР</b>\n\n"
        "Пришли текст (стих/прозу/сочинение).\n"
        "Я сделаю разбор:\n"
        "• тема и идея\n"
        "• настроение\n"
        "• образы и средства\n"
        "• сильные места и что улучшить\n\n"
        "<i>Можно присылать хоть 3 строки, хоть большой отрывок.</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_to_chat_keyboard()
    )
    await callback.answer("Режим включён")


@router.callback_query(F.data == "mode_ege")
async def mode_ege(callback: CallbackQuery):
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

    db.set_mode(user_id, "ege_mode")

    await callback.message.edit_text(
        "🎓 <b>ЕГЭ-РЕЖИМ</b>\n\n"
        "Напиши, что нужно:\n"
        "• план сочинения\n"
        "• тезис + аргументы\n"
        "• подбор примеров\n"
        "• сравнение героев / тем\n\n"
        "⚠️ Я НЕ пишу полностью готовое сочинение за тебя.\n"
        "Я даю структуру и сильные формулировки.\n\n"
        "<i>Пример:</i>\n"
        "«Составь план и тезисы по теме: что такое честь в “Капитанской дочке”»",
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_to_chat_keyboard()
    )
    await callback.answer("Режим включён")


@router.callback_query(F.data == "mode_dialog")
async def mode_dialog(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)

    if not user_data.get("selected_author"):
        await callback.message.edit_text(
            "❌ Сначала выбери автора (он будет твоим “основным голосом”).\n\n👇 Выберите эпоху:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        await callback.answer()
        return

    user_data["dialog_first_author"] = None
    user_data["dialog_second_author"] = None
    db.save_user_data(user_id, user_data)

    db.set_mode(user_id, "dialog_first")

    await callback.message.edit_text(
        "💬 <b>ДИАЛОГ АВТОРОВ</b>\n\n"
        "Сначала выбери <b>первого автора</b>.\n"
        "👇 Выберите эпоху:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_groups_keyboard()
    )
    await callback.answer("Выбор автора")


@router.callback_query(F.data == "back_to_chat")
async def back_to_chat(callback: CallbackQuery):
    user_id = callback.from_user.id
    db.set_mode(user_id, None)

    await callback.message.edit_text(
        "✅ Вернулись в обычный диалог.\n\n"
        "Пиши вопрос — я отвечу в стиле выбранного автора.",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard()
    )
    await callback.answer("Ок")


# =========================
# 👤 Выбор автора + обработка спец-режимов выбора
# =========================
@router.callback_query(F.data.startswith("author_"))
async def author_selected(callback: CallbackQuery):
    user_id = callback.from_user.id
    author_key = callback.data.split("_", 1)[1]

    if author_key not in list_author_keys():
        await callback.answer("Автор не найден", show_alert=True)
        return

    user_data = db.get_user_data(user_id)
    mode = user_data.get("mode")

    # ---- сравнение авторов ----
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

    # ---- диалог авторов ----
    if mode == "dialog_first":
        user_data["dialog_first_author"] = author_key
        user_data["dialog_second_author"] = None
        db.save_user_data(user_id, user_data)

        db.set_mode(user_id, "dialog_second")
        await callback.message.edit_text(
            f"💬 <b>ДИАЛОГ АВТОРОВ</b>\n\n"
            f"Первый выбран: <b>{get_author(author_key).get('name', author_key)}</b>\n\n"
            f"Теперь выбери <b>второго автора</b>.\n"
            "👇 Выберите эпоху:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        await callback.answer("Первый выбран")
        return

    if mode == "dialog_second":
        first = user_data.get("dialog_first_author")
        second = author_key

        if not first:
            db.set_mode(user_id, "dialog_first")
            await callback.message.edit_text(
                "⚠️ Потерял выбор первого автора. Выберите его заново:\n👇 Выберите эпоху:",
                parse_mode=ParseMode.HTML,
                reply_markup=get_groups_keyboard()
            )
            await callback.answer()
            return

        if first == second:
            await callback.answer("Нужно выбрать двух разных авторов", show_alert=True)
            return

        user_data["dialog_second_author"] = second
        db.save_user_data(user_id, user_data)
        db.set_mode(user_id, "dialog_wait_topic")

        await callback.message.edit_text(
            "💬 <b>ДИАЛОГ АВТОРОВ</b>\n\n"
            f"Выбраны:\n"
            f"1) <b>{get_author(first).get('name', first)}</b>\n"
            f"2) <b>{get_author(second).get('name', second)}</b>\n\n"
            "Теперь напиши <b>тему / вопрос</b>, о чём они будут говорить.\n\n"
            "<i>Пример: «Что важнее: свобода или долг?»</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=get_back_to_chat_keyboard()
        )
        await callback.answer("Выбран второй")
        return

    # ---- обычный выбор автора ----
    user_data["selected_author"] = author_key
    user_data.pop("pending_question", None)
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


# =========================
# 💬 Обработка текстовых сообщений
# =========================
@router.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_text = (message.text or "").strip()
    if not user_text:
        return

    user_data = db.get_user_data(user_id)
    mode = user_data.get("mode")

    # если пользователь в выборе авторов по кнопкам
    if mode in ("compare_first", "compare_second", "dialog_first", "dialog_second"):
        await message.answer(
            "🧩 Сейчас нужно выбирать кнопками 👇",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        return

    author_key = user_data.get("selected_author")

    # ✅ НОВОЕ: если автор не выбран — пытаемся распознать и предложить варианты
    if not author_key:
        candidates = guess_authors_from_text(user_text)

        if candidates:
            # сохраняем вопрос, чтобы после нажатия кнопки сразу ответить
            user_data["pending_question"] = user_text
            db.save_user_data(user_id, user_data)

            lines = [
                "🔎 <b>Похоже, вопрос связан с конкретным автором/произведением.</b>",
                "Выбери, как отвечать:",
                ""
            ]
            for c in candidates:
                lines.append(f"• <b>{c['author_name']}</b> — {c['reason']}")

            await message.answer(
                "\n".join(lines),
                parse_mode=ParseMode.HTML,
                reply_markup=build_quick_author_keyboard(candidates)
            )
            return

        # если ничего надёжного не нашли — обычное поведение
        await message.answer(
            "❌ <b>Сначала выберите автора!</b>\n\n👇 Выберите эпоху:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_groups_keyboard()
        )
        return

    author = get_author(author_key)

    # =========================
    # 📝 РАЗБОР ТЕКСТА
    # =========================
    if mode == "analysis_text":
        prompt = (
            "Сделай литературный разбор текста пользователя.\n"
            "Структура:\n"
            "1) Тема и идея\n"
            "2) Настроение/тон\n"
            "3) Образы и художественные средства (2–6 примеров)\n"
            "4) Композиция/ритм (если стихи)\n"
            "5) Сильные места\n"
            "6) Что улучшить (бережно)\n\n"
            "Важно:\n"
            "- НЕ выдумывай авторство текста\n"
            "- Пиши понятно и структурировано\n\n"
            f"ТЕКСТ ПОЛЬЗОВАТЕЛЯ:\n{user_text}"
        )

        thinking = await message.answer(
            f"<i>📝 {author.get('name', author_key)} читает и разбирает…</i>",
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
                "<i>Можешь прислать ещё текст — разберу тоже.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_to_chat_keyboard()
            )
            return
        except Exception as e:
            logger.exception("Ошибка разбора: %s", e)
            try:
                await thinking.delete()
            except Exception:
                pass
            await message.answer(
                "⚠️ Не получилось сделать разбор. Попробуй ещё раз.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_to_chat_keyboard()
            )
            return

    # =========================
    # 🎓 ЕГЭ-РЕЖИМ
    # =========================
    if mode == "ege_mode":
        prompt = (
            "Ты помощник по литературе и ЕГЭ.\n"
            "Требования:\n"
            "- НЕ пиши полностью готовое сочинение под ключ\n"
            "- Дай: план, тезис, 2–3 аргумента, примеры, краткие цитаты (без длинных)\n"
            "- Дай 3–5 сильных формулировок\n"
            "- Если запрос неполный — предложи 2 варианта трактовки\n"
            "- Пиши структурировано\n\n"
            f"ЗАПРОС ПОЛЬЗОВАТЕЛЯ:\n{user_text}"
        )

        thinking = await message.answer(
            f"<i>🎓 {author.get('name', author_key)} помогает подготовиться…</i>",
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
                f"{author.get('name', author_key)}:\n\n{response}",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_to_chat_keyboard()
            )
            return
        except Exception as e:
            logger.exception("Ошибка ЕГЭ-режима: %s", e)
            try:
                await thinking.delete()
            except Exception:
                pass
            await message.answer(
                "⚠️ Не получилось помочь в ЕГЭ-режиме. Попробуй ещё раз.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_back_to_chat_keyboard()
            )
            return

    # =========================
    # 💬 ДИАЛОГ АВТОРОВ
    # =========================
    if mode == "dialog_wait_topic":
        first = user_data.get("dialog_first_author")
        second = user_data.get("dialog_second_author")

        if not first or not second:
            db.set_mode(user_id, None)
            await message.answer(
                "⚠️ Потерял выбранных авторов. Нажми «💬 Диалог авторов» ещё раз.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_chat_keyboard()
            )
            return

        a1 = get_author(first)
        a2 = get_author(second)

        prompt = (
            "Сгенерируй короткий, но содержательный диалог между двумя авторами.\n"
            "Формат:\n"
            "- 8–14 реплик\n"
            "- реплики строго чередуются\n"
            "- каждая реплика начинается с имени автора и двоеточия\n"
            "- в конце 1–2 строки итога\n\n"
            "Важно:\n"
            "- Без современного сленга\n"
            "- Без карикатуры\n\n"
            f"ТЕМА:\n{user_text}\n\n"
            f"ПЕРВЫЙ АВТОР: {a1.get('name', first)}\n"
            f"СТИЛЬ ПЕРВОГО: {a1.get('style_prompt','')}\n\n"
            f"ВТОРОЙ АВТОР: {a2.get('name', second)}\n"
            f"СТИЛЬ ВТОРОГО: {a2.get('style_prompt','')}\n"
        )

        thinking = await message.answer(
            "<i>💬 Авторы начинают разговор…</i>",
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

            db.set_mode(user_id, None)

            await message.answer(
                response,
                parse_mode=ParseMode.HTML,
                reply_markup=get_chat_keyboard()
            )
            return
        except Exception as e:
            logger.exception("Ошибка диалога авторов: %s", e)
            try:
                await thinking.delete()
            except Exception:
                pass
            await message.answer(
                "⚠️ Не получилось сделать диалог. Попробуй ещё раз.",
                parse_mode=ParseMode.HTML,
                reply_markup=get_chat_keyboard()
            )
            db.set_mode(user_id, None)
            return

    # =========================
    # ✍️ Соавторство
    # =========================
    if mode in ("cowrite_prose", "cowrite_poem"):
        genre = "рассказ" if mode == "cowrite_prose" else "стихотворение"
        prompt = (
            f"Мы пишем {genre} ВМЕСТЕ.\n"
            "Пользователь написал фрагмент ниже.\n\n"
            "Твоя задача:\n"
            "- органично ПРОДОЛЖИТЬ\n"
            "- сохранить стиль автора\n"
            "- НЕ завершать полностью\n\n"
            f"ФРАГМЕНТ:\n{user_text}"
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

    # =========================
    # 💬 Обычный чат
    # =========================
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


# =========================
# 🚀 Запуск
# =========================
async def main():
    if not BOT_TOKEN:
        raise RuntimeError("❌ BOT_TOKEN пуст. Добавь BOT_TOKEN в переменные окружения / .env")

    await start_web_server()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    limiter = InMemoryRateLimiter(RateLimitConfig())
    dp.message.middleware(AntiFloodMiddleware(limiter))

    dp.include_router(router)

    # на всякий случай выключаем webhook
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("🤖 Start polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
