# gigachat_client.py
import asyncio
import logging
from typing import List, Optional

from authors import get_author
from knowledge_base import search_in_knowledge
from database import db
from config import GIGACHAT_CREDENTIALS, GIGACHAT_SCOPE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole
    GIGACHAT_AVAILABLE = True
except ImportError:
    GIGACHAT_AVAILABLE = False
    logger.error("❌ Библиотека gigachat не установлена")


class GigaChatClient:
    def __init__(self, credentials: Optional[str]):
        self.credentials = (credentials or "").strip()
        self.client = None

        if not GIGACHAT_AVAILABLE:
            logger.error("❌ GigaChat SDK недоступен")
            return

        if not self.credentials:
            logger.error("❌ GIGACHAT_CREDENTIALS пуст")
            return

        try:
            self.client = GigaChat(
                credentials=self.credentials,
                scope=GIGACHAT_SCOPE,
                verify_ssl_certs=False,
            )
            logger.info("✅ GigaChat подключен (scope=%s)", GIGACHAT_SCOPE)
        except Exception as e:
            logger.exception("❌ Ошибка инициализации GigaChat: %s", e)
            self.client = None

    async def generate_response(
        self,
        author_key: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
        cache_ttl_seconds: int = 3600,
    ) -> str:
        author = get_author(author_key)
        system_prompt = (
            author.get("system_prompt")
            or "Ты — русский писатель. Отвечай умно и интересно."
        ).strip()

        # ---- БАЗА ЗНАНИЙ ----
        knowledge_hint = search_in_knowledge(author_key, user_message).strip()
        knowledge_block = (
            "\n\nФакты из базы знаний (используй их, не выдумывай):\n"
            f"{knowledge_hint}\n"
            if knowledge_hint
            else ""
        )

        # ---- КЭШ ----
        cache_key = db._make_cache_key(
            author_key, system_prompt, knowledge_block, user_message
        )
        cached = await db.cache_get(cache_key)
        if cached:
            return cached

        # ---- ЕСЛИ ИИ НЕДОСТУПЕН ----
        if not self.client:
            logger.warning("⚠️ GigaChat client = None, используется база знаний")
            if knowledge_hint:
                fallback = (
                    f"{knowledge_hint}\n\n"
                    "(ИИ ответить не смог — отвечаю фактами из базы.)"
                )
                await db.cache_set(
                    cache_key,
                    author_key,
                    db._hash_text(user_message),
                    fallback,
                    ttl_seconds=cache_ttl_seconds,
                )
                return fallback
            return "ИИ временно недоступен. Попробуйте позже."

        # ---- СООБЩЕНИЯ ДЛЯ ИИ ----
        messages = [
            Messages(
                role=MessagesRole.SYSTEM,
                content=system_prompt + knowledge_block,
            )
        ]

        if conversation_history:
            for msg in conversation_history[-4:]:
                role = (
                    MessagesRole.USER
                    if msg["role"] == "user"
                    else MessagesRole.ASSISTANT
                )
                messages.append(Messages(role=role, content=msg["content"]))

        messages.append(
            Messages(role=MessagesRole.USER, content=user_message)
        )

        # ---- ВЫЗОВ ИИ ----
        try:
            response = await asyncio.to_thread(
                self.client.chat,
                Chat(
                    messages=messages,
                    model="GigaChat:latest",
                    temperature=0.7,
                ),
            )
            answer = response.choices[0].message.content.strip()

            await db.cache_set(
                cache_key,
                author_key,
                db._hash_text(user_message),
                answer,
                ttl_seconds=cache_ttl_seconds,
            )
            return answer

        except Exception as e:
            logger.exception("❌ Ошибка запроса к GigaChat: %s", e)
            if knowledge_hint:
                fallback = (
                    f"{knowledge_hint}\n\n"
                    "(ИИ ответить не смог — отвечаю фактами из базы.)"
                )
                await db.cache_set(
                    cache_key,
                    author_key,
                    db._hash_text(user_message),
                    fallback,
                    ttl_seconds=600,
                )
                return fallback
            return "ИИ временно недоступен. Попробуйте позже."


# ---- ГЛОБАЛЬНЫЙ КЛИЕНТ ----
gigachat_client = GigaChatClient(GIGACHAT_CREDENTIALS)
