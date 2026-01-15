import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Конфигурация
from config import BOT_TOKEN

# Импорт обработчиков - ВАЖНО: правильное написание!
from handlers.start_handler import router as start_router
from handlers.author_handler import router as author_router
from handlers.chat_handler import router as chat_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция запуска бота"""
    
    # Проверяем наличие токена
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN не найден!")
        return
    
    # Инициализация бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Хранилище состояний
    storage = MemoryStorage()
    
    # Инициализация диспетчера
    dp = Dispatcher(storage=storage)
    
    # Регистрация роутеров
    dp.include_router(start_router)
    dp.include_router(author_router)
    dp.include_router(chat_router)
    
    # Логирование запуска
    logger.info("=" * 50)
    logger.info("🚀 ЗАПУСК ЛИТЕРАТУРНОГО БОТА")
    logger.info("=" * 50)
    
    try:
        # Запуск поллинга
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
    finally:
        await bot.session.close()
        logger.info("⏹️ Бот остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹️ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"\n❌ Непредвиденная ошибка: {e}")
