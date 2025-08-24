"""
@file: __init__.py
@description: Инициализация пакета сервисов
@dependencies: app.services
@created: 2024-08-24
"""

from .user_service import user_service

__all__ = [
    "user_service"
]
