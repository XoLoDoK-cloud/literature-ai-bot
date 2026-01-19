# ========== context_analyzer.py ==========
import re
from typing import Dict, List, Tuple
import random

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
            ],
            "саморазвитие": [
                "развитие", "улучшение", "рост", "становление", "прогресс",
                "дисциплина", "привычка", "мотивация", "цель", "успех",
                "провал", "опыт", "урок", "совет", "рекомендация"
            ],
            "история": [
                "история", "эпоха", "век", "время", "год", "событие",
                "революция", "война", "мир", "общество", "культура",
                "традиция", "обычай", "нрав", "быт", "уклад"
            ]
        }
        
        self.user_mood_indicators = {
            "любопытный": ["почему", "как", "что", "зачем", "интересно", "расскажи"],
            "философский": ["смысл", "жизнь", "смерть", "вечность", "существование"],
            "практичный": ["как", "совет", "рекомендация", "помощь", "практический"],
            "критический": ["почему", "но", "однако", "хотя", "спорный", "сомнение"],
            "эмоциональный": ["люблю", "ненавижу", "восхищаюсь", "разочарован", "чувствую"]
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
        mood_scores = {}
        for mood, indicators in self.user_mood_indicators.items():
            score = sum(1 for indicator in indicators if indicator in msg_lower)
            if score > 0:
                mood_scores[mood] = score
        
        if mood_scores:
            analysis["user_mood"] = max(mood_scores.items(), key=lambda x: x[1])[0]
        
        # Определяем тип вопроса
        question_words = ["почему", "как", "что", "зачем", "когда", "где", "кто"]
        if any(msg_lower.startswith(word) for word in question_words):
            analysis["question_type"] = "вопрос"
        elif "?" in message:
            analysis["question_type"] = "вопрос"
        elif any(word in msg_lower for word in ["расскажи", "поделись", "объясни"]):
            analysis["question_type"] = "просьба рассказать"
        
        # Определяем сложность
        word_count = len(message.split())
        if word_count < 5:
            analysis["complexity"] = "низкая"
        elif word_count > 15:
            analysis["complexity"] = "высокая"
        
        return analysis
    
    def generate_context_hints(self, analysis: Dict, author_name: str) -> str:
        """Генерирует подсказки для контекста на основе анализа"""
        hints = []
        
        # Подсказки по темам
        if "литература" in analysis["main_topics"]:
            hints.append(f"Упомяни конкретные произведения или литературные приёмы")
        
        if "философия" in analysis["main_topics"]:
            hints.append(f"Прояви философскую глубину, но сохраняй ясность")
        
        if "биография" in analysis["main_topics"]:
            hints.append(f"Расскажи о личном опыте или историческом контексте")
        
        # Подсказки по настроению
        if analysis["user_mood"] == "любопытный":
            hints.append(f"Будь подробным и объясняющим")
        elif analysis["user_mood"] == "философский":
            hints.append(f"Говори глубоко, но доступно")
        elif analysis["user_mood"] == "практичный":
            hints.append(f"Давай конкретные советы и примеры")
        
        # Подсказки по типу вопроса
        if analysis["question_type"] == "вопрос":
            hints.append(f"Ответь прямо на вопрос, но развернуто")
        elif analysis["question_type"] == "просьба рассказать":
            hints.append(f"Расскажи историю или приведи пример")
        
        # Подсказки по сложности
        if analysis["complexity"] == "низкая":
            hints.append(f"Будь простым и понятным")
        elif analysis["complexity"] == "высокая":
            hints.append(f"Прояви эрудицию и глубину мысли")
        
        if hints:
            return f"Рекомендации для ответа {author_name}: " + "; ".join(hints)
        return ""
    
    def extract_key_concepts(self, message: str) -> List[str]:
        """Извлекает ключевые концепции из сообщения"""
        # Упрощенный извлечение существительных и важных слов
        words = re.findall(r'\b[а-яё]{4,}\b', message.lower())
        
        # Фильтруем стоп-слова
        stop_words = {"этот", "очень", "просто", "такой", "свой", "весь", "какой"}
        concepts = [word for word in words if word not in stop_words]
        
        return concepts[:5]  # Возвращаем до 5 ключевых концепций

# Глобальный экземпляр
context_analyzer = ContextAnalyzer()
