import os
from dotenv import load_dotenv

load_dotenv()

# Токены
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Проверка
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Добавьте в Railway Variables")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY не найден! Добавьте в Railway Variables")

print("✅ Конфигурация загружена")
