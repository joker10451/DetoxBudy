"""
@file: fix_enum_data.py
@description: Скрипт для исправления enum данных в базе
@dependencies: sqlalchemy, focus_session models
@created: 2024-12-19
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.detoxbuddy.database.database import get_db
from src.detoxbuddy.database.models.focus_session import FocusSession, FocusSessionType, FocusSessionStatus
from sqlalchemy import text
import structlog

logger = structlog.get_logger()


def fix_enum_data():
    """Исправление enum данных в базе"""
    db = next(get_db())
    
    try:
        # Исправляем session_type в focus_sessions используя прямой SQL
        logger.info("Исправляем session_type в focus_sessions...")
        
        # Используем прямой SQL для обновления данных
        result = db.execute(
            text("UPDATE focus_sessions SET session_type = 'FOCUS' WHERE session_type = 'focus'")
        )
        focus_updated = result.rowcount
        logger.info(f"Исправлено {focus_updated} сессий с 'focus' на 'FOCUS'")
        
        result = db.execute(
            text("UPDATE focus_sessions SET session_type = 'SHORT_BREAK' WHERE session_type = 'short_break'")
        )
        short_updated = result.rowcount
        logger.info(f"Исправлено {short_updated} сессий с 'short_break' на 'SHORT_BREAK'")
        
        result = db.execute(
            text("UPDATE focus_sessions SET session_type = 'LONG_BREAK' WHERE session_type = 'long_break'")
        )
        long_updated = result.rowcount
        logger.info(f"Исправлено {long_updated} сессий с 'long_break' на 'LONG_BREAK'")
        
        db.commit()
        logger.info("✅ Enum данные исправлены")
        
        # Проверяем результат
        total_sessions = db.execute(text("SELECT COUNT(*) FROM focus_sessions")).scalar()
        logger.info(f"Всего сессий в базе: {total_sessions}")
        
        # Проверяем, что все сессии имеют правильные enum значения
        sessions = db.query(FocusSession).all()
        logger.info(f"Все сессии загружены успешно: {len(sessions)}")
        
    except Exception as e:
        logger.error(f"Ошибка при исправлении данных: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_enum_data()
