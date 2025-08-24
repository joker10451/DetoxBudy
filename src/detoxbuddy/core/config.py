"""
Конфигурация приложения DetoxBuddy
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки
    project_name: str = Field(default="DetoxBuddy", description="Название проекта")
    version: str = Field(default="1.0.0", description="Версия приложения")
    environment: str = Field(default="development", description="Окружение")
    debug: bool = Field(default=True, description="Режим отладки")
    log_level: str = Field(default="INFO", description="Уровень логирования")
    

    
    # Telegram Bot
    telegram_bot_token: Optional[str] = Field(default=None, description="Токен Telegram бота")
    
    # База данных
    database_url: str = Field(
        default="postgresql://detoxbuddy:password@localhost:5432/detoxbuddy",
        description="URL базы данных PostgreSQL"
    )
    
    # Redis
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="URL Redis сервера"
    )
    
    # Безопасность
    secret_key: str = Field(default="your-secret-key-here", description="Секретный ключ")
    algorithm: str = Field(default="HS256", description="Алгоритм шифрования")
    access_token_expire_minutes: int = Field(default=30, description="Время жизни токена")
    
    # Файлы
    upload_dir: str = Field(default="uploads/", description="Директория для загрузок")
    max_file_size: int = Field(default=10485760, description="Максимальный размер файла (10MB)")
    
    # Мониторинг
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN")
    
    # Внешние сервисы (для будущего использования)
    stripe_secret_key: Optional[str] = Field(default=None, description="Stripe секретный ключ")
    stripe_publishable_key: Optional[str] = Field(default=None, description="Stripe публичный ключ")
    
    # Celery настройки
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_TASK_SERIALIZER: str = "json"
    CELERY_RESULT_SERIALIZER: str = "json"
    CELERY_ACCEPT_CONTENT: list = ["json"]
    CELERY_TIMEZONE: str = "UTC"
    CELERY_ENABLE_UTC: bool = True
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 30 * 60  # 30 минут
    CELERY_TASK_SOFT_TIME_LIMIT: int = 25 * 60  # 25 минут
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Игнорируем дополнительные поля из .env


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
