import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Update,
)

from config import BOT_TOKEN
from database import db
from gigachat_client import gigachat_client

# ----------------- ЛОГИ -----------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ----------------- AIROGRAM -----------------
router = Router()

# Данные о писателях
AUTHORS = {
    "pushkin": {"name": "🖋️ Александр Пушкин", "greeting": "Здравствуйте! Рад нашей беседе. Что желаете узнать?"},
    "dostoevsky": {"name": "📚 Фёдор Достоевский", "greeting": "Здравствуйте. Что тревожит вашу душу?"},
    "tolstoy": {"name": "✍️ Лев Толстой", "greeting": "Здравствуйте, друг мой. Поговорим о важном?"},
    "gogol": {"name": "👻 Николай Гоголь", "greeting": "А, вот и вы! Любопытно, что вы хотите узнать?"},
    "chekhov": {"name": "🏥 Антон Чехов", "greeting": "Здравствуйте. Рассказывайте. Краткость — сестра таланта."},
    "gigachad": {"name": "💪 ГИГАЧАД", "greeting": "СЛУШАЙ СЮДА! Готов прокачать твой мозг классикой! 🔥"},
}

def get_authors_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    buttons.append([
        InlineKeyboardButton(text="🖋️ Пушкин", callback_data="author_pushkin"),
        InlineKeyboardButton(text="📚 Достоевский", callback_data="author_dostoevsky"),
        InlineKeyboardButton(text="✍️ Толстой", callback_data="author_tolstoy"),
    ])
    buttons.append([
        InlineKeyboardButton(text="👻 Гоголь", callback_data="author_gogol"),
        InlineKeyboardButton(text="🏥 Чехов", callback_data="author_chekhov"),
        InlineKeyboardButton(text="💪 ГИГАЧАД", callback_data="author_gigachad"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_chat_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(text="👥 Сменить автора", callback_data="change_author"),
            InlineKeyboardButton(text="🔄 Новый диалог", callback_data="reset_chat"),
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ----------------- КОМАНДЫ -----------------
@router.message(CommandStart())
async def cmd_start(message: Message):
    user_name = message.from_user.first_name if message.from_user else "Друг"
    welcome_text = f"""
✨ <b>ЛИТЕРАТУРНЫЙ ДИАЛОГ</b> ✨

👋 <b>Привет, {user_name}!</b>

💬 <b>Я могу представить любого русского классика.</b>
<b>Выберите писателя и задайте ему любой вопрос.</b>

👇 <b>Выберите автора для диалога:</b>
"""
    await message.answer(
        welcome_text,
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard()
    )

@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
📚 <b>ПОМОЩЬ ПО БОТУ</b>

✨ <b>Как использовать:</b>

1. <b>Выберите автора</b> из списка
2. <b>Задавайте вопросы</b> о:
   • Литературе и творчестве
   • Жизни и философии
   • Исторических событиях
   • Любых других темах

3. <b>Управляйте диалогом:</b>
   • 👥 Сменить автора — выбрать нового писателя
   • 🔄 Новый диалог — начать разговор заново
   • 🏠 Главное меню — вернуться к выбору автора

💡 <i>Бот использует ИИ GigaChat и базу знаний о писателях</i>
"""
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@router.message(Command("authors"))
async def cmd_authors(message: Message):
    await message.answer(
        "👥 <b>ВСЕ ПИСАТЕЛИ</b>\n\nВыберите автора для диалога:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard()
    )

# ----------------- ВЫБОР АВТОРА -----------------
@router.callback_query(F.data.startswith("author_"))
async def author_selected(callback: CallbackQuery):
    author_key = callback.data.split("_")[1]

    if author_key not in AUTHORS:
        await callback.answer("Автор не найден")
        return

    author = AUTHORS[author_key]
    user_id = callback.from_user.id

    user_data = db.get_user_data(user_id)
    user_data["selected_author"] = author_key
    db.save_user_data(user_id, user_data)

    await callback.message.edit_text(
        f"{author['name']}\n\n💬 {author['greeting']}\n\n<i>Задавайте вопросы — отвечу в своём стиле!</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_chat_keyboard()
    )
    await callback.answer(f"Выбран: {author['name']}")

@router.callback_query(F.data == "change_author")
async def change_author(callback: CallbackQuery):
    await callback.message.edit_text(
        "👥 <b>Выберите автора:</b>",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "reset_chat")
async def reset_chat(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    user_data["conversation_history"] = []
    user_data["selected_author"] = None
    db.save_user_data(user_id, user_data)

    await callback.message.edit_text(
        "🔄 <b>Диалог сброшен!</b>\n\nВыберите нового автора:",
        parse_mode=ParseMode.HTML,
        reply_markup=get_authors_keyboard()
    )
    await callback.answer("Диалог сброшен")

@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    await cmd_start(callback.message)
    await callback.answer()

# ----------------- СООБЩЕНИЯ -----------------
@router.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)

    if not user_data.get("selected_author"):
        await message.answer(
            "❌ <b>Сначала выберите автора!</b>\n\nИспользуйте кнопки ниже:",
            parse_mode=ParseMode.HTML,
            reply_markup=get_authors_keyboard()
        )
        return

    author_key = user_data["selected_author"]
    author = AUTHORS.get(author_key)

    user_text = message.text

    thinking_msg = await message.answer(
        f"<i>✨ {author['name']} обдумывает ответ.</i>",
        parse_mode=ParseMode.HTML
    )

    try:
        response = await gigachat_client.generate_response(
            author_key=author_key,
            user_message=user_text,
            conversation_history=user_data.get("conversation_history", [])
        )

        await thinking_msg.delete()

        response_text = f"{author['name']}\n\n{response}\n\n<code>💭 Продолжайте диалог или используйте кнопки</code>"
        await message.answer(
            response_text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_chat_keyboard()
        )

        db.update_conversation(user_id, author_key, user_text, response)

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.answer(
            "⚠️ <b>Произошла ошибка!</b>\n\nПопробуйте:\n1. Перезапустить бота /start\n2. Задать вопрос по-другому",
            parse_mode=ParseMode.HTML
        )

# ----------------- WEBHOOK (вместо polling) -----------------
WEBHOOK_PATH = "/webhook"

def get_base_url() -> str:
    # Render даёт домен в переменной окружения
    host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
    if host:
        return f"https://{host}"

    # запасной вариант: можно вручную задать WEBHOOK_BASE_URL в Render Env
    manual = os.getenv("WEBHOOK_BASE_URL")
    if manual:
        return manual.rstrip("/")

    raise RuntimeError("Не найден RENDER_EXTERNAL_HOSTNAME и WEBHOOK_BASE_URL")

async def handle_webhook(request: web.Request) -> web.Response:
    update = Update.model_validate(await request.json())
    await request.app["dp"].feed_update(request.app["bot"], update)
    return web.Response(text="ok")

async def on_startup(app: web.Application):
    bot: Bot = app["bot"]
    webhook_url = app["base_url"] + WEBHOOK_PATH

    # сбросим старый polling/webhook и очистим старые апдейты
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(webhook_url)

    logger.info("✅ Webhook установлен: %s", webhook_url)

async def on_shutdown(app: web.Application):
    bot: Bot = app["bot"]
    await bot.delete_webhook()
    logger.info("🛑 Webhook удалён")

async def main():
    print("=" * 50)
    print("🚀 ЗАПУСК ЛИТЕРАТУРНОГО БОТА (WEBHOOK)")
    print("=" * 50)
    print(f"🤖 Бот: {'✅ Токен загружен' if BOT_TOKEN else '❌ Токен не найден'}")
    print(f"🧠 ИИ: {'✅ GigaChat доступен' if getattr(gigachat_client, 'client', None) else '❌ GigaChat недоступен'}")
    print("=" * 50)

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    app = web.Application()
    app["bot"] = bot
    app["dp"] = dp
    app["base_url"] = get_base_url()

    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    port = int(os.getenv("PORT", "10000"))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logger.info("🚀 Бот запущен в режиме webhook на порту %s", port)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
