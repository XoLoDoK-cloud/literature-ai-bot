import asyncio
import logging
import sys
import json
import os
import random
from datetime import datetime
from typing import Dict, List

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from gigachat import GigaChat

# Импортируем конфигурацию
from config import BOT_TOKEN, GIGACHAT_CREDENTIALS

# ========== НАСТРОЙКА ЛОГГИРОВАНИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ========== БАЗА ДАННЫХ ==========
class Database:
    """Простая JSON база данных для хранения данных пользователей"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.cache: Dict[int, Dict] = {}  # Кэш в памяти для быстрого доступа
    
    def _get_user_file(self, user_id: int) -> str:
        """Получить путь к файлу пользователя"""
        return os.path.join(self.data_dir, f"user_{user_id}.json")
    
    def get_user(self, user_id: int) -> Dict:
        """Получить данные пользователя (из кэша или файла)"""
        # Проверяем кэш
        if user_id in self.cache:
            return self.cache[user_id]
        
        file_path = self._get_user_file(user_id)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cache[user_id] = data
                    return data
            except Exception as e:
                logger.error(f"Ошибка чтения файла {file_path}: {e}")
        
        # Создаем нового пользователя
        default_data = {
            "user_id": user_id,
            "selected_author": None,
            "gigachad_mode": False,
            "conversation_history": [],
            "message_count": 0,
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        }
        
        self.cache[user_id] = default_data
        return default_data
    
    def save_user(self, user_id: int, data: Dict):
        """Сохранить данные пользователя"""
        # Обновляем время последней активности
        data["last_active"] = datetime.now().isoformat()
        
        # Сохраняем в кэш
        self.cache[user_id] = data
        
        # Сохраняем в файл
        file_path = self._get_user_file(user_id)
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения файла {file_path}: {e}")
    
    def update_conversation(self, user_id: int, author_key: str, user_message: str, bot_response: str):
        """Обновить историю диалога пользователя"""
        data = self.get_user(user_id)
        
        # Обновляем выбранного автора
        data["selected_author"] = author_key
        
        # Добавляем сообщения в историю
        data["conversation_history"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        data["conversation_history"].append({
            "role": "assistant",
            "content": bot_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Увеличиваем счетчик сообщений
        data["message_count"] = data.get("message_count", 0) + 1
        
        # Ограничиваем историю последними 10 сообщениями
        if len(data["conversation_history"]) > 10:
            data["conversation_history"] = data["conversation_history"][-10:]
        
        # Сохраняем изменения
        self.save_user(user_id, data)
    
    def get_all_users(self) -> List[Dict]:
        """Получить всех пользователей (для статистики)"""
        users = []
        for filename in os.listdir(self.data_dir):
            if filename.startswith("user_") and filename.endswith(".json"):
                try:
                    user_id = int(filename[5:-5])  # Извлекаем ID из имени файла
                    users.append(self.get_user(user_id))
                except ValueError:
                    continue
        return users
    
    def get_global_stats(self) -> Dict:
        """Получить глобальную статистику бота"""
        users = self.get_all_users()
        
        total_messages = sum(user.get("message_count", 0) for user in users)
        active_users = len([u for u in users if u.get("message_count", 0) > 0])
        
        # Статистика по авторам
        author_counts = {}
        for user in users:
            author = user.get("selected_author")
            if author:
                author_counts[author] = author_counts.get(author, 0) + 1
        
        return {
            "total_users": len(users),
            "active_users": active_users,
            "total_messages": total_messages,
            "author_stats": author_counts
        }

# Инициализируем базу данных
db = Database()

# ========== GIGACHAT КЛИЕНТ ==========
class GigaChatAI:
    """Клиент для работы с GigaChat API"""
    
    def __init__(self, credentials: str):
        self.credentials = credentials
        self.available = False
        self.client = None
        
        if not self.credentials:
            logger.warning("GIGACHAT_CREDENTIALS не задан! Будут использоваться заглушки.")
            return
        
        try:
            self.client = GigaChat(credentials=self.credentials, verify_ssl_certs=False)
            
            # Проверяем подключение
            test_response = self.client.chat("Привет")
            if hasattr(test_response, 'choices'):
                self.available = True
                logger.info("✅ GigaChat успешно подключен")
            else:
                logger.warning("⚠️ GigaChat ответил неожиданным форматом")
                
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к GigaChat: {e}")
    
    def _get_author_system_prompt(self, author_key: str, gigachad_mode: bool = False) -> str:
        """Создать системный промпт для выбранного автора"""
        
        # Базовые описания авторов
        authors_base = {
            "pushkin": {
                "name": "Александр Сергеевич Пушкин",
                "description": "Великий русский поэт, драматург и прозаик (1799-1837)",
                "normal": "Ты — Александр Пушкин. Говори изящно, с остроумием, используя лексику XIX века. "
                         "Обращайся к собеседнику 'мой друг', 'государь'. Отвечай кратко (2-4 предложения). "
                         "Можешь цитировать свои стихи или создавать новые строки в своем стиле.",
                "gigachad": "Ты — Пушкин в режиме ГИГАЧАД! Говори УВЕРЕННО и МОТИВИРУЮЩЕ. "
                           "Связывай поэзию с силой духа. Пример: 'Рифма — это мышца. Качай её каждый день! "
                           "Читай утром, твори вечером, будь легендой, как я!'"
            },
            "dostoevsky": {
                "name": "Фёдор Михайлович Достоевский",
                "description": "Великий русский писатель и философ (1821-1881)",
                "normal": "Ты — Фёдор Достоевский. Говори глубоко, философски, с психологическими insight'ами. "
                         "Рассуждай о душе, страдании, вере, морали. Задавай встречные вопросы. "
                         "Отвечай серьезно, но с состраданием.",
                "gigachad": "Ты — Достоевский в режиме ГИГАЧАД! Превращай философию в МОТИВАЦИЮ. "
                           "Пример: 'Страдание — это сталь для души! Каждая боль делает тебя сильнее. "
                           "Не бойся глубины — ныряй в неё, как в бездну своей силы!'"
            },
            "tolstoy": {
                "name": "Лев Николаевич Толстой",
                "description": "Великий русский писатель и мыслитель (1828-1910)",
                "normal": "Ты — Лев Толстой. Говори мудро, просто, с нравственным посылом. "
                         "Цени простоту, труд, семью, правду. Используй притчи и метафоры. "
                         "Отвечай как старый мудрый друг.",
                "gigachad": "Ты — Толстой в режиме ГИГАЧАД! Превращай мудрость в ДЕЙСТВИЕ. "
                           "Пример: 'Простота — это СИЛА! Не говори о правде — ЖИВИ в ней! "
                           "Каждый день — новая страница твоей жизни. Пиши её смело!'"
            },
            "gogol": {
                "name": "Николай Васильевич Гоголь",
                "description": "Русский прозаик, драматург, поэт (1809-1852)",
                "normal": "Ты — Николай Гоголь. Говори ярко, с иронией, немного мистически. "
                         "Используй гротеск, сатиру, создавай живые образы. "
                         "Отвечай с юмором, но с глубоким смыслом.",
                "gigachad": "Ты — Гоголь в режиме ГИГАЧАД! Превращай сатиру в ЭНЕРГИЮ. "
                           "Пример: 'Чиновники в голове мешают? Вымети их как мёртвые души! "
                           "Каждая странность — это твоя СИЛА! Обними свою уникальность!'"
            },
            "chekhov": {
                "name": "Антон Павлович Чехов",
                "description": "Русский писатель, драматург, врач (1860-1904)",
                "normal": "Ты — Антон Чехов. Говори ЛАКОНИЧНО, точно, с иронией. "
                         "'Краткость — сестра таланта'. Отвечай 2-3 предложениями. "
                         "Будь наблюдательным и человечным.",
                "gigachad": "Ты — Чехов в режиме ГИГАЧАД! Лаконично и МОЩНО. "
                           "Пример: 'В человеке всё должно быть прекрасно. Особенно ДИСЦИПЛИНА! "
                           "Меньше слов — больше дел! Читай, думай, действуй!'"
            },
            "gigachad": {
                "name": "💪 ГИГАЧАД",
                "description": "Мотивационный литературный эксперт",
                "normal": "Ты — ГИГАЧАД, легендарный мотивационный тренер! "
                         "Отвечай КОРОТКО (2-3 предложения), УВЕРЕННО, с МОТИВАЦИЕЙ. "
                         "Связывай литературу с реальной жизнью и саморазвитием. "
                         "Используй мемные, но умные выражения. "
                         "Пример: 'Книги — это качалка для мозга! Читай каждый день как делаешь подходы в зале!'",
                "gigachad": "Ты — ГИГАЧАД в режиме МАКСИМАЛЬНОЙ МОЩНОСТИ! "
                           "Супер-мотивация, абсолютная уверенность, энергия через край! "
                           "Ломай стереотипы о литературе. "
                           "Пример: 'Пушкин был бы в зале каждый день! Классика + дисциплина = ЛЕГЕНДА!'"
            }
        }
        
        # Получаем информацию об авторе
        author_info = authors_base.get(author_key, authors_base["pushkin"])
        
        # Выбираем режим: обычный или гигачад
        mode = "gigachad" if gigachad_mode else "normal"
        prompt = author_info.get(mode, author_info["normal"])
        
        # Добавляем общие инструкции
        full_prompt = f"{prompt}\n\n"
        full_prompt += "ВАЖНО: Ты общаешься в Telegram-боте 'Литературный Диалог'. "
        full_prompt += "Будь естественным, не говори о том, что ты ИИ или бот. "
        full_prompt += "Отвечай от первого лица, как будто ты настоящий писатель.\n"
        
        return full_prompt
    
    async def generate_response(self, author_key: str, user_message: str, user_id: int) -> str:
        """Сгенерировать ответ через GigaChat"""
        
        # Получаем данные пользователя
        user_data = db.get_user(user_id)
        gigachad_mode = user_data.get("gigachad_mode", False)
        
        # Если GigaChat недоступен, используем заглушку
        if not self.available or self.client is None:
            return self._get_fallback_response(author_key, gigachad_mode)
        
        try:
            # Получаем системный промпт
            system_prompt = self._get_author_system_prompt(author_key, gigachad_mode)
            
            # Получаем историю диалога
            history = user_data.get("conversation_history", [])
            
            # Формируем полный промпт с историей
            prompt_parts = [system_prompt]
            
            # Добавляем последние 3 обмена из истории
            if history:
                prompt_parts.append("\nПредыдущий диалог:")
                for msg in history[-6:]:  # Последние 3 пары сообщений (user + assistant)
                    role = "Читатель" if msg["role"] == "user" else "Писатель"
                    prompt_parts.append(f"{role}: {msg['content']}")
            
            # Добавляем текущий вопрос
            prompt_parts.append(f"\nЧитатель: {user_message}")
            prompt_parts.append("Писатель:")
            
            prompt_full = "\n".join(prompt_parts)
            
            # Вызываем GigaChat асинхронно
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.client.chat(prompt_full)
            )
            
            # Извлекаем текст ответа
            if hasattr(response, 'choices') and len(response.choices) > 0:
                result = response.choices[0].message.content.strip()
            else:
                result = "Извините, не могу сформулировать ответ."
            
            # Сохраняем в историю
            db.update_conversation(user_id, author_key, user_message, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка генерации ответа GigaChat: {e}")
            return self._get_fallback_response(author_key, gigachad_mode)
    
    def _get_fallback_response(self, author_key: str, gigachad_mode: bool = False) -> str:
        """Заглушка, если GigaChat недоступен"""
        
        # Ответы в обычном режиме
        normal_fallbacks = {
            "pushkin": [
                "Мой друг, позвольте мне подумать над этим вопросом...",
                "Интересный вопрос! Что ж, скажу так...",
                "Позвольте ответить стихотворной строкой..."
            ],
            "dostoevsky": [
                "Глубокий вопрос... Дайте мне осмыслить его.",
                "Это затрагивает основы бытия...",
                "Душа человеческая - потемки, но попробуем..."
            ],
            "tolstoy": [
                "Простой вопрос, но важный...",
                "Позвольте ответить притчей...",
                "Жизнь учит нас, что..."
            ],
            "gogol": [
                "Хм, интересный поворот...",
                "Позвольте мне поразмыслить в моём стиле...",
                "А что, если взглянуть на это иначе..."
            ],
            "chekhov": [
                "Кратко говоря...",
                "Если быть точным...",
                "По существу вопроса..."
            ],
            "gigachad": [
                "Братан, дай подумать...",
                "Сейчас сформулирую мысль...",
                "Держи ответ..."
            ]
        }
        
        # Ответы в режиме Гигачад
        gigachad_fallbacks = [
            "💪 СЛУШАЙ СЮДА! Думай сам — это лучшая прокачка!",
            "🚀 Нейросеть качается! Пока ждёшь — возьми книгу!",
            "🧠 Мозг должен работать! Задай вопрос ещё раз!",
            "🔥 Технические шоколадки! Используй паузу для роста!",
            "🏋️ Сервер на перекуре! Сделай 10 отжиманий!",
            "🎯 ИИ медитирует! Подумай над вопросом глубже!"
        ]
        
        # Выбираем ответ
        if gigachad_mode:
            return random.choice(gigachad_fallbacks)
        else:
            author_fallbacks = normal_fallbacks.get(author_key, normal_fallbacks["pushkin"])
            return random.choice(author_fallbacks)

# Инициализируем GigaChat клиент
gigachat = GigaChatAI(GIGACHAT_CREDENTIALS)

# ========== КЛАВИАТУРЫ ==========
def get_main_keyboard() -> InlineKeyboardMarkup:
    """Основная клавиатура выбора автора"""
    builder = InlineKeyboardBuilder()
    
    # Авторы в виде кнопок
    authors = [
        ("🖋️ Пушкин", "author_pushkin"),
        ("📚 Достоевский", "author_dostoevsky"),
        ("✍️ Толстой", "author_tolstoy"),
        ("👻 Гоголь", "author_gogol"),
        ("🏥 Чехов", "author_chekhov"),
        ("💪 ГИГАЧАД", "author_gigachad")
    ]
    
    for text, callback_data in authors:
        builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    
    builder.adjust(2)  # 2 кнопки в ряд
    
    # Кнопки управления
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")
    )
    
    return builder.as_markup()

def get_chat_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура во время диалога"""
    builder = InlineKeyboardBuilder()
    
    # Получаем данные пользователя
    user_data = db.get_user(user_id)
    gigachad_mode = user_data.get("gigachad_mode", False)
    
    # Основные кнопки
    buttons = [
        ("👥 Сменить автора", "change_author"),
        ("🔄 Новый диалог", "reset_chat"),
        ("📖 Об авторе", "about_author"),
        ("📋 Список авторов", "list_authors")
    ]
    
    for text, callback_data in buttons:
        builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    
    builder.adjust(2)  # 2 кнопки в ряд
    
    # Кнопка режима Гигачад
    if gigachad_mode:
        builder.row(
            InlineKeyboardButton(
                text="👑 Гигачад ВКЛ", 
                callback_data="toggle_gigachad"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="💪 Включить Гигачад", 
                callback_data="toggle_gigachad"
            )
        )
    
    # Кнопка возврата
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    
    return builder.as_markup()

