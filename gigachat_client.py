# gigachat_client.py
import asyncio
import logging
from typing import List, Optional

from authors import get_author
from database import db
from config import GIGACHAT_CREDENTIALS, GIGACHAT_SCOPE
from knowledge_base import format_facts_for_user

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole
    GIGACHAT_AVAILABLE = True
except ImportError:
    GIGACHAT_AVAILABLE = False
    logger.error("❌ Библиотека gigachat не установлена")


def _is_fact_question(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    fact_markers = (
        "когда", "где", "кто", "сколько", "дата", "год",
        "родился", "родилась", "умер", "умерла", "причина смерти",
        "в каком году", "в каком", "место рождения", "где жил", "где учился"
    )
    if any(m in t for m in fact_markers):
        return True
    return len(t) <= 32 and t.endswith("?")


def _rag_block(rag_results: list[dict]) -> str:
    if not rag_results:
        return ""
    parts = []
    for r in rag_results[:5]:
        title = r.get("title", "Факт")
        content = (r.get("content", "") or "").strip()
        if content:
            parts.append(f"[{title}]\n{content}")
    return "\n\n".join(parts).strip()


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
        system_prompt = (author.get("system_prompt") or "Ты — русский писатель.").strip()

        rag_results = await db.kb_search(author_key=author_key, query=user_message, k=6)
        rag_text = _rag_block(rag_results)
        rag_fallback = format_facts_for_user(rag_results)

        want_fact = _is_fact_question(user_message) and bool(rag_results)

        knowledge_block = (
            f"\n\nФакты из базы знаний (используй только их, не выдумывай):\n{rag_text}\n"
            if rag_text else ""
        )

        cache_key = db._make_cache_key(author_key, system_prompt, knowledge_block, user_message)
        cached = await db.cache_get(cache_key)
        if cached:
            return cached

        if not self.client:
            if rag_fallback:
                out = rag_fallback + "\n\n(ИИ временно недоступен — отвечаю фактами из базы.)"
                await db.cache_set(cache_key, author_key, db._hash_text(user_message), out, ttl_seconds=600)
                return out
            return "ИИ временно недоступен. Попробуйте позже."

        messages = []

        if want_fact:
            sys = (
                system_prompt
                + "\n\nТы отвечаешь ТОЛЬКО по данным фактам ниже. Ничего не выдумывай."
                + "\nОтвет: сначала 2–6 пунктов фактов, потом 1–2 предложения в стиле автора."
                + knowledge_block
            )
            messages.append(Messages(role=MessagesRole.SYSTEM, content=sys))
            messages.append(Messages(role=MessagesRole.USER, content=user_message))
        else:
            sys = (
                system_prompt
                + "\n\nЕсли в блоке фактов есть нужные сведения — опирайся на них и не выдумывай."
                + knowledge_block
            )
            messages.append(Messages(role=MessagesRole.SYSTEM, content=sys))

            if conversation_history:
                for msg in conversation_history[-6:]:
                    role = MessagesRole.USER if msg["role"] == "user" else MessagesRole.ASSISTANT
                    messages.append(Messages(role=role, content=msg["content"]))

            messages.append(Messages(role=MessagesRole.USER, content=user_message))

        try:
            response = await asyncio.to_thread(
                self.client.chat,
                Chat(
                    messages=messages,
                    model="GigaChat:latest",
                    temperature=0.65 if want_fact else 0.75,
                ),
            )
            answer = response.choices[0].message.content.strip()

            await db.cache_set(
                cache_key,
                author_key,
                db._hash_text(user_message),
                answer,
                ttl_seconds=7200 if want_fact else cache_ttl_seconds,
            )
            return answer

        except Exception as e:
            logger.exception("❌ Ошибка запроса к GigaChat: %s", e)
            if rag_fallback:
                out = rag_fallback + "\n\n(ИИ ответить не смог — отвечаю фактами из базы.)"
                await db.cache_set(cache_key, author_key, db._hash_text(user_message), out, ttl_seconds=600)
                return out
            return "ИИ временно недоступен. Попробуйте позже."


gigachat_client = GigaChatClient(GIGACHAT_CREDENTIALS)
