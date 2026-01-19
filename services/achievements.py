import json
import os
from typing import Dict, List
from datetime import datetime

class AchievementsService:
    """Сервис достижений"""
    
    def __init__(self, achievements_file: str = "data/achievements.json"):
        self.achievements_file = achievements_file
        self.achievements = self._load_achievements()
    
    def _load_achievements(self) -> List[Dict]:
        """Загружает достижения"""
        if not os.path.exists(self.achievements_file):
            return self._get_default_achievements()
        
        try:
            with open(self.achievements_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return self._get_default_achievements()
    
    def _get_default_achievements(self) -> List[Dict]:
        """Возвращает стандартные достижения"""
        return [
            {
                "id": "first_message",
                "name": "🎯 Первый шаг",
                "description": "Отправить первое сообщение",
                "condition": {"type": "message_count", "value": 1},
                "emoji": "🎯"
            },
            {
                "id": "chat_master",
                "name": "💬 Мастер диалога",
                "description": "Отправить 50 сообщений",
                "condition": {"type": "message_count", "value": 50},
                "emoji": "💬"
            },
            {
                "id": "author_explorer",
                "name": "👑 Исследователь классики",
                "description": "Побеседовать с 3 разными авторами",
                "condition": {"type": "different_authors", "value": 3},
                "emoji": "👑"
            },
            {
                "id": "gigachad_fan",
                "name": "💪 Фанат Гигачада",
                "description": "Активировать режим Гигачад 10 раз",
                "condition": {"type": "gigachad_activations", "value": 10},
                "emoji": "💪"
            },
            {
                "id": "what_if_expert",
                "name": "🎭 Эксперт 'Что если'",
                "description": "Задать 5 вопросов в режиме 'Что если'",
                "condition": {"type": "what_if_questions", "value": 5},
                "emoji": "🎭"
            },
            {
                "id": "writing_partner",
                "name": "✍️ Соавтор классика",
                "description": "Написать совместный текст с автором",
                "condition": {"type": "writing_sessions", "value": 1},
                "emoji": "✍️"
            },
            {
                "id": "bookworm",
                "name": "📚 Книжный червь",
                "description": "Получить 10 рекомендаций книг",
                "condition": {"type": "book_recommendations", "value": 10},
                "emoji": "📚"
            },
            {
                "id": "timeline_expert",
                "name": "📅 Знаток биографий",
                "description": "Изучить все таймлайны авторов",
                "condition": {"type": "timelines_viewed", "value": 5},
                "emoji": "📅"
            },
            {
                "id": "week_streak",
                "name": "🔥 Неделя подряд",
                "description": "Активность 7 дней подряд",
                "condition": {"type": "streak_days", "value": 7},
                "emoji": "🔥"
            }
        ]
    
    def check_new_achievements(self, user_id: int, user_data: Dict) -> List[Dict]:
        """Проверяет и возвращает новые достижения"""
        current_achievements = user_data.get("achievements", [])
        new_achievements = []
        
        for achievement in self.achievements:
            if achievement["id"] in current_achievements:
                continue
            
            if self._check_condition(achievement["condition"], user_data):
                new_achievements.append(achievement)
                current_achievements.append(achievement["id"])
        
        # Обновляем достижения пользователя
        user_data["achievements"] = current_achievements
        
        return new_achievements
    
    def _check_condition(self, condition: Dict, user_data: Dict) -> bool:
        """Проверяет условие достижения"""
        cond_type = condition["type"]
        required_value = condition["value"]
        
        if cond_type == "message_count":
            current_value = user_data.get("message_count", 0)
            return current_value >= required_value
        
        elif cond_type == "different_authors":
            # Считаем уникальных авторов из истории
            authors = set()
            for msg in user_data.get("conversation_history", []):
                if msg.get("role") == "assistant":
                    # Извлекаем автора из сообщения (упрощённо)
                    text = msg.get("content", "").lower()
                    if any(name in text for name in ["пушкин", "александр"]):
                        authors.add("pushkin")
                    elif any(name in text for name in ["достоевск", "фёдор"]):
                        authors.add("dostoevsky")
                    elif any(name in text for name in ["толст", "лев"]):
                        authors.add("tolstoy")
                    elif any(name in text for name in ["гогол", "николай"]):
                        authors.add("gogol")
                    elif any(name in text for name in ["чехов", "антон"]):
                        authors.add("chekhov")
                    elif any(name in text for name in ["гигачад", "gigachad"]):
                        authors.add("gigachad")
            
            return len(authors) >= required_value
        
        elif cond_type == "gigachad_activations":
            # Упрощённо: считаем сообщения в режиме Гигачад
            gigachad_messages = 0
            for msg in user_data.get("conversation_history", []):
                if msg.get("role") == "user" and "гигачад" in msg.get("content", "").lower():
                    gigachad_messages += 1
            
            return gigachad_messages >= required_value
        
        elif cond_type == "streak_days":
            # Простая проверка streak
            last_active = user_data.get("last_active")
            if not last_active:
                return False
            
            # Здесь должна быть логика подсчёта дней подряд
            # Упрощённо: считаем что streak есть если есть активность
            return user_data.get("message_count", 0) > 0
        
        # Для других типов условий
        return False
    
    def format_achievements(self, user_data: Dict) -> str:
        """Форматирует список достижений"""
        user_achievement_ids = user_data.get("achievements", [])
        total_achievements = len(self.achievements)
        unlocked = len(user_achievement_ids)
        
        achievements_text = f"""
🏆 <b>ВАШИ ДОСТИЖЕНИЯ</b>
{'═' * 40}

📊 <b>Прогресс:</b> {unlocked}/{total_achievements} ({unlocked/total_achievements*100:.0f}%)

{'═' * 40}
"""
        
        if unlocked == 0:
            achievements_text += "\n🎯 <b>Достижений пока нет!</b>\n"
            achievements_text += "<i>Активно общайтесь с авторами, чтобы получить достижения</i>\n"
        
        else:
            achievements_text += "\n<b>🎖️ РАЗБЛОКИРОВАННЫЕ:</b>\n\n"
            
            for achievement in self.achievements:
                if achievement["id"] in user_achievement_ids:
                    achievements_text += f"{achievement['emoji']} <b>{achievement['name']}</b>\n"
                    achievements_text += f"<i>{achievement['description']}</i>\n\n"
        
        # Показываем ближайшие к получению
        next_achievements = []
        for achievement in self.achievements:
            if achievement["id"] not in user_achievement_ids:
                next_achievements.append(achievement)
                if len(next_achievements) >= 3:
                    break
        
        if next_achievements:
            achievements_text += "🎯 <b>БЛИЖАЙШИЕ ЦЕЛИ:</b>\n\n"
            for achievement in next_achievements:
                achievements_text += f"{achievement['emoji']} {achievement['name']}\n"
                achievements_text += f"<i>{achievement['description']}</i>\n\n"
        
        achievements_text += f"{'═' * 40}\n"
        achievements_text += "<code>🎮 Продолжайте общение для новых достижений!</code>"
        
        return achievements_text

# Глобальный экземпляр
achievements_service = AchievementsService()
