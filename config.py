import os
from dotenv import load_dotenv
load_dotenv()
# Токены
BOT_TOKEN = os.getenv("BOT_TOKEN")
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")
# Проверка
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден!")
if not GIGACHAT_CREDENTIALS:
    print("⚠️ GIGACHAT_CREDENTIALS не найден, будут использоваться заглушки")
print("✅ Конфигурация загружена")
