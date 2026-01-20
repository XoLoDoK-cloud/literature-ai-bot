import json
import os
from datetime import datetime

class SimpleDatabase:
    """Простая база данных на JSON файлах"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _get_user_file(self, user_id: int) -> str:
        return os.path.join(self.data_dir, f"user_{user_id}.json")
    
    def get_user_data(self, user_id: int) -> dict:
        """Получить данные пользователя"""
        file_path = self._get_user_file(user_id)
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Создаем новые данные
        return {
            "user_id": user_id,
            "selected_author": None,
            "conversation_history": [],
            "message_count": 0,
            "created_at": datetime.now().isoformat()
        }
    
    def save_user_data(self, user_id: int, data: dict):
        """Сохранить данные пользователя"""
        data["updated_at"] = datetime.now().isoformat()
        file_path = self._get_user_file(user_id)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
    
    def update_conversation(self, user_id: int, author_key: str, user_message: str, bot_response: str):
        """Обновить историю диалога"""
        data = self.get_user_data(user_id)
        
        # Добавляем сообщения
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
        
        # Обновляем автора и счетчик
        data["selected_author"] = author_key
        data["message_count"] = len(data["conversation_history"]) // 2
        
        # Ограничиваем историю (последние 20 сообщений)
        if len(data["conversation_history"]) > 20:
            data["conversation_history"] = data["conversation_history"][-20:]
        
        self.save_user_data(user_id, data)
    
    def reset_conversation(self, user_id: int):
        """Сбросить диалог"""
        data = self.get_user_data(user_id)
        data["conversation_history"] = []
        data["message_count"] = 0
        self.save_user_data(user_id, data)

# Глобальный экземпляр
db = SimpleDatabase()
