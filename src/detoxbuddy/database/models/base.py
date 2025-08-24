"""
@file: base.py
@description: Базовая модель SQLAlchemy для всех моделей проекта
@dependencies: sqlalchemy.orm
@created: 2024-08-24
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Базовая модель для всех SQLAlchemy моделей в проекте.
    Наследуется от DeclarativeBase для поддержки современных возможностей SQLAlchemy 2.0.
    """
    pass
