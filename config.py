# config.py
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")
GIGACHAT_SCOPE = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")

# --- Anti-flood / rate-limit ---
# короткое окно: N сообщений за WINDOW сек
RATE_LIMIT_MAX = int(os.getenv("RATE_LIMIT_MAX", "5"))
RATE_LIMIT_WINDOW_SEC = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "10"))

# длинное окно: N сообщений за HOUR сек
RATE_LIMIT_HOURLY_MAX = int(os.getenv("RATE_LIMIT_HOURLY_MAX", "60"))
RATE_LIMIT_HOURLY_WINDOW_SEC = int(os.getenv("RATE_LIMIT_HOURLY_WINDOW_SEC", str(60 * 60)))

# cooldown на тяжёлые запросы (когда идём в ИИ), в секундах
AI_COOLDOWN_SEC = int(os.getenv("AI_COOLDOWN_SEC", "2"))

# сколько пасажей из RAG подставлять в ИИ
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))

if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не задан")

if not GIGACHAT_CREDENTIALS:
    print("⚠️ GIGACHAT_CREDENTIALS не задан — ИИ будет отключён")

print("✅ Конфигурация загружена")
