# config.py
import os
from dotenv import load_dotenv

# Загружаем .env (локально) и переменные окружения (Render)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")

# ВАЖНО: scope для GigaChat
# Для обычного ключа (физлицо) — GIGACHAT_API_PERS
# Для корпоративного — GIGACHAT_API_B2B или GIGACHAT_API_CORP
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не задан")

if not GIGACHAT_CREDENTIALS:
    print("⚠️ GIGACHAT_CREDENTIALS не задан — ИИ будет отключён")

print("✅ Конфигурация загружена")
