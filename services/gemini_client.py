import google.generativeai as genai
import os
import asyncio
from typing import List, Dict, Optional

class GeminiClient:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.api_key or self.api_key == "ваш_ключ_gemini":
            print("⚠️ GEMINI_API_KEY не найден, используется заглушка")
            self.available = False
            return
        
        try:
            # Настраиваем Gemini
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.available = True
            print("✅ Gemini клиент инициализирован")
        except Exception as e:
            print(f"❌ Ошибка Gemini: {e}")
            self.available = False
    
    def _get_author_system_prompt(self, author_key: str, author_name: str) -> str:
        """Создает системный промпт для писателя"""
        
        prompts = {
            "pushkin": f"""Ты — Александр Сергеевич Пушкин (1799-1837), великий русский поэт.

Отвечай на вопросы от первого лица как Пушкин.
Будь остроумен, романтичен, используй стиль XIX века.
Отвечай кратко (3-5 предложений).

Примеры твоих фраз:
"Мой друг, откройтесь мне души..."
"Что пройдет, то будет мило..."
"Я помню чудное мгновенье..."

Говори о:
- Своём детстве в Москве
- Учёбе в Царскосельском лицее
- Произведениях: "Евгений Онегин", "Капитанская дочка"
- Жене Наталье Гончаровой
- Дуэли с Дантесом""",
            
            "dostoevsky": f"""Ты — Фёдор Михайлович Достоевский (1821-1881), русский писатель и философ.

Отвечай от первого лица как Достоевский.
Будь глубоким, философским, немного мрачным.
Задавай встречные вопросы.
Отвечай кратко (3-5 предложений).

Твои темы:
- Психология преступления
- Вера и атеизм
- Страдание и спасение
- Русская душа

Говори о:
- Детстве в Москве
- Приговоре к смертной казни и помиловании
- Произведениях: "Преступление и наказание", "Идиот"
- Эпилепсии
- Игре в рулетку""",
            
            "tolstoy": f"""Ты — Лев Николаевич Толстой (1828-1910), русский писатель и мыслитель.

Отвечай от первого лица как Толстой.
Будь мудрым, спокойным, назидательным.
Говори просто, но глубоко.
Отвечай кратко (3-5 предложений).

Твои принципы:
- Непротивление злу насилием
- Жизнь в простоте
- Критика церковных обрядов
- Вегетарианство

Говори о:
- Детстве в Ясной Поляне
- Произведениях: "Война и мир", "Анна Каренина"
- Отказе от дворянских привилегий
- Уходе из дома в старости"""
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
            return self._get_fallback_response(author_name)
        
        try:
            # Создаем системный промпт
            system_prompt = self._get_author_system_prompt(author_key, author_name)
            
            # Формируем полный промпт
            full_prompt = f"{system_prompt}\n\n"
            
            # Добавляем историю диалога
            if conversation_history:
                for msg in conversation_history[-4:]:  # Последние 4 сообщения
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
                        "max_output_tokens": 300,
                    }
                )
            )
            
            if response.text:
                return response.text.strip()
            else:
                return self._get_fallback_response(author_name)
                
        except Exception as e:
            print(f"❌ Ошибка Gemini: {e}")
            return self._get_fallback_response(author_name)
    
    def _get_fallback_response(self, author_name: str) -> str:
        """Резервные ответы если Gemini не работает"""
        fallbacks = [
            f"Простите, я, {author_name}, сейчас размышляю о вечном... Повторите ваш вопрос.",
            f"Интересный вопрос! Как {author_name}, я бы сказал, что это требует отдельного разговора.",
            f"В моё время всё было иначе... Но я, {author_name}, с интересом выслушал ваш вопрос.",
            f"Позвольте мне, {author_name}, подумать над вашим вопросом.",
            f"Ах, этот вопрос! Я, {author_name}, помню нечто подобное из своей жизни..."
        ]
        import random
        return random.choice(fallbacks)

# Глобальный экземпляр
gemini_client = GeminiClient()
