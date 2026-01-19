from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_quiz_start_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для начала викторины"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🎯 Легкая викторина", callback_data="quiz_easy"),
        InlineKeyboardButton(text="🧠 Средняя викторина", callback_data="quiz_medium")
    )
    
    builder.row(
        InlineKeyboardButton(text="🏆 Сложная викторина", callback_data="quiz_hard"),
        InlineKeyboardButton(text="🎲 Случайная викторина", callback_data="quiz_random")
    )
    
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"))
    
    return builder.as_markup()

def get_quiz_question_keyboard(options: list) -> InlineKeyboardMarkup:
    """Клавиатура с вариантами ответов"""
    builder = InlineKeyboardBuilder()
    
    for i, option in enumerate(options):
        builder.row(InlineKeyboardButton(
            text=f"{i+1}. {option}",
            callback_data=f"quiz_answer_{i}"
        ))
    
    builder.row(InlineKeyboardButton(text="⏹️ Завершить викторину", callback_data="quiz_stop"))
    
    return builder.as_markup()
