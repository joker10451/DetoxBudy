"""
@file: database.py
@description: Настройка подключения к базе данных
@dependencies: sqlalchemy, config
@created: 2024-08-24
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import Generator

from detoxbuddy.core.config_simple import settings
from .models import Base

# Создание движка базы данных
import os

# Создаем директорию data если её нет
os.makedirs("data", exist_ok=True)

if settings.database_url:
    try:
        # Продакшн/разработка с реальной БД
        engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=settings.debug
        )
        # Проверяем подключение
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        print(f"✅ Подключено к базе данных: {settings.database_url}")
    except Exception as e:
        print(f"❌ Не удалось подключиться к PostgreSQL: {e}")
        print("🔄 Переключаемся на локальную SQLite базу данных...")
        # Fallback на SQLite
        engine = create_engine(
            "sqlite:///./data/detoxbuddy.db",
            connect_args={"check_same_thread": False},
            echo=settings.debug
        )
        print("✅ Используется SQLite база данных: ./data/detoxbuddy.db")
else:
    # Разработка с SQLite файлом
    engine = create_engine(
        "sqlite:///./data/detoxbuddy.db",
        connect_args={"check_same_thread": False},
        echo=settings.debug
    )
    print("✅ Используется SQLite база данных: ./data/detoxbuddy.db")

# Создание фабрики сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Автоматически создаем таблицы при импорте модуля
try:
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы базы данных созданы/проверены")
except Exception as e:
    print(f"❌ Ошибка создания таблиц: {e}")


def create_tables() -> None:
    """Создает все таблицы в базе данных"""
    Base.metadata.create_all(bind=engine)


def drop_tables() -> None:
    """Удаляет все таблицы из базы данных"""
    Base.metadata.drop_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Генератор для получения сессии базы данных.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session() -> Session:
    """
    Получает сессию базы данных.
    """
    return SessionLocal()


def init_db() -> None:
    """
    Инициализация базы данных.
    Создает таблицы и проверяет подключение.
    """
    try:
        create_tables()
        print("✅ База данных инициализирована успешно")
    except Exception as e:
        print(f"❌ Ошибка инициализации базы данных: {e}")
        raise
