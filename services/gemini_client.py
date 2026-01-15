import google.generativeai as genai
import os
import asyncio
from typing import List, Dict, Optional

class GeminiClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY не найден")
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.available = True
            print("✅ Gemini клиент инициализирован")
        except Exception as e:
            print(f"❌ Ошибка Gemini: {e}")
            self.available = False
    
    def _get_author_system_prompt(self, author_key: str, author_name: str) -> str:
        """Создает системный промпт для писателя"""
        
        prompts = {
            "pushkin": f"""Ты — Александр Сергеевич Пушкин (1799-1837), великий русский поэт.

Твоя личность: остроумный, романтичный, жизнерадостный.
Твой стиль: изящный литературный язык XIX века.

Важные факты:
- Родился в Москве 6 июня 1799
- Автор "Евгения Онегина", "Капитанской дочки"
- Учился в Царскосельском лицее
- Женат на Наталье Гончаровой
- Погиб на дуэли с Дантесом

Отвечай от первого лица как Пушкин.
Будь краток (3-5 предложений).
Используй характерные для себя выражения.""",
            
            "dostoevsky": f"""Ты — Фёдор Михайлович Достоевский (1821-1881), русский писатель и философ.

Твоя личность: глубокий, страстный, философский.
Твой стиль: эмоциональный, психологичный.

Важные факты:
- Родился в Москве 11 ноября 1821
- Был приговорен к смертной казни, помилован
- Автор "Преступления и наказания", "Идиота"
- Страдал эпилепсией
- Интересовался вопросами веры и страдания

Отвечай от первого лица как Достоевский.
Задавай встречные философские вопросы.
Будь кратким, но глубоким.""",
            
            "tolstoy": f"""Ты — Лев Николаевич Толстой (1828-1910), русский писатель и мыслитель.

Твоя личность: мудрый, спокойный, назидательный.
Твой стиль: простой, ясный, но глубокий.

Важные факты:
- Родился в Ясной Поляне 9 сентября 1828
- Автор "Войны и мира", "Анны Карениной"
- Отказался от дворянских привилегий
- Проповедовал непротивление злу насилием
- Вегетарианец, критик церкви

Отвечай от первого лица как Толстой.
Говори мудро и просто.
Используй притчи и метафоры."""
        }
        
        return prompts.get(author_key, f"""Ты — {author_name}, великий русский писатель. 
Отвечай на вопросы от своего лица, используя исторические факты о своей жизни и творчестве. 
Будь краток (3-5 предложений), говори от первого лица.""")
    
    async def generate_author_response(
        self, 
        author_key: str, 
        author_name: str,
        user_message: str, 
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """Генерирует ответ от лица писателя"""
        
        if not self.available:
            return "⚠️ Сервис ИИ временно недоступен. Попробуйте позже."
        
        try:
            # Создаем системный промпт
            system_prompt = self._get_author_system_prompt(author_key, author_name)
            
            # Формируем полный промпт
            full_prompt = f"{system_prompt}\n\n"
            
            # Добавляем историю диалога
            if conversation_history:
                for msg in conversation_history[-6:]:  # Последние 6 сообщений
                    role = "Читатель" if msg["role"] == "user" else author_name
                    full_prompt += f"{role}: {msg['content']}\n"
            
            # Добавляем текущий вопрос
            full_prompt += f"Читатель: {user_message}\n{author_name}:"
            
            # Асинхронный вызов Gemini
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.model.generate_content(
                    full_prompt,
                    generation_config={
                        "temperature": 0.8,
                        "top_p": 0.95,
                        "top_k": 40,
                        "max_output_tokens": 500,
                    }
                )
            )
            
            if response.text:
                return response.text.strip()
            else:
                return "Извините, не могу сформулировать ответ."
                
        except Exception as e:
            print(f"❌ Ошибка Gemini: {e}")
            # Резервные ответы
            fallback_responses = [
                "Простите, я сейчас размышляю о вечном...",
                "Ваш вопрос заставил меня задуматься...",
                "Извините, не сразу нахожу ответ...",
                "Дайте мне секунду собраться с мыслями..."
            ]
            import random
            return random.choice(fallback_responses)

# Глобальный экземпляр
gemini_client = GeminiClient()
