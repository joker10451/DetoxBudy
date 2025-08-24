#!/usr/bin/env python3
"""
@file: run_celery_beat.py
@description: Скрипт для запуска Celery beat (планировщик задач)
@dependencies: celery, redis, database
@created: 2024-08-24
"""

import sys
import os
import logging
from pathlib import Path

# Добавляем путь к src для импортов
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from detoxbuddy.core.celery_app import celery_app
from detoxbuddy.core.config import settings
from detoxbuddy.database.database import init_db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('celery_beat.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Основная функция запуска Celery beat"""
    try:
        logger.info("Запуск Celery beat (планировщик задач)...")
        
        # Проверяем подключение к брокеру (Redis или SQLite)
        try:
            from redis import Redis
            redis_client = Redis.from_url(settings.CELERY_BROKER_URL)
            redis_client.ping()
            logger.info("✅ Подключение к Redis успешно")
        except Exception as e:
            logger.info("Redis недоступен, используем SQLite брокер")
            logger.info("✅ Будет использован SQLite для очередей задач")
        
        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        init_db()
        
        # Запуск Celery beat
        logger.info("Запуск Celery beat...")
        celery_app.start([
            'beat',
            '--loglevel=info',
            '--scheduler=celery.beat.PersistentScheduler'
        ])
        
    except Exception as e:
        logger.error(f"Ошибка при запуске Celery beat: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
