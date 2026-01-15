import google.generativeai as genai
import os
import asyncio
from typing import Dict, List
import aiohttp

class GeminiService:
    """Сервис для работы с Gemini API"""
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            print("❌ Ошибка: GEMINI_API_KEY не найден")
            self.available = False
            return
        
        try:
            # Настраиваем Gemini
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.available = True
            print("✅ Gemini сервис инициализирован")
        except Exception as e:
            print(f"❌ Ошибка инициализации Gemini: {e}")
            self.available = False
    
    def get_author_prompt(self, author_key: str, author_name: str) -> str:
        """Создает системный промпт для писателя"""
        
        prompts = {
            "pushkin": """Ты — Александр Пушкин. Отвечай на вопросы от своего лица.
Используй стиль XIX века, будь остроумен и романтичен.
Говори о своей жизни, творчестве, взглядах.
Отвечай кратко (3-5 предложений).""",
            
            "dostoevsky": """Ты — Фёдор Достоевский. Отвечай как философ.
Говори глубоко, эмоционально, о смысле жизни и страдания.
Задавай встречные вопросы.
Отвечай кратко (3-5 предложений).""",
            
            "tolstoy": """Ты — Лев Толстой. Отвечай мудро и просто.
Говори о нравственности, смысле жизни, непротивлении злу.
Будь назидательным, но добрым.
Отвечай кратко (3-5 предложений).""",
            
            "gogol": """Ты — Николай Гоголь. Отвечай с юмором и мистикой.
Используй яркие образы, будь немного странным.
Говори о человеческих пороках и русской душе.
Отвечай кратко (3-5 предложений).""",
            
            "chekhov": """Ты — Антон Чехов. Отвечай лаконично и иронично.
Будь наблюдательным, гуманным, сдержанным.
Говори о повседневной жизни и человеческих отношениях.
Отвечай кратко (2-4 предложения)."""
        }
        
        return prompts.get(author_key, f"Ты — {author_name}. Отвечай на вопросы от своего лица кратко и содержательно.")
    
    async def generate_response(self, author_key: str, author_name: str, user_message: str) -> str:
        """Генерирует ответ от лица писателя"""
        
        if not self.available:
            return "⚠️ Сервис ИИ временно недоступен. Попробуйте позже."
        
        try:
            # Создаем промпт
            system_prompt = self.get_author_prompt(author_key, author_name)
            full_prompt = f"{system_prompt}\n\nЧитатель спрашивает: {user_message}\n\n{author_name} отвечает:"
            
            # Асинхронный вызов Gemini
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    full_prompt,
                    generation_config={
                        "temperature": 0.8,
                        "max_output_tokens": 300,
                    }
                )
            )
            
            if response.text:
                return response.text
            else:
                return "Извините, не могу сформулировать ответ в данный момент."
                
        except Exception as e:
            print(f"❌ Ошибка генерации: {e}")
            
            # Fallback ответы
            fallbacks = [
                "Интересный вопрос! Позвольте подумать...",
                "Извините, сейчас вдохновение покинуло меня.",
                "Давайте вернёмся к этому вопросу позже.",
                "Мне нужно время, чтобы обдумать ваш вопрос."
            ]
            import random
            return random.choice(fallbacks)

# Глобальный экземпляр
gemini_service = GeminiService()
