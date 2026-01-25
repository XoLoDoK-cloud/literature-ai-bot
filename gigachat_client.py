import asyncio
from typing import List, Optional

try:
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole
    GIGACHAT_AVAILABLE = True
except ImportError:
    GIGACHAT_AVAILABLE = False

from config import GIGACHAT_CREDENTIALS
from knowledge_base import rag_search, format_rag_blocks, get_author_card, format_compare_facts

# ✅ ВАЖНО: берём стиль автора из вашего authors.py
from authors import get_author


def _is_fact_question(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    markers = (
        "когда", "где", "кто", "сколько", "дата", "год",
        "родился", "родилась", "умер", "умерла",
        "место рождения", "причина смерти", "в каком году", "где учился"
    )
    return any(m in t for m in markers)


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
        1) Пытаемся взять system_prompt из authors.py
        2) Если его нет — используем старый fallback styles
        """
        author = get_author(author_key) or {}
        system_prompt = (author.get("system_prompt") or "").strip()
        if system_prompt:
            return system_prompt

        # fallback (старое поведение, чтобы не ломать совместимость)
        styles = {
            "pushkin": "Ты — Александр Сергеевич Пушкин. Ясно, изящно, иногда поэтично. Даты не выдумывай.",
            "dostoevsky": "Ты — Фёдор Михайлович Достоевский. Глубоко, психологично. Даты не выдумывай.",
            "tolstoy": "Ты — Лев Николаевич Толстой. Мудро и просто. Даты не выдумывай.",
            "gogol": "Ты — Николай Васильевич Гоголь. Иронично и образно. Даты не выдумывай.",
            "chekhov": "Ты — Антон Павлович Чехов. Коротко и точно. Даты не выдумывай.",
            "gigachad": "Ты — Гигачад. Энергично и мотивирующе. Но факты не выдумывай.",
        }
        return styles.get(author_key, "Ты — русский писатель. Отвечай умно и без выдуманных фактов.")

    async def generate_response(
        self,
        author_key: str,
        user_message: str,
        conversation_history: Optional[List[dict]] = None
    ) -> str:
        # RAG 2.0
        blocks = rag_search(author_key, user_message, limit=7)
        rag_text = format_rag_blocks(blocks)

        fact_mode = _is_fact_question(user_message) and bool(rag_text)
        style = self._author_style_prompt(author_key)

        if fact_mode:
            system_prompt = (
                style
                + "\n\nСТРОГИЙ РЕЖИМ ФАКТОВ:"
                + "\n1) Отвечай ТОЛЬКО по фактам из блока KNOWLEDGE."
                + "\n2) Если факта нет в KNOWLEDGE — скажи: «В моей базе этого нет»."
                + "\n3) Формат: сначала 2–6 пунктов фактов, затем 1–2 предложения в стиле автора."
                + "\n\nKNOWLEDGE:\n" + rag_text
            )
        else:
            system_prompt = (
                style
                + "\n\nЕсли в KNOWLEDGE есть полезные сведения — используй их. Не выдумывай даты."
                + (("\n\nKNOWLEDGE:\n" + rag_text) if rag_text else "")
            )

        # если ИИ недоступен — fallback фактами
        if not self.client:
            if rag_text:
                return "Вот что есть в базе:\n\n" + rag_text
            return "ИИ временно недоступен. Попробуйте позже."

        messages = [Messages(role=MessagesRole.SYSTEM, content=system_prompt)]

        # история только если не факт-режим (чтобы не ломать точность)
        if not fact_mode and conversation_history:
            for msg in conversation_history[-4:]:
                role = MessagesRole.USER if msg["role"] == "user" else MessagesRole.ASSISTANT
                messages.append(Messages(role=role, content=msg["content"]))

        messages.append(Messages(role=MessagesRole.USER, content=user_message))

        try:
            response = await asyncio.to_thread(
                self.client.chat,
                Chat(messages=messages, model="GigaChat:latest", temperature=0.65 if fact_mode else 0.75)
            )
            return response.choices[0].message.content.strip()
        except Exception:
            if rag_text:
                return "Вот что есть в базе:\n\n" + rag_text
            return "Простите, я не смог ответить. Попробуйте переформулировать."

    async def compare_authors(self, narrator_author_key: str, a1: str, a2: str) -> str:
        card1 = get_author_card(a1)
        card2 = get_author_card(a2)

        if not card1 or not card2:
            return "Не могу сравнить — не нашёл одного из авторов в базе."

        facts1 = format_compare_facts(card1)
        facts2 = format_compare_facts(card2)

        # fallback без ИИ
        if not self.client:
            return (
                f"🆚 <b>{card1['full_name']}</b> vs <b>{card2['full_name']}</b>\n\n"
                f"<b>{card1['full_name']}:</b>\n<pre>{facts1}</pre>\n\n"
                f"<b>{card2['full_name']}:</b>\n<pre>{facts2}</pre>"
            )

        style = self._author_style_prompt(narrator_author_key)
        system_prompt = (
            style
            + "\n\nСравни двух авторов СТРОГО по фактам ниже. Запрещено выдумывать даты/произведения."
            + "\nФормат:"
            + "\n🆚 Автор1 vs Автор2"
            + "\n📚 Произведения"
            + "\n🧠 Темы/мировоззрение"
            + "\n✍️ Манера/стиль"
            + "\n✅ 3 вывода"
            + "\n\nFACTS_A:\n" + facts1
            + "\n\nFACTS_B:\n" + facts2
        )

        messages = [
            Messages(role=MessagesRole.SYSTEM, content=system_prompt),
            Messages(role=MessagesRole.USER, content="Сравни этих двух авторов по фактам выше.")
        ]

        try:
            response = await asyncio.to_thread(
                self.client.chat,
                Chat(messages=messages, model="GigaChat:latest", temperature=0.6)
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return (
                f"🆚 <b>{card1['full_name']}</b> vs <b>{card2['full_name']}</b>\n\n"
                f"<b>{card1['full_name']}:</b>\n<pre>{facts1}</pre>\n\n"
                f"<b>{card2['full_name']}:</b>\n<pre>{facts2}</pre>"
            )


gigachat_client = GigaChatClient(GIGACHAT_CREDENTIALS)
