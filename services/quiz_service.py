import random
import json
import os
from typing import Dict, List, Tuple
from datetime import datetime

class QuizService:
    """Сервис литературных викторин"""
    
    def __init__(self, quiz_file: str = "data/quiz_questions.json"):
        self.quiz_file = quiz_file
        self._ensure_quiz_file()
        self.questions = self._load_questions()
        self.user_sessions = {}  # user_id: {current_question, score, etc}
    
    def _ensure_quiz_file(self):
        """Создает файл с вопросами если его нет"""
        if not os.path.exists(self.quiz_file):
            default_questions = [
                {
                    "question": "Кто автор романа 'Евгений Онегин'?",
                    "options": ["Александр Пушкин", "Лев Толстой", "Фёдор Достоевский", "Николай Гоголь"],
                    "correct": 0,
                    "difficulty": "easy",
                    "author": "pushkin"
                },
                {
                    "question": "В каком году родился Лев Толстой?",
                    "options": ["1799", "1821", "1828", "1809"],
                    "correct": 2,
                    "difficulty": "medium",
                    "author": "tolstoy"
                },
                {
                    "question": "Какое произведение написал Фёдор Достоевский?",
                    "options": ["Война и мир", "Мёртвые души", "Преступление и наказание", "Вишнёвый сад"],
                    "correct": 2,
                    "difficulty": "easy",
                    "author": "dostoevsky"
                },
                {
                    "question": "Как звали жену Александра Пушкина?",
                    "options": ["Софья Андреевна", "Наталья Гончарова", "Анна Сниткина", "Мария Исаева"],
                    "correct": 1,
                    "difficulty": "hard",
                    "author": "pushkin"
                },
                {
                    "question": "Сколько томов планировалось в 'Мёртвых душах' Гоголя?",
                    "options": ["1", "2", "3", "4"],
                    "correct": 2,
                    "difficulty": "hard",
                    "author": "gogol"
                },
                {
                    "question": "Какой врач был Антон Чехов по профессии?",
                    "options": ["Хирург", "Терапевт", "Психиатр", "Педиатр"],
                    "correct": 1,
                    "difficulty": "medium",
                    "author": "chekhov"
                },
                {
                    "question": "Что говорил Гигачад о чтении книг?",
                    "options": ["Это скучно", "Это качалка для мозга", "Трата времени", "Для слабаков"],
                    "correct": 1,
                    "difficulty": "easy",
                    "author": "gigachad"
                }
            ]
            os.makedirs(os.path.dirname(self.quiz_file), exist_ok=True)
            with open(self.quiz_file, 'w', encoding='utf-8') as f:
                json.dump(default_questions, f, ensure_ascii=False, indent=2)
    
    def _load_questions(self) -> List[Dict]:
        """Загружает вопросы из файла"""
        with open(self.quiz_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def start_quiz(self, user_id: int, difficulty: str = None) -> Dict:
        """Начинает новую викторину для пользователя"""
        # Фильтруем вопросы по сложности если нужно
        filtered_questions = self.questions
        if difficulty:
            filtered_questions = [q for q in self.questions if q["difficulty"] == difficulty]
        
        if not filtered_questions:
            filtered_questions = self.questions
        
        # Выбираем случайные 5 вопросов
        quiz_questions = random.sample(filtered_questions, min(5, len(filtered_questions)))
        
        self.user_sessions[user_id] = {
            "questions": quiz_questions,
            "current_question": 0,
            "score": 0,
            "started_at": datetime.now().isoformat(),
            "answers": []
        }
        
        return self.get_current_question(user_id)
    
    def get_current_question(self, user_id: int) -> Dict:
        """Получает текущий вопрос"""
        if user_id not in self.user_sessions:
            return None
        
        session = self.user_sessions[user_id]
        if session["current_question"] >= len(session["questions"]):
            return None
        
        question = session["questions"][session["current_question"]]
        
        return {
            "number": session["current_question"] + 1,
            "total": len(session["questions"]),
            "question": question["question"],
            "options": question["options"],
            "difficulty": question["difficulty"],
            "author": question.get("author", "unknown")
        }
    
    def answer_question(self, user_id: int, answer_index: int) -> Tuple[bool, str]:
        """Проверяет ответ и переходит к следующему вопросу"""
        if user_id not in self.user_sessions:
            return False, "Викторина не начата"
        
        session = self.user_sessions[user_id]
        current_q = session["current_question"]
        
        if current_q >= len(session["questions"]):
            return False, "Викторина уже завершена"
        
        question = session["questions"][current_q]
        is_correct = (answer_index == question["correct"])
        
        # Сохраняем ответ
        session["answers"].append({
            "question": question["question"],
            "user_answer": answer_index,
            "correct_answer": question["correct"],
            "is_correct": is_correct
        })
        
        # Увеличиваем счет если правильно
        if is_correct:
            difficulty_multiplier = {
                "easy": 1,
                "medium": 2,
                "hard": 3
            }
            session["score"] += difficulty_multiplier.get(question["difficulty"], 1)
        
        # Переходим к следующему вопросу
        session["current_question"] += 1
        
        return is_correct, question["options"][question["correct"]]
    
    def finish_quiz(self, user_id: int) -> Dict:
        """Завершает викторину и возвращает результаты"""
        if user_id not in self.user_sessions:
            return None
        
        session = self.user_sessions.pop(user_id)
        
        total_questions = len(session["questions"])
        correct_answers = sum(1 for a in session["answers"] if a["is_correct"])
        percentage = (correct_answers / total_questions * 100) if total_questions > 0 else 0
        
        # Определяем оценку
        if percentage >= 90:
            grade = "Отлично! 🏆"
            grade_emoji = "🏆"
        elif percentage >= 70:
            grade = "Хорошо! 👍"
            grade_emoji = "👍"
        elif percentage >= 50:
            grade = "Удовлетворительно 👌"
            grade_emoji = "👌"
        else:
            grade = "Попробуйте еще раз 📚"
            grade_emoji = "📚"
        
        return {
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "score": session["score"],
            "percentage": percentage,
            "grade": grade,
            "grade_emoji": grade_emoji,
            "answers": session["answers"],
            "started_at": session["started_at"],
            "finished_at": datetime.now().isoformat()
        }

# Создаем глобальный экземпляр
quiz_service = QuizService()
