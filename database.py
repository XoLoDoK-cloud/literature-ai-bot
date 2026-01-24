import json
import os
from datetime import datetime
from typing import Dict, Any, Optional


class Database:
    """
    Простая JSON-база (1 файл на пользователя).
    Подходит для Render (1 инстанс). Для масштаба лучше SQLite/Postgres.
    """

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def _get_user_file(self, user_id: int) -> str:
        return os.path.join(self.data_dir, f"user_{user_id}.json")

    def _default_user_data(self, user_id: int) -> Dict[str, Any]:
        return {
            "user_id": user_id,
            "selected_author": None,
            "conversation_history": [],
            "created_at": datetime.now().isoformat(),
            "stats": {
                "total_user_messages": 0,
                "total_bot_messages": 0,
                "dialog_resets": 0,
                "author_usage": {}  # {author_key: count}
            }
        }

    def get_user_data(self, user_id: int) -> Dict[str, Any]:
        file_path = self._get_user_file(user_id)

        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = self._default_user_data(user_id)
        else:
            data = self._default_user_data(user_id)

        # миграции/гарантии полей
        data.setdefault("user_id", user_id)
        data.setdefault("selected_author", None)
        data.setdefault("conversation_history", [])
        data.setdefault("created_at", datetime.now().isoformat())
        data.setdefault("stats", {})
        stats = data["stats"]
        stats.setdefault("total_user_messages", 0)
        stats.setdefault("total_bot_messages", 0)
        stats.setdefault("dialog_resets", 0)
        stats.setdefault("author_usage", {})

        return data

    def save_user_data(self, user_id: int, data: Dict[str, Any]) -> None:
        file_path = self._get_user_file(user_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def set_selected_author(self, user_id: int, author_key: Optional[str]) -> None:
        data = self.get_user_data(user_id)
        data["selected_author"] = author_key
        self.save_user_data(user_id, data)

    def record_user_message(self, user_id: int, author_key: str, user_message: str) -> None:
        data = self.get_user_data(user_id)
        data["stats"]["total_user_messages"] += 1
        usage = data["stats"]["author_usage"]
        usage[author_key] = int(usage.get(author_key, 0)) + 1

        data.setdefault("conversation_history", [])
        data["conversation_history"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })

        # ограничиваем историю (последние 12 сообщений)
        if len(data["conversation_history"]) > 12:
            data["conversation_history"] = data["conversation_history"][-12:]

        data["selected_author"] = author_key
        self.save_user_data(user_id, data)

    def record_bot_message(self, user_id: int, author_key: str, bot_response: str) -> None:
        data = self.get_user_data(user_id)
        data["stats"]["total_bot_messages"] += 1

        data.setdefault("conversation_history", [])
        data["conversation_history"].append({
            "role": "assistant",
            "content": bot_response,
            "timestamp": datetime.now().isoformat()
        })

        if len(data["conversation_history"]) > 12:
            data["conversation_history"] = data["conversation_history"][-12:]

        data["selected_author"] = author_key
        self.save_user_data(user_id, data)

    def reset_dialog(self, user_id: int, keep_author: bool = True) -> None:
        data = self.get_user_data(user_id)
        selected = data.get("selected_author") if keep_author else None
        data["conversation_history"] = []
        data["stats"]["dialog_resets"] += 1
        data["selected_author"] = selected
        self.save_user_data(user_id, data)

    def get_stats(self, user_id: int) -> Dict[str, Any]:
        data = self.get_user_data(user_id)
        stats = data.get("stats", {})
        usage = stats.get("author_usage", {}) or {}
        favorite_author = None
        if usage:
            favorite_author = max(usage.items(), key=lambda kv: kv[1])[0]

        return {
            "total_user_messages": int(stats.get("total_user_messages", 0)),
            "total_bot_messages": int(stats.get("total_bot_messages", 0)),
            "dialog_resets": int(stats.get("dialog_resets", 0)),
            "favorite_author": favorite_author,
            "selected_author": data.get("selected_author")
        }


db = Database()
