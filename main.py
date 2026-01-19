import asyncio
import logging
import sys
import json
import os
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from gigachat import GigaChat

# ========== КОНФИГУРАЦИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

from config import BOT_TOKEN, GIGACHAT_CREDENTIALS

# ========== БАЗА ДАННЫХ ==========
class SimpleDatabase:
    def __init__(self):
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _get_user_file(self, user_id: int) -> str:
        return os.path.join(self.data_dir, f"user_{user_id}.json")
    
    def get_user_data(self, user_id: int) -> dict:
        file_path = self._get_user_file(user_id)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading DB: {e}")
        return {
            "user_id": user_id,
            "selected_author": None,
            "conversation_history": [],
            "gigachad_mode": False,
            "message_count": 0,
            "created_at": datetime.now().isoformat()
        }
    
    def save_user_data(self, user_id: int, data: dict):
        file_path = self._get_user_file(user_id)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def update_conversation(self, user_id: int, author_key: str, user_message: str, bot_response: str):
        data = self.get_user_data(user_id)
        data["selected_author"] = author_key
        data["conversation_history"].append({
            "role": "user",
            "content": user_message
        })
        data["conversation_history"].append({
            "role": "assistant",
            "content": bot_response
        })
        data["message_count"] = data.get("message_count", 0) + 1
        
        # Ограничиваем историю
        if len(data["conversation_history"]) > 10:
            data["conversation_history"] = data["conversation_history"][-10:]
        
        self.save_user_data(user_id, data)

db = SimpleDatabase()

