# gigachat_client.py
import asyncio
from typing import List, Optional

try:
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole
    GIGACHAT_AVAILABLE = True
except ImportError:
    GIGACHAT_AVAILABLE = False

from config import GIGACHAT_CREDENTIALS
from authors import get_author
from knowledge_base import rag_search, format_rag_blocks


class GigaChatClient:
    def __init__(self, credentials: str = None):
        self.credentials = (credentials or "").strip()
        self.client = None

        if GIGACHAT_AVAILABLE and self.credentials:
            try:
                self.client = GigaChat(credentials=self.credentials, verify_ssl_certs=False)
            except Exception:
                self.client = None

    def _author_style_prompt(self, author_key: str) -> str:
        """
        Берём system_prompt из authors.py (он самый правильный).
        Если вдруг пусто — fallback.
        """
        author = get_author(author_key) or {}
        system_prompt = (author.get("system_prompt") or "").strip()
        if system_prompt:
            return system_prompt

        # fallback (на всякий случай)
        styles = {
            "pushkin": "Ты — Александр Сергеевич Пушкин. Ясно, изящно, иногда поэтично.",
            "dostoevsky": "Ты — Фёдор Михайлович Достоевский. Глубоко, психологично.",
            "tolstoy": "Ты — Лев Николаевич Толстой. Мудро и просто.",
            "gogol": "Ты — Николай Васильевич Гоголь. Иронично и образно.",
            "chekhov": "Ты — Антон Павлович Чехов. Коротко и точно.",
            "filatov": "Ты — Леонид Алексеевич Филатов. Иронично, интеллигентно, сатирично, но без грубости.",
        }
        return styles.get(author_key, "Ты — русский писатель. Отвечай умно и выразительно.")

    async def generate_response(
        self,
        author_key: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None
    ) -> str:
        # RAG: просто добавляем как контекст (без строгих правил и без 'в базе нет')
        blocks = rag_search(author_key, user_message, limit=7)
        rag_text = format_rag_blocks(blocks).strip()

        style = self._author_style_prompt(author_key)

        system_prompt = style + "\n\nПравила:\n" \
            "— Отвечай в стиле выбранного автора.\n" \
            "— Если есть блок KNOWLEDGE, используй его как дополнительную подсказку.\n" \
            "— Не упоминай слово KNOWLEDGE и не пиши, что 'в базе нет'. Просто отвечай.\n"

        if rag_text:
            system_prompt += "\nKNOWLEDGE:\n" + rag_text

        # Если ИИ недоступен — fallback: покажем, что нашёл RAG, либо скажем что ИИ недоступен
        if not self.client:
            if rag_text:
                return rag_text
            return "ИИ временно недоступен. Попробуйте позже."

        messages = [Messages(role=MessagesRole.SYSTEM, content=system_prompt)]

        # История диалога (чтобы бот нормально “помнил” контекст)
        if conversation_history:
            for msg in conversation_history[-6:]:
                role = MessagesRole.USER if msg.get("role") == "user" else MessagesRole.ASSISTANT
                messages.append(Messages(role=role, content=msg.get("content", "")))

        messages.append(Messages(role=MessagesRole.USER, content=user_message))

        try:
            response = await asyncio.to_thread(
                self.client.chat,
                Chat(messages=messages, model="GigaChat:latest", temperature=0.78)
            )
            return response.choices[0].message.content.strip()
        except Exception:
            # Если упало — попробуем хотя бы вернуть RAG, чтобы ответ был не пустой
            if rag_text:
                return rag_text
            return "Простите, я не смог ответить. Попробуйте переформулировать."

    async def compare_authors(self, narrator_author_key: str, a1: str, a2: str) -> str:
        """
        Сравнение БЕЗ строгих фактов.
        При желании можно использовать RAG по каждому автору как подсказку.
        """
        # RAG подсказки по авторам
        rag_a1 = format_rag_blocks(rag_search(a1, "биография стиль произведения темы", limit=7)).strip()
        rag_a2 = format_rag_blocks(rag_search(a2, "биография стиль произведения темы", limit=7)).strip()

        style = self._author_style_prompt(narrator_author_key)

        system_prompt = (
            style
            + "\n\nСравни двух авторов. Можно опираться на свои знания и подсказки ниже.\n"
              "Формат:\n"
              "🆚 Автор1 vs Автор2\n"
              "📚 Произведения\n"
              "🧠 Темы/мировоззрение\n"
              "✍️ Манера/стиль\n"
              "✅ 3 вывода\n"
        )

        if rag_a1:
            system_prompt += "\n\nПОДСКАЗКИ ПО АВТОРУ 1:\n" + rag_a1
        if rag_a2:
            system_prompt += "\n\nПОДСКАЗКИ ПО АВТОРУ 2:\n" + rag_a2

        if not self.client:
            # fallback без ИИ
            text = "ИИ временно недоступен.\n"
            if rag_a1 or rag_a2:
                text += "\n" + "\n".join([x for x in [rag_a1, rag_a2] if x])
            return text

        messages = [
            Messages(role=MessagesRole.SYSTEM, content=system_prompt),
            Messages(role=MessagesRole.USER, content=f"Сравни авторов: {a1} и {a2}.")
        ]

        try:
            response = await asyncio.to_thread(
                self.client.chat,
                Chat(messages=messages, model="GigaChat:latest", temperature=0.7)
            )
            return response.choices[0].message.content.strip()
        except Exception:
            if rag_a1 or rag_a2:
                return "\n\n".join([x for x in [rag_a1, rag_a2] if x])
            return "Не получилось сравнить. Попробуйте ещё раз."


gigachat_client = GigaChatClient(GIGACHAT_CREDENTIALS)
