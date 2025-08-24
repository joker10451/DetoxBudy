#!/usr/bin/env python3
"""
@file: reminder_monitor.py
@description: Простой монитор для периодической проверки напоминаний
@dependencies: database, tasks
@created: 2024-08-24
"""

import sys
import time
import logging
from pathlib import Path

# Добавляем путь к src для импортов
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from detoxbuddy.tasks.reminder_tasks import check_due_reminders
from detoxbuddy.core.config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reminder_monitor.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Основная функция монитора"""
    logger.info("🚀 Запуск монитора напоминаний")
    logger.info(f"⏰ Интервал проверки: {settings.CELERY_TASK_TIME_LIMIT // 60} минут")
    
    try:
        while True:
            logger.info("🔍 Проверка напоминаний...")
            
            try:
                result = check_due_reminders()
                logger.info(f"✅ Обработано напоминаний: {result.get('processed', 0)}")
                
                if result.get('processed', 0) > 0:
                    logger.info(f"📨 Отправлено {result['processed']} напоминаний")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка при проверке напоминаний: {e}")
            
            # Ждем 60 секунд до следующей проверки
            logger.info("⏳ Ожидание 60 секунд...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("🛑 Монитор остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")


if __name__ == "__main__":
    main()
