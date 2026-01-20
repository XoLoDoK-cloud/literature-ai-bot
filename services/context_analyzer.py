import re
import random
from typing import Dict, List, Tuple

class ContextAnalyzer:
    """Анализатор контекста для улучшения диалогов"""
    
    def __init__(self):
        self.topic_keywords = {
            "литература": [
                "книга", "роман", "повесть", "поэма", "стих", "проза", 
                "литератур", "чтение", "автор", "писатель", "произведение",
                "глава", "сюжет", "герой", "персонаж", "классика"
            ],
            "философия": [
                "смысл", "жизнь", "смерть", "вера", "бог", "душа", "мораль",
                "этика", "добро", "зло", "свобода", "воля", "судьба", "философ",
                "существование", "бытие", "истина", "мудрость", "разум"
            ],
            "биография": [
                "детство", "юность", "родился", "учился", "жил", "работал",
                "путешествовал", "женился", "умер", "современник", "эпоха",
                "друг", "враг", "влияние", "наследие", "память"
            ],
            "творчество": [
                "писал", "творил", "создал", "вдохновение", "идея", "замысел",
                "работа", "рукопись", "издание", "публикация", "критика",
                "успех", "провал", "цензура", "запрет", "признание"
            ]
        }
    
    def analyze_user_message(self, message: str) -> Dict:
        """Анализирует сообщение пользователя"""
        analysis = {
            "main_topics": [],
            "user_mood": "нейтральный",
            "question_type": "общий",
            "complexity": "средняя"
        }
        
        msg_lower = message.lower()
        
        # Определяем основные темы
        for topic, keywords in self.topic_keywords.items():
            if any(keyword in msg_lower for keyword in keywords):
                analysis["main_topics"].append(topic)
        
        # Определяем настроение пользователя
        if any(word in msg_lower for word in ["почему", "как", "что", "зачем"]):
            analysis["user_mood"] = "любопытный"
        elif any(word in msg_lower for word in ["грустно", "печаль", "тоска"]):
            analysis["user_mood"] = "грустный"
        elif any(word in msg_lower for word in ["рад", "счастье", "восторг"]):
            analysis["user_mood"] = "радостный"
        
        # Определяем тип
        if any(msg_lower.startswith(word) for word in ["почему", "как", "что", "зачем"]):
            analysis["question_type"] = "вопрос"
        elif "?" in message:
            analysis["question_type"] = "вопрос"
        
        # Определяем сложность
        word_count = len(message.split())
        if word_count < 5:
            analysis["complexity"] = "низкая"
        elif word_count > 15:
            analysis["complexity"] = "высокая"
        
        return analysis
    
    def generate_context_hints(self, analysis: Dict, author_name: str) -> str:
        """Генерирует подсказки для контекста"""
        hints = []
        
        if "литература" in analysis["main_topics"]:
            hints.append("Упомяни литературные произведения")
        
        if "философия" in analysis["main_topics"]:
            hints.append("Прояви философскую глубину")
        
        if analysis["user_mood"] == "любопытный":
            hints.append("Будь подробным и объясняющим")
        elif analysis["user_mood"] == "грустный":
            hints.append("Прояви сочувствие и понимание")
        
        return f"Контекст: {', '.join(hints)}" if hints else ""

# Глобальный экземпляр
context_analyzer = ContextAnalyzer()
