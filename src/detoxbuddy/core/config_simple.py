"""
Упрощенная конфигурация приложения DetoxBuddy без pydantic
"""

import os
from typing import Optional


class Settings:
    """Настройки приложения"""
    
    def __init__(self):
        # Основные настройки
        self.project_name = os.getenv("PROJECT_NAME", "DetoxBuddy")
        self.version = os.getenv("VERSION", "1.0.0")
        self.environment = os.getenv("ENVIRONMENT", "production")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # Telegram Bot
        self.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        
        # База данных
        self.database_url = os.getenv(
            "DATABASE_URL", 
            "postgresql://detoxbuddy:password@localhost:5432/detoxbuddy"
        )
        
        # Redis
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        
        # Безопасность
        self.secret_key = os.getenv("SECRET_KEY", "your-secret-key-here")
        self.algorithm = os.getenv("ALGORITHM", "HS256")
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        
        # Файлы
        self.upload_dir = os.getenv("UPLOAD_DIR", "uploads/")
        self.max_file_size = int(os.getenv("MAX_FILE_SIZE", "10485760"))
        
        # Мониторинг
        self.sentry_dsn = os.getenv("SENTRY_DSN")
        
        # Внешние сервисы
        self.stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
        self.stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")
        
        # Celery настройки
        self.CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
        self.CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
        self.CELERY_TASK_SERIALIZER = "json"
        self.CELERY_RESULT_SERIALIZER = "json"
        self.CELERY_ACCEPT_CONTENT = ["json"]
        self.CELERY_TIMEZONE = "UTC"
        self.CELERY_ENABLE_UTC = True
        self.CELERY_TASK_TRACK_STARTED = True
        self.CELERY_TASK_TIME_LIMIT = 30 * 60
        self.CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60


# Создаем экземпляр настроек
settings = Settings()


def get_settings() -> Settings:
    """Получить настройки приложения"""
    return settings


# Дополнительные константы
class Constants:
    """Константы приложения"""
    
    # Команды бота
    COMMAND_START = "start"
    COMMAND_HELP = "help"
    COMMAND_DETOX = "detox"
    COMMAND_FOCUS = "focus"
    COMMAND_QUIET = "quiet"
    COMMAND_CONTENT = "content"
    COMMAND_ANALYTICS = "analytics"
    COMMAND_SETTINGS = "settings"
    
    # Статусы пользователей
    USER_STATUS_ACTIVE = "active"
    USER_STATUS_INACTIVE = "inactive"
    USER_STATUS_BLOCKED = "blocked"
    
    # Типы напоминаний
    REMINDER_TYPE_QUIET_HOURS = "quiet_hours"
    REMINDER_TYPE_FOCUS_BREAK = "focus_break"
    REMINDER_TYPE_DETOX_TASK = "detox_task"
    
    # Типы контента
    CONTENT_TYPE_ARTICLE = "article"
    CONTENT_TYPE_VIDEO = "video"
    CONTENT_TYPE_PODCAST = "podcast"
    CONTENT_TYPE_BOOK = "book"
    
    # Планы подписки
    SUBSCRIPTION_FREE = "free"
    SUBSCRIPTION_PREMIUM = "premium"
    SUBSCRIPTION_YEARLY = "yearly"


# Создаем экземпляр констант
constants = Constants()
