import os
import asyncio
import logging

from aiohttp import web

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode

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

    port = int(os.getenv("PORT", "10000"))
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()

    logger.info("🌐 Web server started on 0.0.0.0:%s", port)


# =========================
# 🤖 Команды / UI
# =========================
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    db.reset_compare(user_id)
    db.set_mode(user_id, None)

    # сбрасываем временные поля диалога авторов
    user_data = db.get_user_data(user_id)
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

    # сброс диалога авторов
    user_data = db.get_user_data(user_id)
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

    # сброс диалога авторов
    user_data = db.get_user_data(user_id)
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

    # сброс диалога авторов
    user_data = db.get_user_data(user_id)
    user_data.pop("dialog_first_author", None)
    user_data.pop("dialog_second_author", None)
    db.save_user_data(user_id, user_data)

    await cmd_start(callback.message)
    await callback.answer()


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
        "• подбор примеров из произведения\n"
        "• как сравнить героев / темы\n\n"
        "⚠️ Я НЕ пишу полностью готовое сочинение за тебя.\n"
        "Я даю структуру и сильные формулировки — чтобы ты сам сделал работу.\n\n"
        "<i>Пример запроса:</i>\n"
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

    # подготовка хранения
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

    # ---- РЕЖИМ: сравнение авторов (как было) ----
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

    # ---- НОВОЕ: выбор авторов для диалога ----
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

    # ---- Обычный выбор автора (как было) ----
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
    if not author_key:
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
            "Обязательно структурируй ответ в пунктах:\n"
            "1) Тема и идея\n"
            "2) Настроение/тон\n"
            "3) Образы и художественные средства (2–6 примеров)\n"
            "4) Композиция/ритм (если стихи)\n"
            "5) Сильные места\n"
            "6) Что можно улучшить (бережно, по делу)\n\n"
            "Важно:\n"
            "- НЕ выдумывай факты об авторстве текста\n"
            "- Не приписывай строки другим авторам\n"
            "- Пиши ясно, как для ученика\n\n"
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
            "Пользователь пишет запрос по литературе/сочинению.\n\n"
            "Требования:\n"
            "- НЕ пиши полностью готовое итоговое сочинение/ответ 'под ключ'\n"
            "- Дай: план, тезис, 2–3 аргумента, примеры/эпизоды, возможные цитаты (без длинных цитат)\n"
            "- Дай 3–5 сильных формулировок, которые ученик может использовать\n"
            "- Если запрос неполный — предложи 2 варианта трактовки\n"
            "- Пиши понятно и структурированно\n\n"
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
            "- в конце сделай 1–2 строки итога (не морализировать)\n\n"
            "Важно:\n"
            "- Первый автор говорит в своём стиле, второй — в своём\n"
            "- Не используй современный сленг\n"
            "- Не делай карикатуру, пусть будет 'настоящая' интонация\n\n"
            f"ТЕМА:\n{user_text}\n\n"
            f"ПЕРВЫЙ АВТОР: {a1.get('name', first)}\n"
            f"СТИЛЬ ПЕРВОГО: {a1.get('style_prompt','')}\n\n"
            f"ВТОРОЙ АВТОР: {a2.get('name', second)}\n"
            f"СТИЛЬ ВТОРОГО: {a2.get('style_prompt','')}\n"
        )

        thinking = await message.answer(
            "<i>💬 Авторы начинают спор/разговор…</i>",
            parse_mode=ParseMode.HTML
        )

        try:
            # Берём "основной голос" пользователя как narrator (выбранный автор)
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
    # ✍️ Соавторство (как было)
    # =========================
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

    # =========================
    # 💬 Обычный чат (как было)
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
