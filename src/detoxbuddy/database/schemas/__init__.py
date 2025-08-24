"""
@file: __init__.py
@description: Инициализация пакета схем Pydantic
@dependencies: pydantic
@created: 2024-08-24
"""

from .user import UserCreate, UserResponse, UserUpdate, UserInDB
from .user_settings import UserSettingsCreate, UserSettingsResponse, UserSettingsUpdate
from .screen_time import (
    ScreenTimeCreate, 
    ScreenTimeResponse, 
    ScreenTimeUpdate, 
    ScreenTimeList,
    ScreenTimeStats,
    QuickScreenTimeEntry
)

__all__ = [
    "UserCreate",
    "UserResponse", 
    "UserUpdate",
    "UserInDB",
    "UserSettingsCreate",
    "UserSettingsResponse",
    "UserSettingsUpdate",
    "ScreenTimeCreate",
    "ScreenTimeResponse", 
    "ScreenTimeUpdate",
    "ScreenTimeList",
    "ScreenTimeStats",
    "QuickScreenTimeEntry"
]
