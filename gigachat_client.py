import asyncio
from typing import List, Optional

try:
    from gigachat import GigaChat
    from gigachat.models import Chat, Messages, MessagesRole
    GIGACHAT_AVAILABLE = True
except ImportError:
    GIGACHAT_AVAILABLE = False
    print("⚠️ GigaChat библиотека не установлена")

from config import GIGACHAT_CREDENTIALS
from knowledge_base import rag_search, format_rag_blocks, get_author_card, format_compare_facts


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
        self.credentials = credentials
        self.client = None

        if GIGACHAT_AVAILABLE and credentials:
            try:
                self.client = GigaChat(credentials=credentials, verify_ssl_certs=False)
                print("✅ GigaChat подключен")
            except Exception as e:
                print(f"❌ Ошибка GigaChat: {e}")
                self.client = None
        else:
            print("⚠️ GigaChat недоступен")

    def _author_style_prompt(self, author_key: str) -> str:
        # короткий стиль (без огромных фактов — факты даст RAG)
        styles = {
            "pushkin": "Ты — Александр Сергеевич Пушкин. Ясно, изящно, иногда поэтично. Без выдумок дат.",
            "dostoevsky": "Ты — Фёдор Михайлович Достоевский. Глубоко, психологично. Даты не выдумывай.",
            "tolstoy": "Ты — Лев Николаевич Толстой. Мудро и просто. Даты не выдумывай.",
            "gogol": "Ты — Николай Васильевич Гоголь. Иронично, образно. Даты не выдумывай.",
            "chekhov": "Ты — Антон Павлович Чехов. Коротко и точно. Даты не выдумывай.",
            "gigachad": "Ты — Гигачад. Энергично и мотивирующе. Но факты не выдумывай."
        }
        return styles.get(author_key, "Ты — русский писатель. Отвечай умно и без выдуманных фактов.")

    async def generate_response(self, author_key: str, user_message: str, conversation_history: Optional[List[dict]] = None) -> str:
        if not self.client:
            return "Извините, ИИ временно недоступен. Попробуйте позже."

        # RAG 2.0: достаём факты
        blocks = rag_search(author_key, user_message, limit=7)
        rag_text = format_rag_blocks(blocks)

        fact_mode = _is_fact_question(user_message) and bool(rag_text)

        style = self._author_style_prompt(author_key)

        if fact_mode:
            system_prompt = (
                style
                + "\n\nСТРОГИЙ РЕЖИМ ФАКТОВ:"
                + "\n1) Отвечай ТОЛЬКО по фактам из блока KNOWLEDGE."
                + "\n2) Если факта нет в KNOWLEDGE — так и скажи: «В моей базе этого нет»."
                + "\n3) Формат: сначала 2–6 пунктов фактов, затем 1–2 предложения в стиле автора."
                + "\n\nKNOWLEDGE:\n" + rag_text
            )
        else:
            system_prompt = (
                style
                + "\n\nЕсли в KNOWLEDGE есть полезные сведения — используй их. Не выдумывай даты."
                + ("\n\nKNOWLEDGE:\n" + rag_text if rag_text else "")
            )

        messages = [Messages(role=MessagesRole.SYSTEM, content=system_prompt)]

        # история — только если НЕ факт-режим (иначе она мешает точности)
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
        except Exception as e:
            print(f"❌ Ошибка GigaChat: {e}")
            # fallback: если есть факты — отдаём их
            if rag_text:
                return "Вот что есть в базе:\n\n" + rag_text
            return "Простите, я задумался над вашим вопросом. Попробуйте переформулировать."

    async def compare_authors(self, narrator_author_key: str, a1: str, a2: str) -> str:
        """
        Сравнение авторов в структурированном виде.
        narrator_author_key — стиль ответа (кто “говорит”)
        a1, a2 — сравниваемые авторы
        """
        card1 = get_author_card(a1)
        card2 = get_author_card(a2)

        if not card1 or not card2:
            return "Не могу сравнить — не нашёл одного из авторов в базе."

        facts1 = format_compare_facts(card1)
        facts2 = format_compare_facts(card2)

        if not self.client:
            # fallback без ИИ — тоже норм
            return (
                f"🆚 {card1['full_name']} vs {card2['full_name']}\n\n"
                f"— {card1['full_name']}:\n{facts1}\n\n"
                f"— {card2['full_name']}:\n{facts2}"
            )

        style = self._author_style_prompt(narrator_author_key)
        system_prompt = (
            style
            + "\n\nТвоя задача: сравнить двух авторов СТРОГО по фактам."
            + "\nЗапрещено придумывать даты/произведения."
            + "\nФормат ответа:"
            + "\n🆚 <Автор1> vs <Автор2>"
            + "\n\n📌 Эпоха/контекст (если есть в фактах)"
            + "\n📚 Произведения (главное)"
            + "\n🧠 Темы/мировоззрение"
            + "\n✍️ Манера/стиль"
            + "\n✅ 3 кратких вывода"
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
        except Exception as e:
            print(f"❌ Ошибка сравнения: {e}")
            return (
                f"🆚 {card1['full_name']} vs {card2['full_name']}\n\n"
                f"— {card1['full_name']}:\n{facts1}\n\n"
                f"— {card2['full_name']}:\n{facts2}"
            )


gigachat_client = GigaChatClient(GIGACHAT_CREDENTIALS)
