"""
@file: init_achievements.py
@description: Скрипт для инициализации достижений в базе данных
@dependencies: sqlalchemy, achievement models
@created: 2024-12-19
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detoxbuddy.database.database import get_db
from src.detoxbuddy.database.models.achievement import Achievement, AchievementType
from src.detoxbuddy.core.config import settings
import structlog

logger = structlog.get_logger()


def init_achievements():
    """Инициализация достижений в базе данных"""
    db = next(get_db())
    
    # Список достижений для создания
    achievements_data = [
        # Достижения по сессиям фокуса
        {
            "name": "Первые шаги",
            "description": "Завершите свою первую сессию фокуса",
            "type": AchievementType.FOCUS_SESSIONS,
            "condition_value": 1,
            "points": 10,
            "badge_icon": "🎯"
        },
        {
            "name": "Фокус-мастер",
            "description": "Завершите 10 сессий фокуса",
            "type": AchievementType.FOCUS_SESSIONS,
            "condition_value": 10,
            "points": 50,
            "badge_icon": "🧠"
        },
        {
            "name": "Концентрация",
            "description": "Завершите 50 сессий фокуса",
            "type": AchievementType.FOCUS_SESSIONS,
            "condition_value": 50,
            "points": 200,
            "badge_icon": "⚡"
        },
        {
            "name": "Мастер фокуса",
            "description": "Завершите 100 сессий фокуса",
            "type": AchievementType.FOCUS_SESSIONS,
            "condition_value": 100,
            "points": 500,
            "badge_icon": "👑"
        },
        
        # Достижения по сокращению экранного времени
        {
            "name": "Цифровой детокс",
            "description": "Сократите среднее экранное время до 6 часов в день",
            "type": AchievementType.SCREEN_TIME_REDUCTION,
            "condition_value": 120,  # 2 часа сокращения (8 - 6 = 2 часа = 120 минут)
            "points": 30,
            "badge_icon": "📱"
        },
        {
            "name": "Осознанное потребление",
            "description": "Сократите среднее экранное время до 4 часов в день",
            "type": AchievementType.SCREEN_TIME_REDUCTION,
            "condition_value": 240,  # 4 часа сокращения
            "points": 100,
            "badge_icon": "🌱"
        },
        {
            "name": "Цифровая свобода",
            "description": "Сократите среднее экранное время до 2 часов в день",
            "type": AchievementType.SCREEN_TIME_REDUCTION,
            "condition_value": 360,  # 6 часов сокращения
            "points": 300,
            "badge_icon": "🕊️"
        },
        
        # Достижения по сериям дней
        {
            "name": "Неделя успеха",
            "description": "Поддерживайте активность 7 дней подряд",
            "type": AchievementType.STREAK_DAYS,
            "condition_value": 7,
            "points": 50,
            "badge_icon": "📅"
        },
        {
            "name": "Месяц дисциплины",
            "description": "Поддерживайте активность 30 дней подряд",
            "type": AchievementType.STREAK_DAYS,
            "condition_value": 30,
            "points": 200,
            "badge_icon": "📆"
        },
        {
            "name": "Стодневка",
            "description": "Поддерживайте активность 100 дней подряд",
            "type": AchievementType.STREAK_DAYS,
            "condition_value": 100,
            "points": 1000,
            "badge_icon": "💎"
        },
        
        # Достижения по напоминаниям
        {
            "name": "Пунктуальность",
            "description": "Выполните 10 напоминаний",
            "type": AchievementType.REMINDERS_COMPLETED,
            "condition_value": 10,
            "points": 25,
            "badge_icon": "⏰"
        },
        {
            "name": "Ответственность",
            "description": "Выполните 50 напоминаний",
            "type": AchievementType.REMINDERS_COMPLETED,
            "condition_value": 50,
            "points": 100,
            "badge_icon": "✅"
        },
        {
            "name": "Мастер планирования",
            "description": "Выполните 100 напоминаний",
            "type": AchievementType.REMINDERS_COMPLETED,
            "condition_value": 100,
            "points": 250,
            "badge_icon": "📋"
        },
        
        # Первые шаги
        {
            "name": "Добро пожаловать",
            "description": "Зарегистрируйтесь в системе",
            "type": AchievementType.FIRST_TIME,
            "condition_value": 1,
            "points": 5,
            "badge_icon": "👋"
        },
        {
            "name": "Первое напоминание",
            "description": "Создайте свое первое напоминание",
            "type": AchievementType.FIRST_TIME,
            "condition_value": 1,
            "points": 10,
            "badge_icon": "📝"
        },
        {
            "name": "Первая сессия",
            "description": "Завершите свою первую сессию фокуса",
            "type": AchievementType.FIRST_TIME,
            "condition_value": 1,
            "points": 15,
            "badge_icon": "🎯"
        },
        
        # Достижения
        {
            "name": "Бронзовый уровень",
            "description": "Достигните 5 уровня",
            "type": AchievementType.MILESTONE,
            "condition_value": 5,
            "points": 100,
            "badge_icon": "🥉"
        },
        {
            "name": "Серебряный уровень",
            "description": "Достигните 10 уровня",
            "type": AchievementType.MILESTONE,
            "condition_value": 10,
            "points": 250,
            "badge_icon": "🥈"
        },
        {
            "name": "Золотой уровень",
            "description": "Достигните 20 уровня",
            "type": AchievementType.MILESTONE,
            "condition_value": 20,
            "points": 500,
            "badge_icon": "🥇"
        },
        {
            "name": "Платиновый уровень",
            "description": "Достигните 50 уровня",
            "type": AchievementType.MILESTONE,
            "condition_value": 50,
            "points": 1000,
            "badge_icon": "💎"
        }
    ]
    
    try:
        # Проверяем, есть ли уже достижения в базе
        existing_count = db.query(Achievement).count()
        if existing_count > 0:
            logger.info(f"В базе уже есть {existing_count} достижений. Пропускаем инициализацию.")
            return
        
        # Создаем достижения
        for achievement_data in achievements_data:
            achievement = Achievement(**achievement_data)
            db.add(achievement)
        
        db.commit()
        logger.info(f"Создано {len(achievements_data)} достижений")
        
    except Exception as e:
        logger.error(f"Ошибка при создании достижений: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_achievements()
