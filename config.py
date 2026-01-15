import os
from dotenv import load_dotenv

load_dotenv()

# Токены
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Проверка
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден!")
if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY не найден, будут использоваться заглушки")

print("✅ Конфигурация загружена")
