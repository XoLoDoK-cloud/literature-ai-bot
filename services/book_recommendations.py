import json
import os
import random
from typing import Dict, List
from datetime import datetime

class BookRecommendations:
    """Сервис рекомендаций книг"""
    
    def __init__(self, books_file: str = "data/books.json"):
        self.books_file = books_file
        self.books = self._load_books()
        self.user_preferences = {}  # user_id: {genres: [], authors: []}
    
    def _load_books(self) -> List[Dict]:
        """Загружает базу книг"""
        if not os.path.exists(self.books_file):
            return self._get_default_books()
        
        try:
            with open(self.books_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return self._get_default_books()
    
    def _get_default_books(self) -> List[Dict]:
        """Возвращает стандартную базу книг"""
        return [
            {
                "id": "pushkin_evgeny",
                "title": "Евгений Онегин",
                "author": "Александр Пушкин",
                "year": 1833,
                "genre": "Роман в стихах",
                "description": "Вершина творчества Пушкина, первый русский реалистический роман.",
                "difficulty": "Средняя",
                "pages": 240,
                "reason": "Идеально для знакомства с русской классикой"
            },
            {
                "id": "dostoevsky_crime",
                "title": "Преступление и наказание",
                "author": "Фёдор Достоевский",
                "year": 1866,
                "genre": "Психологический роман",
                "description": "Глубокое исследование человеческой психологии и морали.",
                "difficulty": "Сложная",
                "pages": 672,
                "reason": "Для тех, кто хочет понять глубины человеческой души"
            },
            {
                "id": "tolstoy_war",
                "title": "Война и мир",
                "author": "Лев Толстой",
                "year": 1869,
                "genre": "Исторический роман-эпопея",
                "description": "Монументальное произведение о войне 1812 года и русском обществе.",
                "difficulty": "Очень сложная",
                "pages": 1225,
                "reason": "Величайший русский роман, меняющий мировоззрение"
            },
            {
                "id": "gogol_dead",
                "title": "Мёртвые души",
                "author": "Николай Гоголь",
                "year": 1842,
                "genre": "Поэма в прозе",
                "description": "Сатира на русское чиновничество и помещичий быт.",
                "difficulty": "Средняя",
                "pages": 352,
                "reason": "Блестящая сатира, актуальная и сегодня"
            },
            {
                "id": "chekhov_garden",
                "title": "Вишнёвый сад",
                "author": "Антон Чехов",
                "year": 1904,
                "genre": "Драма",
                "description": "Прощание с уходящей эпохой дворянской России.",
                "difficulty": "Легкая",
                "pages": 96,
                "reason": "Идеальное введение в русскую драматургию"
            }
        ]
    
    def get_recommendations(self, conversation_history: List[Dict], 
                           user_preferences: List[str] = None) -> List[Dict]:
        """Получает персонализированные рекомендации"""
        
        # Анализируем историю диалога
        mentioned_authors = []
        mentioned_genres = []
        
        for msg in conversation_history[-10:]:
            text = msg.get("content", "").lower()
            
            # Ищем упоминания авторов
            if "пушкин" in text:
                mentioned_authors.append("pushkin")
            if "достоевск" in text:
                mentioned_authors.append("dostoevsky")
            if "толст" in text:
                mentioned_authors.append("tolstoy")
            if "гогол" in text:
                mentioned_authors.append("gogol")
            if "чехов" in text:
                mentioned_authors.append("chekhov")
            
            # Ищем упоминания жанров
            if any(word in text for word in ["поэм", "стих", "рифм"]):
                mentioned_genres.append("поэзия")
            if any(word in text for word in ["роман", "проз", "повесть"]):
                mentioned_genres.append("проза")
            if any(word in text for word in ["драм", "пьес", "театр"]):
                mentioned_genres.append("драма")
            if any(word in text for word in ["философ", "психолог", "душ"]):
                mentioned_genres.append("философия")
        
        # Фильтруем книги
        filtered_books = []
        
        for book in self.books:
            score = 0
            
            # Очки за автора
            author_lower = book["author"].lower()
            if any(author in author_lower for author in ["пушкин"]):
                if "pushkin" in mentioned_authors:
                    score += 3
            if any(author in author_lower for author in ["достоевск"]):
                if "dostoevsky" in mentioned_authors:
                    score += 3
            if any(author in author_lower for author in ["толст"]):
                if "tolstoy" in mentioned_authors:
                    score += 3
            
            # Очки за жанр
            if mentioned_genres:
                for genre in mentioned_genres:
                    if genre in book["genre"].lower():
                        score += 2
            
            # Очки за сложность (предпочитаем среднюю)
            if book["difficulty"] == "Средняя":
                score += 1
            
            if score > 0:
                filtered_books.append((score, book))
        
        # Сортируем по релевантности
        filtered_books.sort(key=lambda x: x[0], reverse=True)
        
        # Если нет подходящих, возвращаем случайные
        if not filtered_books:
            return random.sample(self.books, min(3, len(self.books)))
        
        # Возвращаем топ рекомендации
        return [book for _, book in filtered_books[:5]]
    
    def get_book_details(self, book_id: str) -> Dict:
        """Получает детальную информацию о книге"""
        for book in self.books:
            if book["id"] == book_id:
                return book
        return None
    
    def update_preferences(self, user_id: int, message: str, author_key: str):
        """Обновляет предпочтения пользователя"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {
                "authors": [],
                "genres": [],
                "last_updated": datetime.now().isoformat()
            }
        
        # Добавляем автора если его еще нет
        if author_key and author_key not in self.user_preferences[user_id]["authors"]:
            self.user_preferences[user_id]["authors"].append(author_key)
        
        # Анализируем сообщение на предмет жанров
        message_lower = message.lower()
        genres = self.user_preferences[user_id]["genres"]
        
        if any(word in message_lower for word in ["стих", "поэм", "рифм"]):
            if "поэзия" not in genres:
                genres.append("поэзия")
        if any(word in message_lower for word in ["роман", "проз", "истор"]):
            if "проза" not in genres:
                genres.append("проза")
        if any(word in message_lower for word in ["драм", "пьес", "театр"]):
            if "драма" not in genres:
                genres.append("драма")
        if any(word in message_lower for word in ["философ", "психолог"]):
            if "философия" not in genres:
                genres.append("философия")
    
    def get_user_preferences(self, user_id: int) -> Dict:
        """Возвращает предпочтения пользователя"""
        return self.user_preferences.get(user_id, {
            "authors": [],
            "genres": [],
            "last_updated": datetime.now().isoformat()
        })

# Глобальный экземпляр
book_recommendations = BookRecommendations()
