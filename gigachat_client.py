# gigachat_client.py
import asyncio
from typing import List, Optional

try:
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole
    GIGACHAT_AVAILABLE = True
except ImportError:
    GIGACHAT_AVAILABLE = False

from authors import get_author
from knowledge_base import search_in_knowledge
from database import db


class GigaChatClient:
    def __init__(self, credentials: Optional[str] = None):
        self.credentials = credentials
        self.client = None

        if GIGACHAT_AVAILABLE and credentials:
            try:
                # verify_ssl_certs=False — как у тебя было (часто нужно в некоторых окружениях)
                self.client = GigaChat(credentials=credentials, verify_ssl_certs=False)
                print("✅ GigaChat подключен")
            except Exception as e:
                print(f"❌ Ошибка подключения GigaChat: {e}")
                self.client = None
        else:
            print("⚠️ GigaChat недоступен (нет библиотеки или credentials)")

    async def generate_response(
        self,
        author_key: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None,
        cache_ttl_seconds: int = 3600,
    ) -> str:
        author = get_author(author_key)
        system_prompt = (author.get("system_prompt") or "Ты — русский писатель. Отвечай умно и интересно.").strip()

        # 1) Подмешиваем базу знаний (если находит что-то по запросу)
        knowledge_hint = search_in_knowledge(author_key, user_message).strip()
        if knowledge_hint:
            knowledge_block = (
                "\n\nФакты из базы знаний (используй их, не выдумывай):\n"
                f"{knowledge_hint}\n"
            )
        else:
            knowledge_block = ""

        # 2) Кэш: ключ зависит от автора + системного промпта + knowledge + вопроса
        cache_key = db._make_cache_key(author_key, system_prompt, knowledge_block, user_message)
        cached = await db.cache_get(cache_key)
        if cached:
            return cached

        # 3) Если ИИ недоступен — фолбэк: база знаний или аккуратная заглушка
        if not self.client:
            if knowledge_hint:
                fallback = f"{knowledge_hint}\n\n(ИИ временно недоступен — отвечаю фактами из базы.)"
                await db.cache_set(cache_key, author_key, db._hash_text(user_message), fallback, ttl_seconds=cache_ttl_seconds)
                return fallback
            return "ИИ временно недоступен. Попробуйте позже."

        # 4) Собираем сообщения
        messages = [Messages(role=MessagesRole.SYSTEM, content=system_prompt + knowledge_block)]

        if conversation_history:
            # берём последние 4 сообщения (как у тебя было), чтобы не раздувать контекст
            for msg in conversation_history[-4:]:
                role = MessagesRole.USER if msg["role"] == "user" else MessagesRole.ASSISTANT
                messages.append(Messages(role=role, content=msg["content"]))

        messages.append(Messages(role=MessagesRole.USER, content=user_message))

        try:
            response = await asyncio.to_thread(
                self.client.chat,
                Chat(messages=messages, model="GigaChat:latest", temperature=0.7),
            )
            answer = response.choices[0].message.content.strip()

            await db.cache_set(cache_key, author_key, db._hash_text(user_message), answer, ttl_seconds=cache_ttl_seconds)
            return answer

        except Exception as e:
            print(f"❌ Ошибка GigaChat: {e}")
            # если есть база знаний — лучше отдать её, чем просто ошибку
            if knowledge_hint:
                fallback = f"{knowledge_hint}\n\n(ИИ ответить не смог — отвечаю фактами из базы.)"
                await db.cache_set(cache_key, author_key, db._hash_text(user_message), fallback, ttl_seconds=600)
                return fallback
            return "Простите, я задумался над вашим вопросом. Попробуйте переформулировать."


# Инициализация (credentials берём из config)
from config import GIGACHAT_CREDENTIALS
gigachat_client = GigaChatClient(GIGACHAT_CREDENTIALS)
