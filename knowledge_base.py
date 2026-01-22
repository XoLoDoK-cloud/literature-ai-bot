# knowledge_base.py
"""
База знаний + RAG (поиск релевантных пасажей).
Без внешних библиотек: делаем BM25-подобный скоринг.
"""

from __future__ import annotations
import math
import re
from typing import Any, Dict, List, Tuple, Optional

# ---- ТВОЯ БАЗА ЗНАНИЙ (оставляем как есть, можно расширять) ----
# ВСТАВЬ СЮДА СВОЙ WRITERS_KNOWLEDGE, если он у тебя большой.
# Ниже — примерная структура; у тебя уже есть полный словарь.
from typing import cast

WRITERS_KNOWLEDGE: Dict[str, Dict[str, Any]] = {
    # ⚠️ Здесь должен быть твой полный словарь.
    # Оставь как в твоём текущем файле (из проекта).
}

# ------------------- базовые helper'ы -------------------
_WORD_RE = re.compile(r"[a-zа-яё0-9]+", re.IGNORECASE)

def _tokenize(text: str) -> List[str]:
    return _WORD_RE.findall(text.lower())

def get_writer_knowledge(author_key: str) -> Dict[str, Any]:
    return WRITERS_KNOWLEDGE.get(author_key, {})

# ------------------- flatten -> passages -------------------
def _flatten(obj: Any, prefix: str = "") -> List[str]:
    lines: List[str] = []
    if obj is None:
        return lines

    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}{k}".strip(".")
            if isinstance(v, (dict, list)):
                lines.extend(_flatten(v, prefix=p + "."))
            else:
                lines.append(f"{p}: {v}")
        return lines

    if isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{prefix}{i}".strip(".")
            if isinstance(v, (dict, list)):
                lines.extend(_flatten(v, prefix=p + "."))
            else:
                lines.append(f"{prefix.rstrip('.')}: {v}")
        return lines

    lines.append(f"{prefix.rstrip('.')}: {obj}")
    return lines

def build_passages(author_key: str, max_lines_per_passage: int = 3) -> List[str]:
    kb = get_writer_knowledge(author_key)
    if not kb:
        return []
    lines = _flatten(kb)
    passages: List[str] = []
    buf: List[str] = []
    for ln in lines:
        ln = str(ln).strip()
        if not ln:
            continue
        buf.append(ln)
        if len(buf) >= max_lines_per_passage:
            passages.append("\n".join(buf))
            buf = []
    if buf:
        passages.append("\n".join(buf))
    return passages

# ------------------- BM25-like index per author -------------------
class _BM25Index:
    def __init__(self, passages: List[str]):
        self.passages = passages
        self.docs = [ _tokenize(p) for p in passages ]
        self.N = len(self.docs)
        self.avgdl = (sum(len(d) for d in self.docs) / self.N) if self.N else 0.0
        self.df: Dict[str, int] = {}
        for d in self.docs:
            seen = set(d)
            for t in seen:
                self.df[t] = self.df.get(t, 0) + 1

    def idf(self, t: str) -> float:
        # классическая BM25 idf
        df = self.df.get(t, 0)
        if df == 0:
            return 0.0
        return math.log(1 + (self.N - df + 0.5) / (df + 0.5))

    def score(self, query_tokens: List[str], k1: float = 1.2, b: float = 0.75) -> List[Tuple[int, float]]:
        if not self.N:
            return []
        q = query_tokens
        scores: List[Tuple[int, float]] = []
        for i, d in enumerate(self.docs):
            dl = len(d) or 1
            tf: Dict[str, int] = {}
            for t in d:
                tf[t] = tf.get(t, 0) + 1

            s = 0.0
            for t in q:
                if t not in tf:
                    continue
                idf = self.idf(t)
                freq = tf[t]
                denom = freq + k1 * (1 - b + b * (dl / (self.avgdl or 1)))
                s += idf * (freq * (k1 + 1) / denom)
            if s > 0:
                scores.append((i, s))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

_INDEX_CACHE: Dict[str, _BM25Index] = {}

def retrieve_passages(author_key: str, query: str, top_k: int = 4) -> List[str]:
    passages = build_passages(author_key)
    if not passages:
        return []
    idx = _INDEX_CACHE.get(author_key)
    if not idx or idx.passages != passages:
        idx = _BM25Index(passages)
        _INDEX_CACHE[author_key] = idx

    qt = _tokenize(query)
    ranked = idx.score(qt)
    out: List[str] = []
    for i, _s in ranked[:max(1, top_k)]:
        out.append(passages[i])
    return out

# ------------------- “быстрые факты” -------------------
def is_fact_question(query: str) -> bool:
    q = query.lower().strip()
    # грубая эвристика, но работает для биографии/дат/мест
    fact_markers = [
        "когда", "в каком", "где", "сколько", "дата", "родился", "родилась",
        "умер", "умерла", "погиб", "погибла", "место", "год", "век",
        "кто такой", "что такое", "как зовут", "настоящее имя"
    ]
    if "?" in q:
        return any(m in q for m in fact_markers)
    # без вопроса — тоже может быть факт
    return any(m in q for m in fact_markers)

def fact_snippet(author_key: str, query: str) -> str:
    # для фактов берём более “жёсткий” поиск: топ-2 пасажа
    passages = retrieve_passages(author_key, query, top_k=2)
    return "\n\n".join(passages).strip()