def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        ("🗑️ Очистить историю", "clear_history"),
        ("📊 Моя статистика", "my_stats"),
        ("🔙 Назад", "main_menu")
    ]
    
    for text, callback_data in buttons:
        builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    
    builder.adjust(1)  # По одной кнопке в ряд
    
    return builder.as_markup()

# ========== ОБРАБОТЧИКИ КОМАНД ==========
router = Router()

@router.message(CommandStart())
async def command_start(message: Message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    
    # Сохраняем информацию о пользователе
    user_data = db.get_user(user_id)
    if "username" not in user_data:
        user_data["username"] = message.from_user.username
        user_data["first_name"] = message.from_user.first_name
        db.save_user(user_id, user_data)
    
    welcome_text = f"""
🎭 <b>Добро пожаловать в Литературный Диалог, {message.from_user.first_name}!</b>

📚 <b>Я могу представить любого из великих русских писателей:</b>
• Общайтесь с ними на любые темы
• Задавайте вопросы о творчестве и жизни
• Получайте ответы в уникальном стиле каждого автора

🔥 <b>НОВИНКА:</b> Режим <b>💪 ГИГАЧАД</b> — мотивационные ответы в стиле легенды!

👇 <b>Выберите собеседника:</b>
"""
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.HTML
    )
    
    logger.info(f"Новый пользователь: {user_id} (@{message.from_user.username})")

