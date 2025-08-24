"""
@file: create_achievement_tables.py
@description: Скрипт для создания таблиц достижений в базе данных
@dependencies: sqlalchemy, achievement models
@created: 2024-12-19
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detoxbuddy.database.database import engine
from src.detoxbuddy.database.models.achievement import Achievement, UserAchievement, UserLevel
from src.detoxbuddy.core.config import settings
import structlog

logger = structlog.get_logger()


def create_achievement_tables():
    """Создание таблиц достижений"""
    try:
        logger.info("Создаем таблицы достижений...")
        
        # Импортируем все модели для создания таблиц
        from src.detoxbuddy.database.models import Base
        
        # Создаем таблицы
        Base.metadata.create_all(bind=engine)
        
        logger.info("✅ Таблицы достижений созданы успешно")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при создании таблиц: {e}")
        raise


if __name__ == "__main__":
    create_achievement_tables()
