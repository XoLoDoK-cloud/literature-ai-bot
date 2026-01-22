# gigachat_client.py
import asyncio
import logging
from typing import List, Optional

from authors import get_author
from database import db
from config import GIGACHAT_CREDENTIALS, GIGACHAT_SCOPE, RAG_TOP_K
from knowledge_base import retrieve_passages, is_fact_question, fact_snippet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole
    GIGACHAT_AVAILABLE = True
except ImportError:
    GIGACHAT_AVAILABLE = False
    logger.error("❌ Библиотека gigachat не установлена")


def _build_rag_block(passages: List[str]) -> str:
    if not passages:
        return ""
    # ограничим размер контекста
    trimmed = []
    total = 0
    for p in passages:
        p = p.strip()
        if not p:
            continue
        if total + len(p) > 1800:
            break
        trimmed.append(p)
        total += len(p)
    if not trimmed:
        return ""
    joined = "\n\n---\n\n".join(trimmed)
    return (
        "\n\nКОНТЕКСТ (факты из базы, используй только это; не выдумывай):\n"
        f"{joined}\n"
    )


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

    async def _chat(self, messages: List[Messages], temperature: float = 0.7) -> str:
        response = await asyncio.to_thread(
            self.client.chat,
            Chat(messages=messages, model="GigaChat:latest", temperature=temperature),
        )
        return response.choices[0].message.content.strip()

    async def generate_response(
        self,
        author_key: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
        cache_ttl_seconds: int = 3600,
    ) -> str:
        author = get_author(author_key)
        system_prompt = (author.get("system_prompt") or "Ты — русский писатель.").strip()

        # --- RAG контекст ---
        rag_passages = retrieve_passages(author_key, user_message, top_k=RAG_TOP_K)
        rag_block = _build_rag_block(rag_passages)

        # --- кэш (учитывает RAG) ---
        cache_key = db._make_cache_key(author_key, system_prompt, rag_block, user_message)
        cached = await db.cache_get(cache_key)
        if cached:
            return cached

        # --- если ИИ недоступен: отдаём факты, если это факт-вопрос ---
        if not self.client:
            if is_fact_question(user_message):
                facts = fact_snippet(author_key, user_message)
                if facts:
                    fallback = f"{facts}\n\n(ИИ недоступен — отвечаю фактами из базы.)"
                    await db.cache_set(cache_key, author_key, db._hash_text(user_message), fallback, ttl_seconds=cache_ttl_seconds)
                    return fallback
            return "ИИ временно недоступен. Попробуйте позже."

        # ------------------ УМНАЯ ЛОГИКА ------------------
        # 1) Если вопрос фактологический и факты есть:
        #    - сначала берём точный факт
        #    - затем просим ИИ кратко “обернуть” ответ стилем автора, не добавляя фактов
        if is_fact_question(user_message):
            facts = fact_snippet(author_key, user_message)
            if facts:
                # Стиль автора поверх факта (коротко, без выдумок)
                style_system = (
                    system_prompt
                    + "\n\nТвоя задача: ответь КОРОТКО на вопрос пользователя, "
                      "используя ТОЛЬКО факты из блока ФАКТЫ. "
                      "НЕЛЬЗЯ добавлять новые факты, даты, имена. "
                      "Если фактов недостаточно — скажи, что точных данных нет."
                    + "\n\nФАКТЫ:\n"
                    + facts
                )

                messages = [Messages(role=MessagesRole.SYSTEM, content=style_system)]
                messages.append(Messages(role=MessagesRole.USER, content=user_message))

                try:
                    styled = await self._chat(messages, temperature=0.4)
                    final = f"{facts}\n\n{styled}".strip()
                    await db.cache_set(cache_key, author_key, db._hash_text(user_message), final, ttl_seconds=cache_ttl_seconds)
                    return final
                except Exception as e:
                    logger.exception("❌ Ошибка стиль-обёртки факта: %s", e)
                    # если стиль не вышел — хотя бы факты
                    await db.cache_set(cache_key, author_key, db._hash_text(user_message), facts, ttl_seconds=cache_ttl_seconds)
                    return facts

        # 2) Иначе: обычный диалог с RAG контекстом + история
        messages = [
            Messages(role=MessagesRole.SYSTEM, content=system_prompt + rag_block)
        ]

        if conversation_history:
            for msg in conversation_history[-6:]:
                role = MessagesRole.USER if msg["role"] == "user" else MessagesRole.ASSISTANT
                messages.append(Messages(role=role, content=msg["content"]))

        messages.append(Messages(role=MessagesRole.USER, content=user_message))

        try:
            answer = await self._chat(messages, temperature=0.7)
            await db.cache_set(cache_key, author_key, db._hash_text(user_message), answer, ttl_seconds=cache_ttl_seconds)
            return answer
        except Exception as e:
            logger.exception("❌ Ошибка запроса к GigaChat: %s", e)
            # fallback: если факты есть — отдадим их
            facts = fact_snippet(author_key, user_message)
            if facts:
                fallback = f"{facts}\n\n(ИИ ответить не смог — отвечаю фактами из базы.)"
                await db.cache_set(cache_key, author_key, db._hash_text(user_message), fallback, ttl_seconds=600)
                return fallback
            return "ИИ временно недоступен. Попробуйте позже."


gigachat_client = GigaChatClient(GIG_