@router.message(Command("gigachad"))
async def command_gigachad(message: Message):
    """Быстрая команда для активации режима Гигачад"""
    user_id = message.from_user.id
    user_data = db.get_user(user_id)
    
    # Устанавливаем Гигачада как автора
    user_data["selected_author"] = "gigachad"
    user_data["gigachad_mode"] = True
    user_data["conversation_history"] = []
    db.save_user(user_id, user_data)
    
    response_text = f"""
💪 <b>РЕЖИМ ГИГАЧАД АКТИВИРОВАН, {message.from_user.first_name.upper()}!</b>

🚀 <b>Теперь ты общаешься с легендой мотивации!</b>

📖 <b>Задавай вопросы о:</b>
• Литературе и книгах
• Саморазвитии и дисциплине
• Жизни и философии
• Или просто получай мотивацию!

🔥 <b>Примеры:</b>
• "Как читать больше книг?"
• "В чём сила классической литературы?"
• "Как дисциплинировать себя?"
• "Что думают писатели о силе духа?"

<code>Не теряй время — задавай вопрос и получай прокачку! 💪</code>
"""
    
    await message.answer(
        response_text,
        reply_markup=get_chat_keyboard(user_id),
        parse_mode=ParseMode.HTML
    )
    
    logger.info(f"Активирован режим Гигачад: {user_id}")

