import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
import json
import os
from datetime import datetime
import google.generativeai as genai

# ========== КОНФИГУРАЦИЯ ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

from config import BOT_TOKEN, GEMINI_API_KEY

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
            except:
                pass
        return {
            "user_id": user_id,
            "selected_author": None,
            "conversation_history": [],
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
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        data["conversation_history"].append({
            "role": "assistant",
            "content": bot_response,
            "timestamp": datetime.now().isoformat()
        })
        if len(data["conversation_history"]) > 10:
            data["conversation_history"] = data["conversation_history"][-10:]
        self.save_user_data(user_id, data)

db = SimpleDatabase()

# ========== GEMINI КЛИЕНТ ==========
class GeminiClient:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        if not self.api_key or self.api_key == "ваш_ключ_gemini":
            print("⚠️ GEMINI_API_KEY не найден, используется заглушка")
            self.available = False
            return
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            self.available = True
            print("✅ Gemini клиент инициализирован")
        except Exception as e:
            print(f"❌ Ошибка Gemini: {e}")
            self.available = False
    
    def _get_author_prompt(self, author_key: str) -> str:
        prompts = {
            "pushkin": """Ты — Александр Пушкин. Отвечай как поэт 19 века.
Говори о: детстве в Москве, Лицее, Наталье Гончаровой, дуэли.
Избегай фраз "Ах, этот вопрос!".""",
            "dostoevsky": """Ты — Фёдор Достоевский. Говори как философ.
Темы: Петербург, каторга, эпилепсия, "Преступление и наказание".
Не говори шаблонных фраз.""",
            "tolstoy": """Ты — Лев Толстой. Говори мудро и просто.
Темы: Ясная Поляна, "Война и мир", вегетарианство, уход из дома."""
        }
        return prompts.get(author_key, f"Ты — писатель. Отвечай от своего лица.")
    
    async def generate_response(self, author_key: str, user_message: str) -> str:
        if not self.available:
            return self._get_fallback_response(author_key)
        try:
            prompt = f"{self._get_author_prompt(author_key)}\n\nВопрос: {user_message}\nОтвет:"
            response = self.model.generate_content(prompt)
            return response.text.strip() if response.text else self._get_fallback_response(author_key)
        except Exception as e:
            print(f"❌ Ошибка Gemini: {e}")
            return self._get_fallback_response(author_key)
    
    def _get_fallback_response(self, author_key: str) -> str:
        responses = {
            "pushkin": "Мой друг, о чём бы вы хотели побеседовать?",
            "dostoevsky": "Что тревожит вашу душу? Расскажите.",
            "tolstoy": "Друг мой, жизнь проста. О чём поговорим?"
        }
        return responses.get(author_key, "Интересный вопрос. Что ещё хотите узнать?")

gemini_client = GeminiClient()

# ========== КЛАВИАТУРЫ ==========
def get_authors_keyboard():
    builder = InlineKeyboardBuilder()
    authors = [
        ("🖋️ Пушкин", "pushkin"),
        ("📚 Достоевский", "dostoevsky"),
        ("✍️ Толстой", "tolstoy")
    ]
    for text, data in authors:
        builder.add(InlineKeyboardButton(text=text, callback_data=f"author_{data}"))
    builder.adjust(2)
    return builder.as_markup()

def get_chat_keyboard():
    builder = InlineKeyboardBuilder()
    buttons = [
        ("👥 Сменить автора", "change_author"),
        ("🔄 Новый диалог", "reset_chat"),
        ("ℹ️ О писателе", "about_author"),
        ("❓ Помощь", "help")
    ]
    for text, data in buttons:
        builder.add(InlineKeyboardButton(text=text, callback_data=data))
    builder.adjust(2)
    return builder.as_markup()

# ========== ОБРАБОТЧИКИ ==========
router = Router()

@router.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "📚 <b>Литературный Диалог</b>\n\nВыберите писателя:",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data.startswith("author_"))
async def select_author(callback: CallbackQuery):
    author_key = callback.data.split("_")[1]
    authors_names = {
        "pushkin": "Александр Пушкин",
        "dostoevsky": "Фёдор Достоевский",
        "tolstoy": "Лев Толстой"
    }
    author_name = authors_names.get(author_key, "Писатель")
    
    user_id = callback.from_user.id
    data = db.get_user_data(user_id)
    data["selected_author"] = author_key
    db.save_user_data(user_id, data)
    
    greetings = {
        "pushkin": "Друзья мои, прекрасен наш союз! О чём побеседуем?",
        "dostoevsky": "Здравствуйте. Что тревожит вашу душу?",
        "tolstoy": "Здравствуйте, друг мой. О чём поговорим?"
    }
    
    await callback.message.edit_text(
        f"✅ <b>Вы выбрали: {author_name}</b>\n\n{greetings.get(author_key, 'Рад беседе!')}",
        reply_markup=get_chat_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.message(F.text)
async def handle_message(message: Message):
    user_id = message.from_user.id
    user_data = db.get_user_data(user_id)
    author_key = user_data.get("selected_author")
    
    if not author_key:
        await message.answer("⚠️ Сначала выберите писателя через /start")
        return
    
    authors_names = {
        "pushkin": "Александр Пушкин",
        "dostoevsky": "Фёдор Достоевский", 
        "tolstoy": "Лев Толстой"
    }
    author_name = authors_names.get(author_key, "Писатель")
    
    # Показываем "печатает"
    typing_msg = await message.answer(f"✍️ <i>{author_name} думает...</i>", parse_mode=ParseMode.HTML)
    
    # Генерируем ответ
    response = await gemini_client.generate_response(author_key, message.text)
    
    # Обновляем историю
    db.update_conversation(user_id, author_key, message.text, response)
    
    # Удаляем "печатает"
    await typing_msg.delete()
    
    # 1. Ответ персонажа
    await message.answer(
        f"<b>{author_name}:</b>\n\n{response}",
        parse_mode=ParseMode.HTML,
        reply_markup=None
    )
    
    # 2. Кнопки управления
    await asyncio.sleep(0.3)
    await message.answer(
        "👇 <b>Что дальше?</b>",
        reply_markup=get_chat_keyboard(),
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data == "change_author")
async def change_author(callback: CallbackQuery):
    await callback.message.edit_text(
        "👥 <b>Выберите писателя:</b>",
        reply_markup=get_authors_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

@router.callback_query(F.data == "reset_chat")
async def reset_chat(callback: CallbackQuery):
    user_id = callback.from_user.id
    data = db.get_user_data(user_id)
    data["conversation_history"] = []
    db.save_user_data(user_id, data)
    
    await callback.message.answer(
        "🔄 <b>Диалог сброшен!</b>\nЗадавайте новые вопросы.",
        reply_markup=get_chat_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# ========== ЗАПУСК БОТА ==========
async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    
    logger.info("🚀 ЗАПУСК ЛИТЕРАТУРНОГО БОТА")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
