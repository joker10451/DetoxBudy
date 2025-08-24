"""
@file: celery_app.py
@description: Конфигурация Celery для фоновых задач и напоминаний
@dependencies: celery, redis, config
@created: 2024-08-24
"""

from celery import Celery
from detoxbuddy.core.config import settings

# Проверяем доступность Redis и выбираем брокер
import os
from redis import Redis

def get_broker_url():
    """Определяет URL брокера в зависимости от доступности Redis"""
    try:
        redis_client = Redis.from_url(settings.CELERY_BROKER_URL)
        redis_client.ping()
        return settings.CELERY_BROKER_URL, settings.CELERY_RESULT_BACKEND
    except:
        # Если Redis недоступен, используем SQLite
        os.makedirs('./data', exist_ok=True)
        sqlite_broker = "sqla+sqlite:///./data/celery_broker.db"
        sqlite_backend = "db+sqlite:///./data/celery_results.db"
        return sqlite_broker, sqlite_backend

broker_url, result_backend = get_broker_url()

# Создаем экземпляр Celery
celery_app = Celery(
    "detoxbuddy",
    broker=broker_url,
    backend=result_backend,
    include=["src.detoxbuddy.tasks.reminder_tasks"]
)

# Конфигурация Celery
celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=settings.CELERY_ENABLE_UTC,
    task_track_started=settings.CELERY_TASK_TRACK_STARTED,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    
    # Расписание задач
    beat_schedule={
        'check-reminders': {
            'task': 'src.detoxbuddy.tasks.reminder_tasks.check_due_reminders',
            'schedule': 60.0,  # каждую минуту
        },
        'cleanup-expired-reminders': {
            'task': 'src.detoxbuddy.tasks.reminder_tasks.cleanup_expired_reminders',
            'schedule': 3600.0,  # каждый час
        },
    }
)

# Автоматическое обнаружение задач
celery_app.autodiscover_tasks()