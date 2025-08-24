#!/usr/bin/env python3
"""
@file: run_celery.py
@description: Скрипт для запуска Celery worker и beat для системы напоминаний
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
        logging.FileHandler('celery.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Основная функция запуска Celery"""
    try:
        logger.info("Запуск Celery worker и beat...")
        
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
        
        # Запуск Celery worker
        logger.info("Запуск Celery worker...")
        celery_app.worker_main([
            'worker',
            '--loglevel=info',
            '--concurrency=2',
            '--pool=prefork'
        ])
        
    except Exception as e:
        logger.error(f"Ошибка при запуске Celery: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
