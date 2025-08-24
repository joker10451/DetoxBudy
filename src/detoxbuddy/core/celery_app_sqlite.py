"""
@file: celery_app_sqlite.py
@description: Альтернативная конфигурация Celery с SQLite брокером
@dependencies: celery, sqlite, config
@created: 2024-08-24
"""

from celery import Celery
from detoxbuddy.core.config import settings
import os

# Создаем директорию для данных если её нет
os.makedirs('./data', exist_ok=True)

# Создаем экземпляр Celery с SQLite брокером
celery_app = Celery(
    "detoxbuddy",
    broker="sqla+sqlite:///./data/celery_broker.db",
    backend="db+sqlite:///./data/celery_results.db",
    include=["src.detoxbuddy.tasks.reminder_tasks"]
)

# Конфигурация Celery
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 минут
    task_soft_time_limit=25 * 60,  # 25 минут
    
    # Настройки для SQLite брокера
    broker_transport_options={
        'polling_interval': 1.0,
        'visibility_timeout': 3600,
    },
    
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
