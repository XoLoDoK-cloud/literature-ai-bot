import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден!")

print("✅ Конфигурация загружена")
