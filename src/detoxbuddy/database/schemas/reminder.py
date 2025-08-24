"""
@file: reminder.py
@description: Pydantic схемы для API напоминаний
@dependencies: pydantic, datetime, typing
@created: 2024-08-24
"""

from datetime import datetime, time
from typing import Optional, List
from pydantic import BaseModel, Field, validator
from enum import Enum

from detoxbuddy.database.models.reminder import ReminderType, ReminderStatus


class ReminderTypeEnum(str, Enum):
    """Типы напоминаний для API"""
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"
    DETOX_REMINDER = "detox_reminder"
    FOCUS_REMINDER = "focus_reminder"
    BREAK_REMINDER = "break_reminder"
    QUIET_HOURS = "quiet_hours"


class ReminderStatusEnum(str, Enum):
    """Статусы напоминаний для API"""
    ACTIVE = "active"
    SENT = "sent"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ReminderBase(BaseModel):
    """Базовая схема напоминания"""
    title: str = Field(..., min_length=1, max_length=200, description="Заголовок напоминания")
    message: Optional[str] = Field(None, max_length=1000, description="Текст напоминания")
    reminder_type: ReminderTypeEnum = Field(..., description="Тип напоминания")
    scheduled_time: datetime = Field(..., description="Время отправки напоминания")
    is_recurring: bool = Field(False, description="Повторяющееся напоминание")
    repeat_interval: Optional[int] = Field(None, ge=1, le=10080, description="Интервал повторения в минутах")
    expires_at: Optional[datetime] = Field(None, description="Время истечения напоминания")
    max_send_count: Optional[int] = Field(None, ge=1, le=1000, description="Максимальное количество отправок")
    priority: int = Field(1, ge=1, le=5, description="Приоритет напоминания (1-5)")
    action_url: Optional[str] = Field(None, max_length=500, description="URL для действия")

    @validator('scheduled_time')
    def validate_scheduled_time(cls, v):
        """Проверяет, что время отправки в будущем"""
        if v <= datetime.utcnow():
            raise ValueError('Время отправки должно быть в будущем')
        return v

    @validator('expires_at')
    def validate_expires_at(cls, v, values):
        """Проверяет, что время истечения после времени отправки"""
        if v and 'scheduled_time' in values and v <= values['scheduled_time']:
            raise ValueError('Время истечения должно быть после времени отправки')
        return v

    @validator('repeat_interval')
    def validate_repeat_interval(cls, v, values):
        """Проверяет, что интервал указан для повторяющихся напоминаний"""
        if values.get('is_recurring') and not v:
            raise ValueError('Интервал повторения обязателен для повторяющихся напоминаний')
        return v


class ReminderCreate(ReminderBase):
    """Схема для создания напоминания"""
    pass


class ReminderUpdate(BaseModel):
    """Схема для обновления напоминания"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    message: Optional[str] = Field(None, max_length=1000)
    reminder_type: Optional[ReminderTypeEnum] = None
    scheduled_time: Optional[datetime] = None
    is_recurring: Optional[bool] = None
    repeat_interval: Optional[int] = Field(None, ge=1, le=10080)
    expires_at: Optional[datetime] = None
    max_send_count: Optional[int] = Field(None, ge=1, le=1000)
    priority: Optional[int] = Field(None, ge=1, le=5)
    action_url: Optional[str] = Field(None, max_length=500)
    is_enabled: Optional[bool] = None

    @validator('scheduled_time')
    def validate_scheduled_time(cls, v):
        """Проверяет, что время отправки в будущем"""
        if v and v <= datetime.utcnow():
            raise ValueError('Время отправки должно быть в будущем')
        return v


class ReminderResponse(ReminderBase):
    """Схема для ответа с напоминанием"""
    id: int
    user_id: int
    status: ReminderStatusEnum
    sent_at: Optional[datetime] = None
    sent_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReminderList(BaseModel):
    """Схема для списка напоминаний"""
    reminders: List[ReminderResponse]
    total: int
    page: int
    size: int
    pages: int


class ReminderFilter(BaseModel):
    """Схема для фильтрации напоминаний"""
    status: Optional[ReminderStatusEnum] = None
    reminder_type: Optional[ReminderTypeEnum] = None
    is_recurring: Optional[bool] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    scheduled_after: Optional[datetime] = None
    scheduled_before: Optional[datetime] = None


class ReminderStats(BaseModel):
    """Схема для статистики напоминаний"""
    total: int
    active: int
    sent: int
    cancelled: int
    expired: int
    by_type: dict[str, int]
    by_priority: dict[str, int]


class QuickReminderCreate(BaseModel):
    """Схема для быстрого создания напоминания"""
    title: str = Field(..., min_length=1, max_length=200)
    message: Optional[str] = Field(None, max_length=1000)
    reminder_type: ReminderTypeEnum = Field(ReminderTypeEnum.CUSTOM, description="Тип напоминания")
    delay_minutes: int = Field(15, ge=1, le=10080, description="Задержка в минутах")
    is_recurring: bool = Field(False, description="Повторяющееся напоминание")
    repeat_interval: Optional[int] = Field(None, ge=1, le=10080, description="Интервал повторения в минутах")

    @validator('repeat_interval')
    def validate_repeat_interval(cls, v, values):
        """Проверяет, что интервал указан для повторяющихся напоминаний"""
        if values.get('is_recurring') and not v:
            raise ValueError('Интервал повторения обязателен для повторяющихся напоминаний')
        return v


class ReminderBulkCreate(BaseModel):
    """Схема для массового создания напоминаний"""
    reminders: List[ReminderCreate] = Field(..., min_items=1, max_items=10)
