"""
Пакет services - содержит все сервисы для бота
"""

from .database import db
from .gigachat_client import gigachat_client
from .knowledge_base import search_in_knowledge, get_writer_knowledge
from .inline_keyboards import (
    get_authors_keyboard,
    get_chat_keyboard,
    get_main_menu_keyboard,
    get_compact_authors_keyboard
)
from .achievements import achievements_service
from .book_recommendations import book_recommendations
from .context_analyzer import context_analyzer
from .daily_quotes import daily_quotes
from .quiz_service import quiz_service
from .statistics import stats_service
from .timeline_service import timeline_service

__all__ = [
    'db',
    'gigachat_client',
    'search_in_knowledge',
    'get_writer_knowledge',
    'get_authors_keyboard',
    'get_chat_keyboard',
    'get_main_menu_keyboard',
    'get_compact_authors_keyboard',
    'achievements_service',
    'book_recommendations',
    'context_analyzer',
    'daily_quotes',
    'quiz_service',
    'stats_service',
    'timeline_service'
]