# ========== GIGACHAT КЛИЕНТ ==========
class GigaChatClient:
    def __init__(self):
        self.credentials = GIGACHAT_CREDENTIALS
        if not self.credentials:
            logger.warning("GIGACHAT_CREDENTIALS не задан!")
            self.available = False
            return
        try:
            self.client = GigaChat(credentials=self.credentials, verify_ssl_certs=False)
            self.available = True
            logger.info("✅ GigaChat клиент инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка GigaChat: {e}")
            self.available = False
    
    def _get_author_prompt(self, author_key: str, gigachad_mode: bool = False) -> str:
        """Получение промпта для автора"""
        
        # Базовые промпты авторов
        author_prompts = {
            "pushkin": {
                "normal": "Ты — Александр Сергеевич Пушкин (1799-1837). Твой стиль изящный, остроумный, иногда ироничный. Отвечай кратко (2-4 предложения), используя лексику XIX века. Примеры твоих фраз: 'Мой друг...', 'Что пройдет, то будет мило...'",
                "gigachad": "Ты — Пушкин в режиме ГИГАЧАД! Говори уверенно, мотивирующе, связывай поэзию с саморазвитием. Пример: 'Рифмы — как мышцы, нужно качать каждый день. Читай утром, твори вечером, будь легендой!'"
            },
            "dostoevsky": {
                "normal": "Ты — Фёдор Михайлович Достоевский (1821-1881). Твой стиль глубокий, философский, психологичный. Говори о душе, страдании, вере. Отвечай кратко, но содержательно.",
                "gigachad": "Ты — Достоевский в режиме ГИГАЧАД! Превращай философию в мотивацию. Пример: 'Страдание закаляет душу как сталь. Каждая проблема — шанс стать сильнее. Не бойся глубины — ныряй!'"
            },
            "tolstoy": {
                "normal": "Ты — Лев Николаевич Толстой (1828-1910). Твой стиль мудрый, простой, назидательный. Говори о жизни, правде, нравственности. Используй притчи.",
                "gigachad": "Ты — Толстой в режиме ГИГАЧАД! Превращай мудрость в действие. Пример: 'Простота — сила. Не говори о правде — живи в ней. Каждый день — новая глава твоей жизни!'"
            },
            "gogol": {
                "normal": "Ты — Николай Васильевич Гоголь (1809-1852). Твой стиль яркий, ироничный, с мистикой. Отвечай с юмором и образностью.",
                "gigachad": "Ты — Гоголь в режиме ГИГАЧАД! Превращай сатиру в мотивацию. Пример: 'Чиновники в голове мешают? Вымети их как мёртвые души! Каждая странность — твоя особенность!'"
            },
            "chekhov": {
                "normal": "Ты — Антон Павлович Чехов (1860-1904). Твой стиль лаконичный, точный, ироничный. 'Краткость — сестра таланта'. Отвечай 2-3 предложениями.",
                "gigachad": "Ты — Чехов в режиме ГИГАЧАД! Лаконично и мощно. Пример: 'В человеке всё должно быть прекрасно. Особенно дисциплина. Читай меньше слов, делай больше дел!'"
            },
            "gigachad": {
                "normal": "Ты — ГИГАЧАД, легендарный мотивационный тренер! Отвечай КОРОТКО (2-3 предложения), УВЕРЕННО, с МОТИВАЦИЕЙ. Связывай литературу с реальной жизнью. Примеры: 'Книги — качалка для мозга. Читай каждый день как делаешь подходы в зале!'",
                "gigachad": "Ты — ГИГАЧАД в режиме ГИГАЧАД (да, это мета)! Супер-мотивация, максимальная уверенность. Ломай стереотипы о литературе. Пример: 'Пушкин был бы в зале, если бы жил сейчас. Классика + качалка = легенда!'"
            }
        }
        
        # Получаем промпт
        author_info = author_prompts.get(author_key, author_prompts["pushkin"])
        mode = "gigachad" if gigachad_mode else "normal"
        return author_info.get(mode, author_info["normal"])
    
    async def generate_response(self, author_key: str, user_message: str, user_id: int) -> str:
        """Генерация ответа через GigaChat"""
        if not self.available:
            return "⚠️ Сервис временно недоступен. Попробуйте позже."
        
        try:
            # Получаем данные пользователя
            user_data = db.get_user_data(user_id)
            gigachad_mode = user_data.get("gigachad_mode", False)
            
            # Формируем полный промпт с историей
            system_prompt = self._get_author_prompt(author_key, gigachad_mode)
            
            # Добавляем историю диалога
            history = user_data.get("conversation_history", [])
            prompt_parts = [system_prompt]
            
            if history:
                prompt_parts.append("\nПредыдущий диалог:")
                for msg in history[-4:]:  # Последние 4 сообщения
                    role = "Читатель" if msg["role"] == "user" else "Писатель"
                    prompt_parts.append(f"{role}: {msg['content']}")
            
            prompt_parts.append(f"\nЧитатель: {user_message}")
            prompt_parts.append("Писатель:")
            
            prompt_full = "\n".join(prompt_parts)
            
            # Генерируем ответ
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.client.chat(prompt_full)
            )
            
            result = response.choices[0].message.content.strip()
            
            # Сохраняем в историю
            db.update_conversation(user_id, author_key, user_message, result)
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации: {e}")
            
            # Fallback ответы в стиле Гигачада
            fallbacks = [
                "Братан, нейросеть на перекуре! Пока ждёшь — возьми книгу! 📚",
                "Серверы качаются. Используй время для саморазвития! 💪",
                "Технические шоколадки. Думай сам — это лучшая прокачка! 🧠",
                "ИИ в медитации. Задай вопрос ещё раз мощнее! 🔥"
            ]
            import random
            return random.choice(fallbacks)

gigachat_client = GigaChatClient()

# ========== КЛАВИАТУРЫ ==========
def get_authors_keyboard(include_gigachad: bool = True):
    """Клавиатура выбора автора"""
    builder = InlineKeyboardBuilder()
    
    authors = [
        ("🖋️ Пушкин", "author_pushkin"),
        ("📚 Достоевский", "author_dostoevsky"),
        ("✍️ Толстой", "author_tolstoy"),
        ("👻 Гоголь", "author_gogol"),
        ("🏥 Чехов", "author_chekhov")
    ]
    
    for text, data in authors:
        builder.add(InlineKeyboardButton(text=text, callback_data=data))
    
    if include_gigachad:
        builder.add(InlineKeyboardButton(
            text="💪 ГИГАЧАД", 
            callback_data="author_gigachad"
        ))
    
    builder.adjust(3)
    
    # Добавляем кнопки управления
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
    )
    
    return builder.as_markup()

