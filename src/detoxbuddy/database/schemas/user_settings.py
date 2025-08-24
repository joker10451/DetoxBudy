"""
@file: user_settings.py
@description: Pydantic схемы для настроек пользователей
@dependencies: pydantic, datetime
@created: 2024-08-24
"""

from datetime import datetime, time
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class UserSettingsBase(BaseModel):
    """Базовая схема настроек пользователя"""
    notifications_enabled: bool = Field(True, description="Уведомления включены")
    daily_reminder_time: Optional[time] = Field(None, description="Время ежедневного напоминания")
    weekly_report_enabled: bool = Field(True, description="Еженедельный отчет включен")
    
    quiet_hours_enabled: bool = Field(False, description="Тихие часы включены")
    quiet_hours_start: Optional[time] = Field(None, description="Начало тихих часов")
    quiet_hours_end: Optional[time] = Field(None, description="Конец тихих часов")
    
    default_focus_duration: int = Field(25, ge=5, le=120, description="Длительность фокуса по умолчанию (минуты)")
    default_break_duration: int = Field(5, ge=1, le=30, description="Длительность перерыва по умолчанию (минуты)")
    long_break_duration: int = Field(15, ge=5, le=60, description="Длительность длинного перерыва (минуты)")
    
    daily_screen_time_limit: Optional[int] = Field(None, ge=30, le=1440, description="Дневной лимит экранного времени (минуты)")
    detox_goal_hours: Optional[int] = Field(None, ge=1, le=24, description="Цель детокса (часы в день)")
    preferred_detox_days: Optional[str] = Field(None, description="Предпочитаемые дни детокса (JSON)")
    
    language: str = Field("ru", min_length=2, max_length=10, description="Язык интерфейса")
    timezone: str = Field("Europe/Moscow", min_length=1, max_length=50, description="Часовой пояс")


class UserSettingsCreate(UserSettingsBase):
    """Схема для создания настроек пользователя"""
    user_id: int = Field(..., description="ID пользователя")


class UserSettingsUpdate(BaseModel):
    """Схема для обновления настроек пользователя"""
    notifications_enabled: Optional[bool] = Field(None, description="Уведомления включены")
    daily_reminder_time: Optional[time] = Field(None, description="Время ежедневного напоминания")
    weekly_report_enabled: Optional[bool] = Field(None, description="Еженедельный отчет включен")
    
    quiet_hours_enabled: Optional[bool] = Field(None, description="Тихие часы включены")
    quiet_hours_start: Optional[time] = Field(None, description="Начало тихих часов")
    quiet_hours_end: Optional[time] = Field(None, description="Конец тихих часов")
    
    default_focus_duration: Optional[int] = Field(None, ge=5, le=120, description="Длительность фокуса по умолчанию (минуты)")
    default_break_duration: Optional[int] = Field(None, ge=1, le=30, description="Длительность перерыва по умолчанию (минуты)")
    long_break_duration: Optional[int] = Field(None, ge=5, le=60, description="Длительность длинного перерыва (минуты)")
    
    daily_screen_time_limit: Optional[int] = Field(None, ge=30, le=1440, description="Дневной лимит экранного времени (минуты)")
    detox_goal_hours: Optional[int] = Field(None, ge=1, le=24, description="Цель детокса (часы в день)")
    preferred_detox_days: Optional[str] = Field(None, description="Предпочитаемые дни детокса (JSON)")
    
    language: Optional[str] = Field(None, min_length=2, max_length=10, description="Язык интерфейса")
    timezone: Optional[str] = Field(None, min_length=1, max_length=50, description="Часовой пояс")


class UserSettingsInDB(UserSettingsBase):
    """Схема настроек пользователя в базе данных"""
    id: int = Field(..., description="ID настроек")
    user_id: int = Field(..., description="ID пользователя")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата последнего обновления")
    
    model_config = ConfigDict(from_attributes=True)


class UserSettingsResponse(UserSettingsInDB):
    """Схема ответа с настройками пользователя"""
    pass
