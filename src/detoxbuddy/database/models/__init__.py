"""
@file: __init__.py
@description: Инициализация пакета моделей базы данных
@dependencies: sqlalchemy, pydantic
@created: 2024-08-24
"""

from .base import Base
from .user import User
from .detox_plan import DetoxPlan, DetoxPlanStatus, DetoxPlanType
from .focus_session import FocusSession, FocusSessionStatus, FocusSessionType
from .screen_time import ScreenTime
from .reminder import Reminder, ReminderType, ReminderStatus
from .user_settings import UserSettings
from .achievement import Achievement, UserAchievement, UserLevel, AchievementType

__all__ = [
    "Base",
    "User", 
    "DetoxPlan",
    "DetoxPlanStatus",
    "DetoxPlanType",
    "FocusSession",
    "FocusSessionStatus", 
    "FocusSessionType",
    "ScreenTime",
    "Reminder",
    "ReminderType",
    "ReminderStatus",
    "UserSettings",
    "Achievement",
    "UserAchievement",
    "UserLevel",
    "AchievementType"
]