def get_chat_keyboard(user_id: int = None):
    """Клавиатура во время диалога"""
    builder = InlineKeyboardBuilder()
    
    # Получаем режим пользователя
    gigachad_mode = False
    if user_id:
        user_data = db.get_user_data(user_id)
        gigachad_mode = user_data.get("gigachad_mode", False)
    
    # Основные кнопки
    buttons = [
        ("👥 Сменить автора", "change_author"),
        ("🔄 Сбросить чат", "reset_chat"),
        ("ℹ️ Об авторе", "about_author"),
        ("📋 Список", "list_authors")
    ]
    
    for text, data in buttons:
        builder.add(InlineKeyboardButton(text=text, callback_data=data))
    
    builder.adjust(2)
    
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
    
    return builder.as_markup()

# ========== ОБРАБОТЧИКИ ==========
router = Router()

@router.message(CommandStart())
async def start_cmd(message: Message):
    """Команда /start"""
    await message.answer(
        "🚀 <b>ЛИТЕРАТУРНЫЙ БОТ v2.0</b>\n\n"
        "<i>Говори с классиками на одном языке!</i>\n\n"
        "📚 <b>Доступные авторы:</b>\n"
        "• 5 русских классиков\n"
        "• Режим 💪 <b>ГИГАЧАД</b> (мотивация + литература)\n"
        "• GigaChat AI вместо Gemini\n\n"
        "👇 <b>Выберите собеседника:</b>",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("gigachad"))
