import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiohttp import web

from config import BOT_TOKEN

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# импортируй свои хендлеры
from handlers import router  # если у тебя другое имя — поправь
dp.include_router(router)


# ---------- WEBHOOK ----------

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = None  # установим при старте


async def on_startup(app: web.Application):
    global WEBHOOK_URL
    WEBHOOK_URL = app["base_url"] + WEBHOOK_PATH
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"✅ Webhook установлен: {WEBHOOK_URL}")


async def on_shutdown(app: web.Application):
    await bot.delete_webhook()
    logging.info("🛑 Webhook удалён")


async def handle_webhook(request: web.Request):
    update = Update.model_validate(await request.json())
    await dp.feed_update(bot, update)
    return web.Response()


async def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)

    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)

    # Render сам прокидывает PORT
    port = int(__import__("os").environ.get("PORT", 10000))
    app["base_url"] = f"https://{__import__('os').environ['RENDER_EXTERNAL_HOSTNAME']}"

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

    logging.info("🚀 Бот запущен в режиме webhook")
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())

