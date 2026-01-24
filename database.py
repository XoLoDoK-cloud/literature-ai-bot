import json
import os
from datetime import datetime
from typing import Optional, Dict, Any


class Database:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    def _get_user_file(self, user_id: int) -> str:
        return os.path.join(self.data_dir, f"user_{user_id}.json")

    def get_user_data(self, user_id: int) -> dict:
        file_path = self._get_user_file(user_id)

        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        else:
            data = {}

        # гарантируем поля
        data.setdefault("user_id", user_id)
        data.setdefault("selected_author", None)
        data.setdefault("conversation_history", [])
        data.setdefault("created_at", datetime.now().isoformat())

        # режимы/сравнение
        data.setdefault("mode", None)  # None | compare_first | compare_second
        data.setdefault("compare_first_author", None)

        return data

    def save_user_data(self, user_id: int, data: dict):
        file_path = self._get_user_file(user_id)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def update_conversation(self, user_id: int, author_key: str, user_message: str, bot_response: str):
        data = self.get_user_data(user_id)

        data.setdefault("conversation_history", [])
        data["conversation_history"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        data["conversation_history"].append({
            "role": "assistant",
            "content": bot_response,
            "timestamp": datetime.now().isoformat()
        })

        data["selected_author"] = author_key

        # ограничиваем историю (последние 10 сообщений)
        if len(data["conversation_history"]) > 10:
            data["conversation_history"] = data["conversation_history"][-10:]

        self.save_user_data(user_id, data)

    # ---------- compare state helpers ----------

    def set_mode(self, user_id: int, mode: Optional[str]) -> None:
        data = self.get_user_data(user_id)
        data["mode"] = mode
        self.save_user_data(user_id, data)

    def set_compare_first_author(self, user_id: int, author_key: Optional[str]) -> None:
        data = self.get_user_data(user_id)
        data["compare_first_author"] = author_key
        self.save_user_data(user_id, data)

    def reset_compare(self, user_id: int) -> None:
        data = self.get_user_data(user_id)
        data["mode"] = None
        data["compare_first_author"] = None
        self.save_user_data(user_id, data)


db = Database()