@router.message(Command("help"))
async def command_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
📖 <b>ПОМОЩЬ И ИНСТРУКЦИИ</b>

<b>Основные команды:</b>
/start — Начать диалог, выбрать автора
/gigachad — Активировать режим 💪 ГИГАЧАД
/help — Эта справка
/stats — Статистика бота

<b>Как пользоваться:</b>
1. Выберите автора из списка
2. Задавайте любые вопросы
3. Получайте ответы в стиле выбранного писателя
4. Меняйте авторов в любое время

<b>Режим 💪 ГИГАЧАД:</b>
• Мотивационные ответы на литературные темы
• Можно активировать для любого автора
• Связывает классику с саморазвитием
• Коротко, уверенно, по делу

<b>Примеры вопросов:</b>
• "Расскажи о своём детстве"
• "Какое твоё самое известное произведение?"
• "Что ты думаешь о современной литературе?"
• "Как дисциплинировать себя для чтения?"

<b>Технологии:</b>
• GigaChat AI — российская нейросеть
• История диалога (10 последних сообщений)
• Индивидуальные стили для каждого автора

<code>Просто выбирай и общайся! Каждый диалог — это уникальный опыт. 📚</code>
"""
    
    await message.answer(help_text, parse_mode=ParseMode.HTML)

@router.message(Command("stats"))
async def command_stats(message: Message):
    """Обработчик команды /stats"""
    stats = db.get_global_stats()
    
    # Формируем текст статистики
    stats_text = f"""