async def gigachad_cmd(message: Message):
    """Быстрая команда для Гигачада"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    user_data["selected_author"] = "gigachad"
    user_data["gigachad_mode"] = True
    user_data["conversation_history"] = []
    db.save_user_data(user_id, user_data)
    
    await message.answer(
        "💪 <b>РЕЖИМ ГИГАЧАД АКТИВИРОВАН!</b>\n\n"
        "<i>Мотивация + литература = легенда!</i>\n\n"
        "🔥 <b>Примеры вопросов:</b>\n"
        "• Как читать больше книг?\n"
        "• В чём сила классики?\n"
        "• Как дисциплинировать себя?\n"
        "• Что Пушкин думал бы о качалке?\n\n"
        "<code>Задавай вопрос — получай мотивацию! 🚀</code>",
        reply_markup=get_chat_keyboard(user_id),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("help"))
async def help_cmd(message: Message):
    """Команда /help"""
    await message.answer(
        "📖 <b>ПОМОЩЬ ПО БОТУ</b>\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Выбор автора\n"
        "/gigachad - Режим Гигачада\n"
        "/help - Эта справка\n"
        "/stats - Статистика\n\n"
        "<b>Режим 💪 ГИГАЧАД:</b>\n"
        "• Мотивационные ответы\n"
        "• Связь литературы с жизнью\n"
        "• Коротко, уверенно, по делу\n\n"
        "<b>Пример вопроса Гигачаду:</b>\n"
        "<i>«Как Достоевский поможет в бизнесе?»</i>\n\n"
        "<code>Просто выбери автора и пиши! 🎯</code>",
        parse_mode=ParseMode.HTML
    )

@router.message(Command("stats"))
async def stats_cmd(message: Message):
    """Статистика бота"""
    # Считаем общую статистику
    total_files = len([f for f in os.listdir("data") if f.startswith("user_")])
    total_messages = 0
    
    for filename in os.listdir("data"):
        if filename.startswith("user_"):
            try:
                with open(os.path.join("data", filename), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    total_messages += data.get("message_count", 0)
            except:
                pass
    
    await message.answer(
        f"📊 <b>СТАТИСТИКА БОТА</b>\n\n"
        f"👥 Пользователей: <b>{total_files}</b>\n"
        f"💬 Сообщений: <b>{total_messages}</b>\n"
        f"🤖 Авторов: <b>6</b> (5 классиков + Гигачад)\n"
        f"⚡ GigaChat: <b>{"✅" if gigachat_client.available else "❌"}</b>\n\n"
        f"<code>Бот работает на GigaChat AI</code>",
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data.startswith("author_"))
async def select_author(callback: CallbackQuery):
    """Выбор автора"""
    author_key = callback.data.split("_")[1]
    
    authors_names = {
        "pushkin": "Александр Пушкин",
        "dostoevsky": "Фёдор Достоевский",
        "tolstoy": "Лев Толстой",
        "gogol": "Николай Гоголь",
        "chekhov": "Антон Чехов",
        "gigachad": "💪 ГИГАЧАД"
    }
    
    author_name = authors_names.get(author_key, "Писатель")
    
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    user_data["selected_author"] = author_key
    user_data["conversation_history"] = []  # Очищаем историю при смене автора
    db.save_user_data(user_id, user_data)
    
    # Приветствия
    greetings = {
        "pushkin": "Приветствую вас, мой друг! О чём желаете побеседовать?",
        "dostoevsky": "Здравствуйте. Что тревожит вашу душу сегодня?",
        "tolstoy": "Здравствуйте. Говорите правду — я слушаю.",
        "gogol": "А, вот и вы! Что привело вас в мой мир?",
        "chekhov": "Здравствуйте. Рассказывайте, я слушаю.",
        "gigachad": f"СЛУШАЙ СЮДА, {callback.from_user.first_name.upper()}! 💪\nЗадавай вопрос — получай мотивацию. Что на уме?"
    }
    
    greeting = greetings.get(author_key, "Рад нашей беседе!")
    
    # Разный формат для Гигачада
    if author_key == "gigachad":
        await callback.message.edit_text(
            f"💪 <b>ВЫБРАН: {author_name}</b>\n\n"
            f"{greeting}\n\n"
            f"<b>🔥 ЗАДАВАЙ:</b>\n"
            f"• Вопросы о литературе\n"
            f"• Вопросы о саморазвитии\n"
            f"• Всё, что волнует\n\n"
            f"<code>Не теряй время — действуй! 🚀</code>",
            reply_markup=get_chat_keyboard(user_id),
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.message.edit_text(
            f"✅ <b>Ваш собеседник: {author_name}</b>\n\n"
            f"{greeting}\n\n"
            f"<i>Задавайте любые вопросы:</i>",
            reply_markup=get_chat_keyboard(user_id),
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()

@router.message(F.text)
async def handle_message(message: Message):
    """Обработка текстовых сообщений"""
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    author_key = user_data.get("selected_author")
    
    if not author_key:
        await message.answer(
            "⚠️ <b>Сначала выберите писателя!</b>\n\n"
            "Используйте /start для выбора автора.",
            reply_markup=get_authors_keyboard()
        )
        return
    
    author_names = {
        "pushkin": "Пушкин",
        "dostoevsky": "Достоевский",
        "tolstoy": "Толстой",
        "gogol": "Гоголь",
        "chekhov": "Чехов",
        "gigachad": "💪 ГИГАЧАД"
    }
    
    author_name = author_names.get(author_key, "Писатель")
    
    # Статус "печатает"
    status_text = f"✍️ {author_name} обдумывает..."
    if author_key == "gigachad" or user_data.get("gigachad_mode"):
        status_text = f"💪 {author_name} качает ответ..."
    
    status_msg = await message.answer(f"<i>{status_text}</i>", parse_mode=ParseMode.HTML)
    
    # Генерируем ответ
    response = await gigachat_client.generate_response(author_key, message.text, user_id)
    
    # Удаляем статус
    await status_msg.delete()
    
    # Отправляем ответ
    if author_key == "gigachad" or user_data.get("gigachad_mode"):
        await message.answer(
            f"<b>💪 {author_name}:</b>\n\n"
            f"{response}\n\n"
            f"<i>Следующий вопрос? Жги! 🔥</i>",
            reply_markup=get_chat_keyboard(user_id),
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer(
            f"<b>{author_name}:</b>\n\n"
            f"{response}\n\n"
            f"<i>Продолжим беседу?</i>",
            reply_markup=get_chat_keyboard(user_id),
            parse_mode=ParseMode.HTML
        )

@router.callback_query(F.data == "change_author")
async def change_author(callback: CallbackQuery):
    """Смена автора"""
    await callback.message.edit_text(
        "👥 <b>ВЫБЕРИТЕ НОВОГО АВТОРА:</b>\n\n"
        "С кем хотите поговорить?",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "reset_chat")
async def reset_chat(callback: CallbackQuery):
    """Сброс диалога"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    user_data["conversation_history"] = []
    db.save_user_data(user_id, user_data)
    
    await callback.message.answer("🔄 <b>История очищена!</b>\nНачнём с чистого листа!", parse_mode=ParseMode.HTML)
    await callback.answer()

