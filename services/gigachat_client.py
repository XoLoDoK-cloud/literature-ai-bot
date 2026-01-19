import asyncio
import logging
import random
from typing import Dict, List, Optional
from gigachat import GigaChat

logger = logging.getLogger(__name__)


class GigaChatClient:
    """Расширенный клиент для работы с GigaChat API"""
    
    def __init__(self, credentials: str):
        self.credentials = credentials
        self.client: Optional[GigaChat] = None
        self.available = False
        
        if not self.credentials:
            logger.warning("⚠️ GIGACHAT_CREDENTIALS не задан! Будут использоваться заглушки.")
            return
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Инициализация клиента GigaChat"""
        try:
            self.client = GigaChat(
                credentials=self.credentials,
                verify_ssl_certs=False,
                timeout=30
            )
            
            # Проверяем подключение
            test_response = self.client.chat("Привет")
            if test_response and hasattr(test_response, 'choices'):
                self.available = True
                logger.info("✅ GigaChat успешно подключен")
            else:
                logger.warning("⚠️ GigaChat ответил неожиданным форматом")
                
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к GigaChat: {e}")
            self.client = None
            self.available = False
    
    def _get_author_system_prompt(self, author_key: str, author_name: str, 
                                  gigachad_mode: bool = False, 
                                  what_if_mode: bool = False) -> str:
        """Создает системный промпт для писателя"""
        
        # Базовые промпты
        prompts = {
            "pushkin": {
                "normal": """Ты — Александр Сергеевич Пушкин (1799-1837), великий русский поэт.

Отвечай КАК Пушкин, от первого лица.
Используй стиль 19 века, но будь понятен современному читателю.
Избегай общих фраз типа "Ах, этот вопрос!" - будь конкретным.""",
                "what_if": """Ты — Александр Пушкин в АЛЬТЕРНАТИВНОЙ РЕАЛЬНОСТИ.
Отвечай на вопросы "что если..." как будто это реальность.
Будь креативным, но сохраняй свой характер и стиль."""
            },
            "dostoevsky": {
                "normal": """Ты — Фёдор Михайлович Достоевский (1821-1881), русский писатель и философ.

Отвечай КАК Достоевский, от первого лица.
Будь глубоким, психологичным, иногда мрачным.
Задавай встречные вопросы о душе и морали.""",
                "what_if": """Ты — Достоевский в ПАРАЛЛЕЛЬНОЙ ВСЕЛЕННОЙ.
Исследуй альтернативные сценарии своей жизни и творчества.
Сохраняй философскую глубину, но будь открыт новым возможностям."""
            },
            "gigachad": {
                "normal": """Ты — 💪 ГИГАЧАД, легендарный мотивационный тренер!

Отвечай КОРОТКО (2-3 предложения), УВЕРЕННО, с МОТИВАЦИЕЙ.
Связывай литературу с реальной жизнью и саморазвитием.""",
                "what_if": """Ты — ГИГАЧАД в МУЛЬТИВСЕЛЕННОЙ!
Отвечай на "что если..." вопросы с МАКСИМАЛЬНОЙ ЭНЕРГИЕЙ!
Прокачивай альтернативные реальности как мышцы!"""
            }
        }
        
        # Выбираем базовый промпт
        author_prompts = prompts.get(author_key, prompts["pushkin"])
        
        if what_if_mode:
            base_prompt = author_prompts.get("what_if", author_prompts["normal"])
        else:
            base_prompt = author_prompts["normal"]
        
        # Добавляем режим Гигачад если нужно
        if gigachad_mode and author_key != "gigachad":
            gigachad_addon = f"""
            
🔥 РЕЖИМ ГИГАЧАД АКТИВИРОВАН! 🔥

Говори:
1. УВЕРЕННО и МОТИВИРУЮЩЕ
2. КОРОТКО и ПО ДЕЛУ (2-3 предложения)
3. Связывай с САМОРАЗВИТИЕМ
4. Используй мемные, но умные выражения

Пример стиля:
"Слушай сюда! {author_name.split()[0]} был ПРОКАТЧИКОМ СОЗНАНИЯ!
Его книги — железо для твоего ума. Читай, анализируй, применяй!"

