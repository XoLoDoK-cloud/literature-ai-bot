import json
import os
from datetime import datetime
import random

class DailyQuotes:
    """Сервис ежедневных цитат"""
    
    def __init__(self, quotes_file: str = "data/quotes.json"):
        self.quotes_file = quotes_file
        self._ensure_quotes_file()
        self.quotes = self._load_quotes()
    
    def _ensure_quotes_file(self):
        """Создает файл с цитатами если его нет"""
        if not os.path.exists(self.quotes_file):
            default_quotes = {
                "pushkin": [
                    {"text": "Я вас любил: любовь еще, быть может, В душе моей угасла не совсем...", "work": "Я вас любил"},
                    {"text": "Мороз и солнце; день чудесный!", "work": "Зимнее утро"},
                    {"text": "Унылая пора! Очей очарованье!", "work": "Осень"},
                    {"text": "Блажен, кто смолоду был молод, Блажен, кто вовремя созрел.", "work": "Евгений Онегин"}
                ],
                "dostoevsky": [
                    {"text": "Красота спасет мир.", "work": "Идиот"},
                    {"text": "Свобода не в том, чтоб не сдерживать себя, а в том, чтоб владеть собой.", "work": "Записки из подполья"},
                    {"text": "Страдание есть единственная причина сознания.", "work": "Записки из подполья"}
                ],
                "tolstoy": [
                    {"text": "Все счастливые семьи похожи друг на друга, каждая несчастливая семья несчастлива по-своему.", "work": "Анна Каренина"},
                    {"text": "Сила правительства держится на невежестве народа.", "work": "Война и мир"},
                    {"text": "Нет величия там, где нет простоты, добра и правды.", "work": "Война и мир"}
                ],
                "gogol": [
                    {"text": "Какой же русский не любит быстрой езды?", "work": "Мертвые души"},
                    {"text": "Нет уз святее товарищества!", "work": "Тарас Бульба"}
                ],
                "gigachad": [
                    {"text": "Книги — это качалка для мозга. Делай подходы каждый день! 💪", "work": "Философия прокачки"},
                    {"text": "Настоящий мужчина читает классику утром, после зарядки. 🏋️", "work": "Утренний ритуал"},
                    {"text": "Каждая прочитанная книга — +10 к силе характера. 📚", "work": "Уровень прокачки"}
                ]
            }
            os.makedirs(os.path.dirname(self.quotes_file), exist_ok=True)
            with open(self.quotes_file, 'w', encoding='utf-8') as f:
                json.dump(default_quotes, f, ensure_ascii=False, indent=2)
    
    def _load_quotes(self) -> dict:
        """Загружает цитаты из файла"""
        with open(self.quotes_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_daily_quote(self, author_key: str) -> dict:
        """Получает цитату дня для автора (детерминированно по дате)"""
        if author_key not in self.quotes:
            author_key = "pushkin"
        
        quotes_list = self.quotes[author_key]
        if not quotes_list:
            return {"text": "Цитата не найдена.", "work": ""}
        
        # Используем дату для детерминированного выбора
        day_of_year = datetime.now().timetuple().tm_yday
        quote_index = day_of_year % len(quotes_list)
        
        return quotes_list[quote_index]
    
    def add_quote(self, author_key: str, text: str, work: str = ""):
        """Добавляет новую цитату"""
        if author_key not in self.quotes:
            self.quotes[author_key] = []
        
        self.quotes[author_key].append({"text": text, "work": work})
        
        # Сохраняем
        with open(self.quotes_file, 'w', encoding='utf-8') as f:
            json.dump(self.quotes, f, ensure_ascii=False, indent=2)
    
    def get_random_quote(self, author_key: str = None) -> dict:
        """Получает случайную цитату"""
        if author_key and author_key in self.quotes:
            return random.choice(self.quotes[author_key])
        
        # Или случайную цитату любого автора
        all_quotes = []
        for author_quotes in self.quotes.values():
            all_quotes.extend(author_quotes)
        
        return random.choice(all_quotes) if all_quotes else {"text": "Цитата не найдена.", "work": ""}

# Создаем глобальный экземпляр
daily_quotes = DailyQuotes()
