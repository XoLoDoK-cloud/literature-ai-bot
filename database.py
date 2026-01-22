# database.py
import os
import json
import time
import hashlib
import aiosqlite
from typing import Optional, Any


def _now_ts() -> int:
    return int(time.time())


class Database:
    def __init__(self, db_path: str = "data/bot.db", legacy_dir: str = "data"):
        self.db_path = db_path
        self.legacy_dir = legacy_dir
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    async def init(self) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("PRAGMA journal_mode=WAL;")
            await conn.execute("PRAGMA foreign_keys=ON;")

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    selected_author TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    author_key TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('user','assistant')),
                    content TEXT NOT NULL,
                    ts INTEGER NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_user_ts
                ON messages(user_id, ts)
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    user_id INTEGER PRIMARY KEY,
                    total_user_messages INTEGER NOT NULL DEFAULT 0,
                    total_assistant_messages INTEGER NOT NULL DEFAULT 0,
                    total_dialog_resets INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS author_usage (
                    user_id INTEGER NOT NULL,
                    author_key TEXT NOT NULL,
                    user_messages INTEGER NOT NULL DEFAULT 0,
                    assistant_messages INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(user_id, author_key),
                    FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS response_cache (
                    cache_key TEXT PRIMARY KEY,
                    author_key TEXT NOT NULL,
                    user_text_hash TEXT NOT NULL,
                    response TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL
                )
            """)

            await conn.commit()

        await self._migrate_legacy_json()

    async def ensure_user(self, user_id: int) -> None:
        now = _now_ts()
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
            row = await cur.fetchone()
            if not row:
                await conn.execute(
                    "INSERT INTO users(user_id, selected_author, created_at, updated_at) VALUES(?,?,?,?)",
                    (user_id, None, now, now),
                )
                await conn.execute(
                    "INSERT OR IGNORE INTO stats(user_id, total_user_messages, total_assistant_messages, total_dialog_resets, updated_at) VALUES(?,?,?,?,?)",
                    (user_id, 0, 0, 0, now),
                )
            else:
                await conn.execute("UPDATE users SET updated_at=? WHERE user_id=?", (now, user_id))
            await conn.commit()

    async def get_selected_author(self, user_id: int) -> Optional[str]:
        await self.ensure_user(user_id)
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute("SELECT selected_author FROM users WHERE user_id=?", (user_id,))
            row = await cur.fetchone()
            return row[0] if row and row[0] else None

    async def set_selected_author(self, user_id: int, author_key: Optional[str]) -> None:
        await self.ensure_user(user_id)
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "UPDATE users SET selected_author=?, updated_at=? WHERE user_id=?",
                (author_key, _now_ts(), user_id),
            )
            await conn.commit()

    async def reset_dialog(self, user_id: int) -> None:
        await self.ensure_user(user_id)
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("DELETE FROM messages WHERE user_id=?", (user_id,))
            await conn.execute(
                "UPDATE stats SET total_dialog_resets = total_dialog_resets + 1, updated_at=? WHERE user_id=?",
                (_now_ts(), user_id),
            )
            await conn.commit()

    async def add_message(self, user_id: int, author_key: str, role: str, content: str) -> None:
        await self.ensure_user(user_id)
        ts = _now_ts()
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "INSERT INTO messages(user_id, author_key, role, content, ts) VALUES(?,?,?,?,?)",
                (user_id, author_key, role, content, ts),
            )

            if role == "user":
                await conn.execute(
                    "UPDATE stats SET total_user_messages = total_user_messages + 1, updated_at=? WHERE user_id=?",
                    (ts, user_id),
                )
                await conn.execute("""
                    INSERT INTO author_usage(user_id, author_key, user_messages, assistant_messages)
                    VALUES(?,?,1,0)
                    ON CONFLICT(user_id, author_key) DO UPDATE SET user_messages = user_messages + 1
                """, (user_id, author_key))
            else:
                await conn.execute(
                    "UPDATE stats SET total_assistant_messages = total_assistant_messages + 1, updated_at=? WHERE user_id=?",
                    (ts, user_id),
                )
                await conn.execute("""
                    INSERT INTO author_usage(user_id, author_key, user_messages, assistant_messages)
                    VALUES(?,?,0,1)
                    ON CONFLICT(user_id, author_key) DO UPDATE SET assistant_messages = assistant_messages + 1
                """, (user_id, author_key))

            await conn.commit()

    async def get_conversation_history(self, user_id: int, limit_pairs: int = 4) -> list[dict]:
        await self.ensure_user(user_id)
        limit = max(2, limit_pairs * 2)
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                "SELECT role, content FROM messages WHERE user_id=? ORDER BY ts DESC, id DESC LIMIT ?",
                (user_id, limit),
            )
            rows = await cur.fetchall()

        rows.reverse()
        return [{"role": r[0], "content": r[1]} for r in rows]

    async def get_stats(self, user_id: int) -> dict[str, Any]:
        await self.ensure_user(user_id)
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute("""
                SELECT total_user_messages, total_assistant_messages, total_dialog_resets
                FROM stats WHERE user_id=?
            """, (user_id,))
            row = await cur.fetchone()

            cur2 = await conn.execute("""
                SELECT author_key, (user_messages + assistant_messages) AS total
                FROM author_usage WHERE user_id=?
                ORDER BY total DESC
                LIMIT 1
            """, (user_id,))
            fav = await cur2.fetchone()

            cur3 = await conn.execute("SELECT selected_author FROM users WHERE user_id=?", (user_id,))
            last = await cur3.fetchone()

        return {
            "total_user_messages": row[0] if row else 0,
            "total_assistant_messages": row[1] if row else 0,
            "total_dialog_resets": row[2] if row else 0,
            "favorite_author": fav[0] if fav else None,
            "selected_author": last[0] if last and last[0] else None,
        }

    # ---------------- CACHE ----------------

    @staticmethod
    def _hash_text(text: str) -> str:
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    @staticmethod
    def _make_cache_key(author_key: str, system_prompt: str, knowledge_hint: str, user_text: str) -> str:
        blob = f"{author_key}\n{system_prompt}\n{knowledge_hint}\n{user_text.strip()}"
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    async def cache_get(self, cache_key: str) -> Optional[str]:
        now = _now_ts()
        async with aiosqlite.connect(self.db_path) as conn:
            cur = await conn.execute(
                "SELECT response, expires_at FROM response_cache WHERE cache_key=?",
                (cache_key,),
            )
            row = await cur.fetchone()
            if not row:
                return None
            response, expires_at = row
            if expires_at <= now:
                await conn.execute("DELETE FROM response_cache WHERE cache_key=?", (cache_key,))
                await conn.commit()
                return None
            return response

    async def cache_set(
        self,
        cache_key: str,
        author_key: str,
        user_text_hash: str,
        response: str,
        ttl_seconds: int = 3600,
    ) -> None:
        now = _now_ts()
        expires_at = now + max(30, int(ttl_seconds))
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT INTO response_cache(cache_key, author_key, user_text_hash, response, created_at, expires_at)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    response=excluded.response,
                    created_at=excluded.created_at,
                    expires_at=excluded.expires_at
            """, (cache_key, author_key, user_text_hash, response, now, expires_at))
            await conn.commit()

    async def cache_cleanup(self) -> None:
        now = _now_ts()
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("DELETE FROM response_cache WHERE expires_at <= ?", (now,))
            await conn.commit()

    async def _migrate_legacy_json(self) -> None:
        # перенос старых data/*.json если они были
        if not os.path.isdir(self.legacy_dir):
            return
        for fname in os.listdir(self.legacy_dir):
            if not fname.endswith(".json"):
                continue
            path = os.path.join(self.legacy_dir, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    payload = json.load(f)
            except Exception:
                continue

            try:
                user_id = int(os.path.splitext(fname)[0])
            except Exception:
                continue

            await self.ensure_user(user_id)

            sel = payload.get("selected_author")
            if sel:
                await self.set_selected_author(user_id, sel)

            history = payload.get("conversation_history") or []
            for msg in history:
                role = msg.get("role")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    author_key = sel or "pushkin"
                    await self.add_message(user_id, author_key, role, content)

            try:
                os.rename(path, path + ".migrated")
            except Exception:
                pass


db = Database()
