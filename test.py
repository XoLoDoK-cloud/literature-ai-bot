import sys
try:
    from aiogram import Bot, Dispatcher
    print("✅ aiogram установлен")
except ImportError as e:
    print(f"❌ aiogram не установлен: {e}")
    print("Установите: pip install aiogram")
