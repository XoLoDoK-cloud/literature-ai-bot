import json
import os
import random
from datetime import datetime
from typing import Dict, List

class DailyQuotes:
    """Сервис ежедневных цитат с красивым оформлением"""
    
    def __init__(self, quotes_file: str = "data/quotes.json"):
        self.quotes_file = quotes_file
        self._ensure_quotes_file()
        self.quotes = self._load_quotes()
        
        # Стили оформления цитат
        self.quote_styles = [
            "✨ {} ✨",
            "💫 {} 💫",
            "🌟 {} 🌟",
            "💎 {} 💎",
            "🎭 {} 🎭",
            "📖 {} 📖"
        ]
    
    def _ensure_quotes_file(self):
        """Создает файл с цитатами если его нет"""
        if not os.path.exists(self.quotes_file):
            os.makedirs(os.path.dirname(self.quotes_file), exist_ok=True)
            
            beautiful_quotes = {
                "pushkin": [
                    {
                        "text": "Я вас любил: любовь еще, быть может, В душе моей угасла не совсем; Но пусть она вас больше не тревожит; Я не хочу печалить вас ничем.",
                        "work": "Я вас любил",
                        "year": 1829,
                        "emoji": "💖",
                        "theme": "любовь"
                    },
                    {
                        "text": "Мороз и солнце; день чудесный! Ещё ты дремлешь, друг прелестный — Пора, красавица, проснись.",
                        "work": "Зимнее утро",
                        "year": 1829,
                        "emoji": "☀️",
                        "theme": "природа"
                    }
                ],
                "dostoevsky": [
                    {
                        "text": "Красота спасет мир.",
                        "work": "Идиот",
                        "year": 1869,
                        "emoji": "🌟",
                        "theme": "философия"
                    },
                    {
                        "text": "Свобода не в том, чтоб не сдерживать себя, а в том, чтоб владеть собой.",
                        "work": "Записки из подполья",
                        "year": 1864,
                        "emoji": "🕊️",
                        "theme": "свобода"
                    }
                ],
                "gigachad": [
                    {
                        "text": "Книги — это качалка для мозга. Делай подходы каждый день!",
                        "work": "Философия прокачки",
                        "year": "Вечность",
                        "emoji": "💪",
                        "theme": "мотивация"
                    },
                    {
                        "text": "Настоящий мужчина читает классику утром, после зарядки.",
                        "work": "Утренний ритуал",
                        "year": "Легенда",
                        "emoji": "🏋️",
                        "theme": "дисциплина"
                    }
                ]
            }
            
            with open(self.quotes_file, 'w', encoding='utf-8') as f:
                json.dump(beautiful_quotes, f, ensure_ascii=False, indent=2)
    
    def get_daily_quote(self, author_key: str = None, formatted: bool = True) -> Dict:
        """Получает цитату дня с красивым оформлением"""
        if author_key and author_key in self.quotes:
            quotes_list = self.quotes[author_key]
        else:
            # Объединяем все цитаты
            all_quotes = []
            for author_quotes in self.quotes.values():
                all_quotes.extend(author_quotes)
            quotes_list = all_quotes
        
        if not quotes_list:
            return {"text": "Мудрость требует тишины...", "work": "", "emoji": "🤫"}
        
        # Детерминированный выбор по дате
        day_of_year = datetime.now().timetuple().tm_yday
        quote = quotes_list[day_of_year % len(quotes_list)]
        
        # Добавляем оформление если нужно
        if formatted and "text" in quote:
            style = random.choice(self.quote_styles)
            quote["formatted_text"] = style.format(quote["text"])
        
        return quote
    
    def format_quote_for_display(self, quote: Dict) -> str:
        """Форматирует цитату для красивого отображения"""
        if not quote:
            return "Цитата не найдена..."
        
        text = quote.get("formatted_text", quote.get("text", ""))
        work = quote.get("work", "")
        emoji = quote.get("emoji", "📖")
        theme = quote.get("theme", "")
        year = quote.get("year", "")
        
        formatted = f"{emoji} {text}\n\n"
        
        if work:
            formatted += f"📚 <i>— {work}"
            if year:
                formatted += f" ({year})"
            formatted += "</i>\n"
        
        if theme:
            formatted += f"🎭 <b>Тема:</b> {theme}\n"
        
        return formatted
    
    def get_quote_of_the_day(self) -> str:
        """Возвращает полностью оформленную цитату дня"""
        quote = self.get_daily_quote()
        return self.format_quote_for_display(quote)
    
    def get_random_quote_by_theme(self, theme: str) -> Dict:
        """Получает случайную цитату по теме"""
        all_quotes = []
        for author_quotes in self.quotes.values():
            for q in author_quotes:
                if q.get("theme") == theme:
                    all_quotes.append(q)
        
        if not all_quotes:
            return self.get_daily_quote()
        
        return random.choice(all_quotes)

# Глобальный экземпляр
daily_quotes = DailyQuotes()