@router.callback_query(F.data == "toggle_gigachad")
async def toggle_gigachad(callback: CallbackQuery):
    """Переключение режима Гигачад"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    
    current_mode = user_data.get("gigachad_mode", False)
    user_data["gigachad_mode"] = not current_mode
    db.save_user_data(user_id, user_data)
    
    if not current_mode:
        await callback.message.answer(
            "👑 <b>РЕЖИМ ГИГАЧАД ВКЛЮЧЁН!</b>\n\n"
            "Теперь все ответы будут:\n"
            "• Мотивационные\n• Уверенные\n• Связь с жизнью\n\n"
            "<code>Задавай вопрос — получишь прокачку! 💪</code>",
            parse_mode=ParseMode.HTML
        )
    else:
        await callback.message.answer(
            "👌 <b>Режим Гигачад отключён</b>\n\n"
            "Возвращаемся к обычному стилю общения.",
            parse_mode=ParseMode.HTML
        )
    
    await callback.answer()

@router.callback_query(F.data == "about_author")
async def about_author(callback: CallbackQuery):
    """Информация об авторе"""
    user_id = callback.from_user.id
    user_data = db.get_user_data(user_id)
    author_key = user_data.get("selected_author")
    
    if not author_key:
        await callback.answer("Сначала выберите автора")
        return
    
    author_info = {
        "pushkin": "Александр Пушкин (1799-1837)\nВеликий русский поэт. Автор 'Евгения Онегина', 'Капитанской дочки'.",
        "dostoevsky": "Фёдор Достоевский (1821-1881)\nФилософ и писатель. Автор 'Преступления и наказания', 'Братьев Карамазовых'.",
        "tolstoy": "Лев Толстой (1828-1910)\nМыслитель и писатель. Автор 'Войны и мира', 'Анны Карениной'.",
        "gogol": "Николай Гоголь (1809-1852)\nМастер сатиры и мистики. Автор 'Мёртвых душ', 'Ревизора'.",
        "chekhov": "Антон Чехов (1860-1904)\nМастер короткой прозы и драматург. 'Краткость — сестра таланта'.",
        "gigachad": "💪 ГИГАЧАД\nМотивационный литературный эксперт. Связывает классику с саморазвитием и реальной жизнью."
    }
    
    await callback.message.answer(
        f"<b>📖 Об авторе:</b>\n\n{author_info.get(author_key, 'Информация об авторе')}",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "list_authors")
async def list_authors(callback: CallbackQuery):
    """Список авторов"""
    await callback.message.answer(
        "📚 <b>ДОСТУПНЫЕ АВТОРЫ:</b>\n\n"
        "🖋️ Александр Пушкин\n"
        "📚 Фёдор Достоевский\n"
        "✍️ Лев Толстой\n"
        "👻 Николай Гоголь\n"
        "🏥 Антон Чехов\n"
        "💪 ГИГАЧАД (мотивация)\n\n"
        "👇 Выберите:",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery):
    """Помощь через callback"""
    await help_cmd(callback.message)
    await callback.answer()

@router.callback_query(F.data == "stats")
async def stats_callback(callback: CallbackQuery):
    """Статистика через callback"""
    await stats_cmd(callback.message)
    await callback.answer()

async def main():
    """Основная функция запуска"""
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    
    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК ЛИТЕРАТУРНОГО БОТА")
    logger.info(f"🤖 Токен бота: {BOT_TOKEN[:10]}...")
    logger.info(f"🔑 GigaChat: {'✅' if gigachat_client.available else '❌'}")
    logger.info(f"📁 База данных: data/")
    logger.info("=" * 50)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"\n❌ Критическая ошибка: {e}")
