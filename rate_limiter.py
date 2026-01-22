# rate_limiter.py
from __future__ import annotations
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Tuple


@dataclass
class LimitResult:
    ok: bool
    retry_after_sec: int = 0
    reason: str = ""


class RateLimiter:
    """
    In-memory антифлуд (для Render 1 инстанс — идеально).
    Два лимита: короткий и длинный.
    Отдельный cooldown для AI-вызовов.
    """
    def __init__(
        self,
        short_max: int,
        short_window_sec: int,
        long_max: int,
        long_window_sec: int,
        ai_cooldown_sec: int,
    ):
        self.short_max = max(1, short_max)
        self.short_window = max(1, short_window_sec)
        self.long_max = max(1, long_max)
        self.long_window = max(1, long_window_sec)
        self.ai_cooldown = max(0, ai_cooldown_sec)

        self._short: Dict[int, Deque[float]] = {}
        self._long: Dict[int, Deque[float]] = {}
        self._last_ai_ts: Dict[int, float] = {}

    def _cleanup(self, dq: Deque[float], window: int, now: float) -> None:
        cutoff = now - window
        while dq and dq[0] < cutoff:
            dq.popleft()

    def allow_message(self, user_id: int) -> LimitResult:
        now = time.time()

        dq_s = self._short.setdefault(user_id, deque())
        dq_l = self._long.setdefault(user_id, deque())

        self._cleanup(dq_s, self.short_window, now)
        self._cleanup(dq_l, self.long_window, now)

        if len(dq_s) >= self.short_max:
            retry = int((dq_s[0] + self.short_window) - now) + 1
            return LimitResult(False, max(1, retry), "short")
        if len(dq_l) >= self.long_max:
            retry = int((dq_l[0] + self.long_window) - now) + 1
            return LimitResult(False, max(5, retry), "long")

        dq_s.append(now)
        dq_l.append(now)
        return LimitResult(True)

    def allow_ai(self, user_id: int) -> LimitResult:
        if self.ai_cooldown <= 0:
            return LimitResult(True)

        now = time.time()
        last = self._last_ai_ts.get(user_id, 0.0)
        wait = (last + self.ai_cooldown) - now
        if wait > 0:
            return LimitResult(False, int(wait) + 1, "ai_cooldown")

        self._last_ai_ts[user_id] = now
        return LimitResult(True)