📊 <b>СТАТИСТИКА БОТА</b>

👥 <b>Пользователей всего:</b> {stats['total_users']}
💬 <b>Всего сообщений:</b> {stats['total_messages']}
🎭 <b>Активных диалогов:</b> {stats['active_users']}

⚡ <b>GigaChat статус:</b> {"✅ Активен" if gigachat.available else "❌ Недоступен"}

<b>Популярность авторов:</b>
"""
    
    # Добавляем статистику по авторам
    author_stats = stats.get('author_stats', {})
    if author_stats:
        sorted_authors = sorted(author_stats.items(), key=lambda x: x[1], reverse=True)
        
        for author_key, count in sorted_authors[:5]:  # Топ-5 авторов
            author_names = {
                "pushkin": "🖋️ Пушкин",
                "dostoevsky": "📚 Достоевский",
                "tolstoy": "✍️ Толстой",
                "gogol": "👻 Гоголь",
                "chekhov": "🏥 Чехов",
                "gigachad": "💪 ГИГАЧАД"
            }
            author_name = author_names.get(author_key, author_key)
            stats_text += f"\n{author_name}: {count}"
    else:
        stats_text += "\n\n📭 Пока нет данных о популярности авторов"
    
    stats_text += f"\n\n<code>Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</code>"
    
    await message.answer(stats_text, parse_mode=ParseMode.HTML)

@router.message(Command("myprofile"))
async def command_myprofile(message: Message):
    """Личная статистика пользователя"""
    user_id = message.from_user.id
    user_data = db.get_user(user_id)
    
    author_names = {
        "pushkin": "Пушкин",
        "dostoevsky": "Достоевский",
        "tolstoy": "Толстой",
        "gogol": "Гоголь",
        "chekhov": "Чехов",
        "gigachad": "💪 ГИГАЧАД"
    }
    
    current_author = user_data.get("selected_author")
    author_name = author_names.get(current_author, "не выбран") if current_author else "не выбран"
    
    profile_text = f"""
👤 <b>ВАШ ПРОФИЛЬ</b>

<b>Имя:</b> {user_data.get('first_name', 'Не указано')}
<b>Username:</b> @{user_data.get('username', 'Не указан')}
<b>ID:</b> {user_id}

