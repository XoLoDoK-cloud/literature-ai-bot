# knowledge_base.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class KBItem:
    author_key: str
    text: str
    tags: List[str]


# =========================
# База фактов (минимально + Филатов подробно)
# =========================

AUTHOR_CARDS: Dict[str, Dict[str, Any]] = {
    "filatov": {
        "full_name": "Леонид Алексеевич Филатов",
        "years": "1946–2003",
        "about": [
            "Советский и российский актёр, режиссёр, поэт, драматург и публицист.",
            "Широко известен сатирической поэмой «Про Федота-стрельца, удалого молодца».",
            "Работал в театре и кино, выступал как автор и ведущий проектов.",
        ],
        "key_works": [
            "«Про Федота-стрельца, удалого молодца» (сатирическая поэма)",
            "Публицистические и авторские выступления (в т.ч. телевизионные проекты, связанные с литературой и культурой)",
        ],
        "themes": [
            "сатира и социальная ирония",
            "ценность слова и ответственности",
            "честность и достоинство",
        ],
        "style": [
            "театральная интонация без клоунады",
            "меткость формулировок",
            "умная ирония",
        ],
    },

    # Несколько базовых карточек для сравнения/фактов (можно расширять)
    "pushkin": {"full_name": "Александр Сергеевич Пушкин", "years": "1799–1837"},
    "lermontov": {"full_name": "Михаил Юрьевич Лермонтов", "years": "1814–1841"},
    "gogol": {"full_name": "Николай Васильевич Гоголь", "years": "1809–1852"},
    "tolstoy": {"full_name": "Лев Николаевич Толстой", "years": "1828–1910"},
    "dostoevsky": {"full_name": "Фёдор Михайлович Достоевский", "years": "1821–1881"},
    "chekhov": {"full_name": "Антон Павлович Чехов", "years": "1860–1904"},
    "akhmatova": {"full_name": "Анна Андреевна Ахматова", "years": "1889–1966"},
    "esenin": {"full_name": "Сергей Александрович Есенин", "years": "1895–1925"},
    "mayakovsky": {"full_name": "Владимир Владимирович Маяковский", "years": "1893–1930"},
    "blokk": {"full_name": "Александр Александрович Блок", "years": "1880–1921"},
    "bulgakov": {"full_name": "Михаил Афанасьевич Булгаков", "years": "1891–1940"},
    "brodsky": {"full_name": "Иосиф Александрович Бродский", "years": "1940–1996"},
}


KB: List[KBItem] = [
    KBItem(
        author_key="filatov",
        tags=["биография", "кто такой", "факты", "жизнь"],
        text=(
            "Леонид Алексеевич Филатов (1946–2003) — актёр, режиссёр, поэт, драматург и публицист. "
            "Известен сочетанием театральной выразительности и точной сатиры."
        ),
    ),
    KBItem(
        author_key="filatov",
        tags=["произведения", "что написал", "федот", "главное"],
        text=(
            "Одно из самых известных произведений Филатова — сатирическая поэма "
            "«Про Федота-стрельца, удалого молодца». "
            "Её часто ценят за иронию, живой язык и социальные намёки."
        ),
    ),
    KBItem(
        author_key="filatov",
        tags=["стиль", "манера", "как говорит", "ирония", "сатира"],
        text=(
            "Манера Филатова: умная ирония без грубости, точные формулировки, чувство меры. "
            "Даже в сатире у него слышна ответственность за слово."
        ),
    ),
    KBItem(
        author_key="filatov",
        tags=["темы", "смысл", "о чем", "позиция"],
        text=(
            "Филатову близки темы честности, внутреннего достоинства, цены слова, "
            "а также сатирический взгляд на общественные привычки и власть языка."
        ),
    ),
]


def rag_search(author_key: str, query: str, limit: int = 7) -> List[str]:
    """
    Простая RAG-поисковая функция:
    - ищем совпадения по словам запроса в KBItem.text и KBItem.tags
    - возвращаем топ-N фрагментов
    """
    q = (query or "").lower().strip()
    if not q:
        return []

    words = [w for w in q.replace("?", " ").replace("!", " ").replace(",", " ").split() if len(w) >= 3]

    scored = []
    for item in KB:
        if item.author_key != author_key:
            continue
        text_l = item.text.lower()
        tags_l = " ".join(item.tags).lower()

        score = 0
        for w in words:
            if w in text_l:
                score += 2
            if w in tags_l:
                score += 3

        if score > 0:
            scored.append((score, item.text))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[:limit]]


def format_rag_blocks(blocks: List[str]) -> str:
    if not blocks:
        return ""
    return "\n\n".join(f"• {b}" for b in blocks)


def get_author_card(author_key: str) -> Dict[str, Any] | None:
    return AUTHOR_CARDS.get(author_key)


def format_compare_facts(card: Dict[str, Any]) -> str:
    """
    Превращаем карточку в текст фактов для compare_authors
    """
    if not card:
        return ""

    lines = []
    full_name = card.get("full_name")
    years = card.get("years")
    if full_name:
        lines.append(f"Имя: {full_name}")
    if years:
        lines.append(f"Годы: {years}")

    for k in ("about", "key_works", "themes", "style"):
        v = card.get(k)
        if isinstance(v, list) and v:
            title = {
                "about": "Кратко",
                "key_works": "Известен по",
                "themes": "Темы",
                "style": "Стиль",
            }.get(k, k)
            lines.append(f"{title}: " + "; ".join(v))

    return "\n".join(lines)
