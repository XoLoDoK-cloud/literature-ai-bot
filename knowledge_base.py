# knowledge_base.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List
import re


@dataclass
class KBItem:
    author_key: str
    text: str
    tags: List[str]


# =========================
# RAG-база (фрагменты по авторам)
# =========================

KB: List[KBItem] = [
    KBItem(
        author_key="filatov",
        tags=["биография", "кто такой", "жизнь", "актер", "режиссер", "драматург"],
        text=(
            "Леонид Алексеевич Филатов — актёр, режиссёр, поэт, драматург и публицист. "
            "Его часто вспоминают за сочетание сценической выразительности и точной иронии."
        ),
    ),
    KBItem(
        author_key="filatov",
        tags=["произведения", "что написал", "федот", "главное", "поэма"],
        text=(
            "Одно из самых известных произведений Филатова — сатирическая поэма "
            "«Про Федота-стрельца, удалого молодца»: ирония, живой язык, социальные намёки."
        ),
    ),
    KBItem(
        author_key="filatov",
        tags=["стиль", "манера", "ирония", "сатира", "речь", "язык"],
        text=(
            "Манера Филатова: умная ирония без грубости, точные формулировки и чувство меры. "
            "Даже в сатире слышна ответственность за слово."
        ),
    ),
    KBItem(
        author_key="filatov",
        tags=["темы", "смысл", "о чем", "позиция", "ценности"],
        text=(
            "Филатову близки темы честности, внутреннего достоинства и цены слова, "
            "а также сатирический взгляд на общественные привычки и власть языка."
        ),
    ),
]


_word_re = re.compile(r"[а-яёa-z0-9]+", re.IGNORECASE)


def _tokenize(text: str) -> List[str]:
    """
    Простая нормальная токенизация:
    - только буквы/цифры
    - слова длиной >= 3
    """
    if not text:
        return []
    tokens = _word_re.findall(text.lower())
    return [t for t in tokens if len(t) >= 3]


def rag_search(author_key: str, query: str, limit: int = 7) -> List[str]:
    """
    Простая RAG-поисковая функция:
    - ищем совпадения по токенам запроса в KBItem.text и KBItem.tags
    - возвращаем топ-N фрагментов
    """
    author_key = (author_key or "").strip()
    if not author_key:
        return []

    words = _tokenize(query)
    if not words:
        return []

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
    return [t for _, t in scored[: max(1, int(limit))]]


def format_rag_blocks(blocks: List[str], max_chars: int = 2200) -> str:
    """
    Форматирование подсказок для промпта:
    - буллеты
    - лимит длины, чтобы RAG не "забивал" ответ
    """
    if not blocks:
        return ""

    text = "\n\n".join(f"• {b.strip()}" for b in blocks if (b or "").strip()).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "…"
    return text
