# rate_limit.py
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional

from aiogram import BaseMiddleware
from aiogram.types import Message


@dataclass
class RateLimitConfig:
    # общий лимит
    max_messages: int = 6
    per_seconds: int = 10

    # наказание
    cooldown_seconds: int = 12

    # отдельный лимит на "тяжёлые" сообщения (ИИ)
    max_ai_messages: int = 3
    ai_per_seconds: int = 20


class InMemoryRateLimiter:
    def __init__(self, cfg: RateLimitConfig):
        self.cfg = cfg
        self._bucket: Dict[int, Deque[float]] = {}
        self._bucket_ai: Dict[int, Deque[float]] = {}
        self._cooldown_until: Dict[int, float] = {}

    def _now(self) -> float:
        return time.time()

    def _get_deque(self, store: Dict[int, Deque[float]], user_id: int) -> Deque[float]:
        if user_id not in store:
            store[user_id] = deque()
        return store[user_id]

    @staticmethod
    def _prune(q: Deque[float], window: int, now: float) -> None:
        while q and (now - q[0]) > window:
            q.popleft()

    def check(self, user_id: int, is_ai: bool) -> Optional[int]:
        now = self._now()

        cd = self._cooldown_until.get(user_id)
        if cd and now < cd:
            return int(cd - now) + 1

        q = self._get_deque(self._bucket, user_id)
        self._prune(q, self.cfg.per_seconds, now)
        if len(q) >= self.cfg.max_messages:
            self._cooldown_until[user_id] = now + self.cfg.cooldown_seconds
            return self.cfg.cooldown_seconds

        if is_ai:
            qa = self._get_deque(self._bucket_ai, user_id)
            self._prune(qa, self.cfg.ai_per_seconds, now)
            if len(qa) >= self.cfg.max_ai_messages:
                self._cooldown_until[user_id] = now + self.cfg.cooldown_seconds
                return self.cfg.cooldown_seconds

        q.append(now)
        if is_ai:
            self._get_deque(self._bucket_ai, user_id).append(now)

        return None


class AntiFloodMiddleware(BaseMiddleware):
    """
    Антифлуд: режет слишком частые сообщения.
    is_ai определяется эвристикой: длинное/творческое/объяснялки => тяжелее.
    """
    def __init__(self, limiter: InMemoryRateLimiter):
        super().__init__()
        self.limiter = limiter

    @staticmethod
    def _looks_ai_heavy(text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False

        fact_words = ("когда", "где", "кто", "сколько", "дата", "год", "умер", "умерла", "родился", "родилась")
        if len(t) <= 40 and any(w in t for w in fact_words):
            return False

        creative = ("стих", "рассказ", "эссе", "в стиле", "перепиши", "продолжи", "придумай", "поясни", "объясни")
        if any(w in t for w in creative):
            return True

        return len(t) > 120

    async def __call__(self, handler, event, data):
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            is_ai = self._looks_ai_heavy(event.text or "")
            wait = self.limiter.check(user_id, is_ai=is_ai)
            if wait is not None:
                await event.answer(f"⏳ Слишком часто. Подожди ~{wait} сек и попробуй снова.")
                return
        return await handler(event, data)
