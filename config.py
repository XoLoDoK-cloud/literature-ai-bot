import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Токены
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Проверяем, что ключи загрузились
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден! Проверьте .env файл")
if not GEMINI_API_KEY:
    raise ValueError("❌ GEMINI_API_KEY не найден! Проверьте .env файл")

print("✅ Конфигурация загружена")
print(f"🤖 Токен бота: {BOT_TOKEN[:15]}...")
print(f"🔑 Gemini ключ: {GEMINI_API_KEY[:10]}...")
