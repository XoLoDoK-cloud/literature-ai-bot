import json
import os
from datetime import datetime

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
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "user_id": user_id,
            "selected_author": None,
            "conversation_history": [],
            "created_at": datetime.now().isoformat()
        }
    
    def save_user_data(self, user_id: int, data: dict):
        file_path = self._get_user_file(user_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def update_conversation(self, user_id: int, author_key: str, user_message: str, bot_response: str):
        data = self.get_user_data(user_id)
        
        if "conversation_history" not in data:
            data["conversation_history"] = []
        
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
        
        # Ограничиваем историю (последние 10 сообщений)
        if len(data["conversation_history"]) > 10:
            data["conversation_history"] = data["conversation_history"][-10:]
        
        self.save_user_data(user_id, data)

db = Database()