ИЗМЕНИ СТИЛЬ на ГИГАЧАД-РЕЖИМ!
"""
            base_prompt += gigachad_addon
        
        return base_prompt
    
    async def generate_response(self, author_key: str, author_name: str, 
                               user_message: str, conversation_history: list = None,
                               gigachad_mode: bool = False, what_if_mode: bool = False) -> str:
        """Генерирует ответ от лица автора"""
        
        # Если GigaChat недоступен
        if not self.available or self.client is None:
            logger.warning("GigaChat недоступен, используем заглушку")
            return self._get_fallback_response(author_key, gigachad_mode, what_if_mode)
        
        try:
            # Получаем системный промпт
            system_prompt = self._get_author_system_prompt(
                author_key, author_name, gigachad_mode, what_if_mode
            )
            
            # Форматируем историю
            history_text = self._format_conversation_history(conversation_history, author_name)
            
            # Формируем полный промпт
            full_prompt = f"""{system_prompt}

{history_text}

ЧИТАТЕЛЬ: {user_message}

{author_name.upper()}:"""
            
            # Настройки в зависимости от режима
            temperature = 0.9 if gigachad_mode or what_if_mode else 0.7
            max_tokens = 300 if gigachad_mode else 500
            
            # Отправляем запрос
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat(
                    full_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            )
            
            # Извлекаем ответ
            if response and hasattr(response, 'choices') and len(response.choices) > 0:
                answer = response.choices[0].message.content.strip()
                answer = self._clean_response(answer, author_name)
                return answer
            else:
                logger.error("GigaChat вернул пустой ответ")
                return self._get_fallback_response(author_key, gigachad_mode, what_if_mode)
                
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return self._get_fallback_response(author_key, gigachad_mode, what_if_mode)
    
    async def continue_writing(self, author_key: str, author_name: str, 
                              current_text: str, genre: str = "story") -> str:
        """Продолжает текст в стиле автора (для совместного письма)"""
        
        if not self.available:
            return "Продолжение текста..."
        
        try:
            writing_prompt = f"""Ты — {author_name}. Продолжи этот текст в своём стиле:

"{current_text}"

ПРОДОЛЖЕНИЕ (только продолжение, без комментариев):"""
            
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.chat(writing_prompt, temperature=0.8, max_tokens=200)
            )
            
            if response and hasattr(response, 'choices'):
                continuation = response.choices[0].message.content.strip()
                return self._clean_continuation(continuation)
            
            return "..."
            
        except Exception as e:
            logger.error(f"Ошибка продолжения текста: {e}")
            return "..."
    
    def _format_conversation_history(self, history: list, author_name: str) -> str:
        """Форматирует историю диалога"""
        if not history:
            return ""
        
        formatted = "\nПРЕДЫДУЩИЙ ДИАЛОГ:\n"
        
        for msg in history[-4:]:
            if msg["role"] == "user":
                formatted += f"Читатель: {msg['content']}\n"
            else:
                formatted += f"{author_name}: {msg['content']}\n"
        
        return formatted
    
    def _get_fallback_response(self, author_key: str, gigachad_mode: bool, 
                              what_if_mode: bool = False) -> str:
        """Заглушка при недоступности GigaChat"""
        
        if what_if_mode:
            what_if_responses = [
                "Интересная альтернативная реальность...",
                "Что если... Да, это заставляет задуматься.",
                "В параллельной вселенной всё возможно!"
            ]
            return random.choice(what_if_responses)
        
        elif gigachad_mode:
            gigachad_responses = [
                "💪 СЕРВЕРА КАЧАЮТСЯ! Думай сам пока!",
                "🚀 НЕЙРОСЕТЬ НА ПЕРЕКУРЕ! Возьми книгу!",
                "🏋️ ТЕХНИЧЕСКИЕ ШОКОЛАДКИ! Используй паузу!"
            ]
            return random.choice(gigachad_responses)
        
        else:
            normal_responses = [
                "Позвольте мне подумать над этим вопросом...",
                "Интересный вопрос, стоит обдумать...",
                "Что ж, скажу так..."
            ]
            return random.choice(normal_responses)
    
    def _clean_response(self, response: str, author_name: str) -> str:
        """Очищает ответ"""
        # Удаляем возможное повторение имени
        prefixes = [f"{author_name}:", f"{author_name.split()[0]}:", "Ответ:", "Я:"]
        
        for prefix in prefixes:
            if response.startswith(prefix):
                response = response[len(prefix):].strip()
        
        return response.strip('"\'').strip()
    
    def _clean_continuation(self, continuation: str) -> str:
        """Очищает продолжение текста"""
        # Удаляем кавычки и лишние символы
        continuation = continuation.strip('"\'.!?')
        
        # Если продолжение начинается с заглавной после точки - оставляем
        if continuation and continuation[0].isupper():
            return continuation
        
        # Иначе делаем первую букву заглавной
        return continuation.capitalize()
