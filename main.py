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
        # Ограничиваем историю 10 сообщениями
        if len(data["conversation_history"]) > 10:
            data["conversation_history"] = data["conversation_history"][-10:]
        self.save_user_data(user_id, data)

db = SimpleDatabase()

# ========== GIGACHAT КЛИЕНТ ==========
class GigaChatClient:
    def __init__(self):
        self.credentials = GIGACHAT_CREDENTIALS
        if not self.credentials:
            logger.warning("GIGACHAT_CREDENTIALS not set")
            self.available = False
            return
        try:
            # Отключаем SSL так как в Replit могут быть проблемы с сертификатами
            self.client = GigaChat(credentials=self.credentials, verify_ssl_certs=False)
            self.available = True
            logger.info("GigaChat client initialized")
        except Exception as e:
            logger.error(f"GigaChat init error: {e}")
            self.available = False
    
    def _get_author_prompt(self, author_key: str) -> str:
        prompts = {
            "pushkin": "Ты — Александр Пушкин, великий русский поэт. Твой стиль изящен, ты используешь лексику XIX века, обращаешься к собеседнику 'милый друг' или 'государь'. Пиши короткими, но емкими фразами, иногда вставляй стихотворные обороты.",
            "dostoevsky": "Ты — Фёдор Достоевский, глубокий психолог и философ. Ты рассуждаешь о душе, страдании, Петербурге и морали. Твой стиль серьезен, местами тревожен, но всегда глубок. Ты задаешь встречные вопросы о смысле жизни.",
            "tolstoy": "Ты — Лев Толстой, мудрый старец из Ясной Поляны. Ты ценишь простоту, труд, семью и искренность. Твой стиль назидателен, но добр. Ты рассуждаешь о том, как человеку жить в правде."
        }
        return prompts.get(author_key, "Ты — великий русский писатель.")
    
    async def generate_response(self, author_key: str, user_message: str) -> str:
        if not self.available:
            return "Извините, сейчас я не могу поддержать беседу..."
            
        try:
            system_prompt = self._get_author_prompt(author_key)
            # Формируем запрос
            prompt_full = f"{system_prompt}\n\nСобеседник: {user_message}\nПисатель:"
            
            # GigaChat API call (sync wrapped in async if needed, but gigachat lib is often sync)
            # Using run_in_executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: self.client.chat(prompt_full)
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"GigaChat gen error: {e}")
            return "Мои мысли сейчас заняты другим произведением. Давайте поговорим позже."

gigachat_client = GigaChatClient()

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
        ("🔄 Сбросить чат", "reset_chat"),
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
        "📚 <b>Добро пожаловать в Литературный Салон!</b>\n\nЗдесь вы можете побеседовать с великими русскими писателями. С кем начнем разговор?",
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
        "pushkin": "Приветствую вас, мой друг! Перо моё готово, о чём поведаете?",
        "dostoevsky": "Слушаю вас внимательно. Всякая душа — потемки, но давайте попробуем заглянуть в них.",
        "tolstoy": "Здравствуйте. Главное в жизни — правда. О чем вы хотите спросить?"
    }
    
    await callback.message.edit_text(
        f"✅ <b>Ваш собеседник: {author_name}</b>\n\n{greetings.get(author_key, 'Рад беседе!')}",
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
        await message.answer("⚠️ Пожалуйста, сначала выберите писателя через /start")
        return
    
    author_name = {
        "pushkin": "Пушкин",
        "dostoevsky": "Достоевский",
        "tolstoy": "Толстой"
    }.get(author_key, "Писатель")
    
    status_msg = await message.answer(f"✍️ <i>{author_name} пишет...</i>", parse_mode=ParseMode.HTML)
    
    response = await gigachat_client.generate_response(author_key, message.text)
    
    db.update_conversation(user_id, author_key, message.text, response)
    
    await status_msg.delete()
    await message.answer(f"<b>{author_name}:</b>\n\n{response}", parse_mode=ParseMode.HTML)
    
    await asyncio.sleep(0.5)
    await message.answer("💬 Продолжим?", reply_markup=get_chat_keyboard())

@router.callback_query(F.data == "change_author")
async def change_author(callback: CallbackQuery):
    await callback.message.edit_text(
        "👥 <b>Выберите нового собеседника:</b>",
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
    await callback.message.answer("🔄 История очищена. Начнем с чистого листа!")
    await callback.answer()

@router.callback_query(F.data == "help")
async def help_cmd(callback: CallbackQuery):
    await callback.message.answer(
        "📝 <b>Помощь:</b>\n\n- Используйте /start для начала\n- Выберите писателя и пишите ему любые вопросы\n- Вы можете сменить автора в любой момент",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    
    logger.info("🚀 Бот запущен (GigaChat)")
    # Удаляем вебхук перед запуском polling для избежания конфликтов
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
