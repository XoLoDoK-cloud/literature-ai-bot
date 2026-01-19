import os
import json
from typing import Dict, List
from datetime import datetime, timedelta

class Statistics:
    """Сервис статистики с графиками ASCII"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
    
    def _get_progress_bar(self, percentage: float, length: int = 10) -> str:
        """Создает прогресс-бар ASCII"""
        filled = int(percentage * length / 100)
        bar = "█" * filled + "░" * (length - filled)
        return f"{bar} {percentage:.0f}%"
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Получает статистику пользователя"""
        user_file = os.path.join(self.data_dir, f"user_{user_id}.json")
        
        if not os.path.exists(user_file):
            return {
                "total_messages": 0,
                "authors": {},
                "streak_days": 0,
                "level": 1
            }
        
        with open(user_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Анализируем историю сообщений
        author_counts = {}
        total_messages = data.get("message_count", 0)
        
        for msg in data.get("conversation_history", []):
            if msg["role"] == "user":
                author = data.get("selected_author", "unknown")
                author_counts[author] = author_counts.get(author, 0) + 1
        
        # Считаем streak (дни подряд)
        streak_days = self._calculate_streak(data.get("message_dates", []))
        
        return {
            "total_messages": total_messages,
            "authors": author_counts,
            "streak_days": streak_days,
            "level": min(total_messages // 10 + 1, 50)  # Уровень
        }
    
    def _calculate_streak(self, message_dates: List[str]) -> int:
        """Считает дни подряд активности"""
        if not message_dates:
            return 0
        
        dates = sorted([datetime.fromisoformat(d) for d in message_dates])
        streak = 1
        current_date = dates[-1].date()
        
        for i in range(len(dates)-2, -1, -1):
            prev_date = dates[i].date()
            if (current_date - prev_date).days == 1:
                streak += 1
                current_date = prev_date
            elif (current_date - prev_date).days > 1:
                break
        
        return streak
    
    def format_user_stats(self, user_id: int, username: str = "Читатель") -> str:
        """Форматирует статистику с графиками"""
        stats = self.get_user_stats(user_id)
        
        # Уровень с прогрессом
        level_progress = (stats["total_messages"] % 10) * 10
        
        stats_text = f"""
🏆 <b>ЛИЧНАЯ СТАТИСТИКА</b>
<code>{'═' * 35}</code>

👤 <b>Читатель:</b> {username}
⭐ <b>Уровень:</b> {stats['level']} ({self._get_progress_bar(level_progress)})
📅 <b>Дней подряд:</b> {stats['streak_days']} 🔥

💬 <b>Всего сообщений:</b> {stats['total_messages']}
<code>{'═' * 35}</code>

📊 <b>АКТИВНОСТЬ ПО АВТОРАМ:</b>
"""
        
        # Сортируем авторов по популярности
        sorted_authors = sorted(
            stats["authors"].items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        author_names = {
            "pushkin": "🖋️ Пушкин",
            "dostoevsky": "📚 Достоевский",
            "tolstoy": "✍️ Толстой",
            "gogol": "👻 Гоголь",
            "gigachad": "💪 ГИГАЧАД"
        }
        
        for author_key, count in sorted_authors[:5]:  # Топ-5
            author_name = author_names.get(author_key, author_key)
            percentage = (count / stats["total_messages"] * 100) if stats["total_messages"] > 0 else 0
            
            stats_text += f"\n{author_name}:"
            stats_text += f"\n{self._get_progress_bar(percentage)}"
            stats_text += f" ({count} сообщ.)\n"
        
        # Достижения
        stats_text += f"\n<code>{'═' * 35}</code>"
        stats_text += "\n🏅 <b>ДОСТИЖЕНИЯ:</b>\n"
        
        achievements = []
        if stats["total_messages"] >= 10:
            achievements.append("🎯 Начинающий литератор")
        if stats["total_messages"] >= 50:
            achievements.append("📚 Опытный читатель")
        if len(stats["authors"]) >= 3:
            achievements.append("👑 Знаток классики")
        if stats["streak_days"] >= 7:
            achievements.append("🔥 Неделя подряд")
        
        if achievements:
            for achievement in achievements:
                stats_text += f"• {achievement}\n"
        else:
            stats_text += "🎯 Продолжайте общение для получения достижений!\n"
        
        stats_text += f"\n<code>{'═' * 35}</code>"
        stats_text += "\n<code>📈 Продолжайте в том же духе!</code>"
        
        return stats_text

# Создаем глобальный экземпляр
stats_service = Statistics()
