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

        # миграция из legacy JSON (если есть)
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
                "UPDATE stats SET total_dialog_resets =
