import os
from dotenv import load_dotenv

load_dotenv()

# Токены
BOT_TOKEN = os.getenv("BOT_TOKEN")
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")

# Проверка
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN не найден в .env файле!")

if not GIGACHAT_CREDENTIALS or GIGACHAT_CREDENTIALS == "ваш_ключ_gigachat_здесь":
    print("⚠️ ВНИМАНИЕ: GIGACHAT_CREDENTIALS не настроен")
    GIGACHAT_CREDENTIALS = None

print("✅ Конфигурация загружена")