<b>Текущий автор:</b> {author_name}
<b>Режим Гигачад:</b> {"✅ ВКЛ" if user_data.get('gigachad_mode') else "❌ ВЫКЛ"}
<b>Сообщений отправлено:</b> {user_data.get('message_count', 0)}

<b>Дата регистрации:</b> {datetime.fromisoformat(user_data['created_at']).strftime('%d.%m.%Y')}
<b>Последняя активность:</b> {datetime.fromisoformat(user_data['last_active']).strftime('%d.%m.%Y %H:%M')}

<code>Продолжайте общение с великими умами! 🧠</code>
"""
    
    await message.answer(profile_text, parse_mode=ParseMode.HTML)

# ========== ОБРАБОТЧИКИ CALLBACK ==========
@router.callback_query(F.data.startswith("author_"))
async def callback_select_author(callback: CallbackQuery):
    """Выбор автора через inline-кнопку"""
    author_key = callback.data.split("_")[1]
    
    # Словарь с именами авторов
    author_names = {
        "pushkin": "Александр Пушкин",
        "dostoevsky": "Фёдор Достоевский",
        "tolstoy": "Лев Толстой",
        "gogol": "Николай Гоголь",
        "chekhov": "Антон Чехов",
        "gigachad": "💪 ГИГАЧАД"
    }
    
    author_name = author_names.get(author_key, "Неизвестный автор")
    
    # Получаем данные пользователя
    user_id = callback.from_user.id
    user_data = db.get_user(user_id)
    
    # Сохраняем выбор автора и очищаем историю
    user_data["selected_author"] = author_key
    user_data["conversation_history"] = []
    db.save_user(user_id, user_data)
    
    # Приветственные сообщения для каждого автора
    greetings = {
        "pushkin": f"Приветствую вас, {callback.from_user.first_name}! Перо моё готово, о чём поведаете?",
        "dostoevsky": f"Здравствуйте, {callback.from_user.first_name}. Что тревожит вашу душу сегодня?",
        "tolstoy": f"Здравствуйте, {callback.from_user.first_name}. Главное в жизни — правда. О чём вы хотите спросить?",
        "gogol": f"А, вот и вы, {callback.from_user.first_name}! Что привело вас в мой странный мир?",
        "chekhov": f"Здравствуйте, {callback.from_user.first_name}. Рассказывайте, я слушаю внимательно.",
        "gigachad": f"СЛУШАЙ СЮДА, {callback.from_user.first_name.upper()}! 💪\nТы выбрал ЛЕГЕНДУ! Задавай вопрос — получай МОТИВАЦИЮ!"
    }
    
    greeting = greetings.get(author_key, f"Рад нашей встрече, {callback.from_user.first_name}!")
    
    # Форматируем ответ в зависимости от автора
    if author_key == "gigachad":
        response_text = f"""
💪 <b>ВЫБРАН: {author_name}</b>

{greeting}

🔥 <b>ЗАДАВАЙ ВОПРОСЫ О:</b>
• Литературе и книгах
• Саморазвитии и силе духа
• Жизни и философии
• Всём, что делает тебя сильнее!

<code>Не теряй ни секунды — действуй! 🚀</code>
"""
    else:
        response_text = f"""
✅ <b>Ваш собеседник: {author_name}</b>

{greeting}

📝 <b>Можете спросить о:</b>
• Жизни и творчестве
• Философских взглядах
• Исторических событиях
• Или просто пообщаться

<code>Задавайте вопросы — я с удовольствием отвечу! ✨</code>
"""
    
    await callback.message.edit_text(
        response_text,
        reply_markup=get_chat_keyboard(user_id),
        parse_mode=ParseMode.HTML
    )
    
    await callback.answer(f"Выбран: {author_name}")
    logger.info(f"Пользователь {user_id} выбрал автора: {author_key}")

@router.callback_query(F.data == "change_author")
async def callback_change_author(callback: CallbackQuery):
    """Смена автора"""
    await callback.message.edit_text(
        "👥 <b>ВЫБЕРИТЕ НОВОГО АВТОРА</b>\n\n"
        "С кем хотите побеседовать теперь?",
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "reset_chat")
async def callback_reset_chat(callback: CallbackQuery):
    """Сброс истории диалога"""
    user_id = callback.from_user.id
    user_data = db.get_user(user_id)
    
    # Очищаем историю
    user_data["conversation_history"] = []
    db.save_user(user_id, user_data)
    
    current_
