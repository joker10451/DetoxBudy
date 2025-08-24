"""
@file: screen_time.py
@description: Pydantic схемы для экранного времени
@dependencies: pydantic, datetime, typing
@created: 2024-08-24
"""

from datetime import datetime, date
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, validator


class ScreenTimeBase(BaseModel):
    """Базовая схема для экранного времени"""
    date: date
    start_time: datetime
    end_time: Optional[datetime] = None
    total_minutes: int = Field(ge=0, description="Общее время в минутах")
    active_minutes: int = Field(ge=0, description="Активное время в минутах")
    passive_minutes: int = Field(ge=0, description="Пассивное время в минутах")
    
    # Информация об устройстве
    device_type: Optional[str] = Field(None, max_length=50, description="Тип устройства")
    device_name: Optional[str] = Field(None, max_length=100, description="Название устройства")
    platform: Optional[str] = Field(None, max_length=50, description="Платформа")
    
    # Детализация по приложениям
    app_usage_data: Optional[str] = Field(None, description="JSON с данными по приложениям")
    most_used_app: Optional[str] = Field(None, max_length=100, description="Самое используемое приложение")
    most_used_app_minutes: Optional[int] = Field(None, ge=0, description="Время в самом используемом приложении")
    
    # Статистика
    pickups_count: int = Field(default=0, ge=0, description="Количество поднятий устройства")
    notifications_count: int = Field(default=0, ge=0, description="Количество уведомлений")
    average_session_length: Optional[float] = Field(None, ge=0, description="Средняя длина сессии в минутах")
    
    # Категории активности
    productivity_minutes: int = Field(default=0, ge=0, description="Продуктивное время в минутах")
    social_media_minutes: int = Field(default=0, ge=0, description="Время в соцсетях в минутах")
    entertainment_minutes: int = Field(default=0, ge=0, description="Развлекательное время в минутах")
    other_minutes: int = Field(default=0, ge=0, description="Другое время в минутах")
    
    # Цели и ограничения
    daily_limit_minutes: Optional[int] = Field(None, ge=0, description="Дневной лимит в минутах")
    limit_exceeded: bool = Field(default=False, description="Превышен ли лимит")
    limit_exceeded_minutes: int = Field(default=0, ge=0, description="Количество минут превышения лимита")

    @validator('total_minutes', 'active_minutes', 'passive_minutes')
    def validate_minutes(cls, v, values):
        """Проверяет корректность времени"""
        if v < 0:
            raise ValueError('Время не может быть отрицательным')
        return v

    @validator('end_time')
    def validate_end_time(cls, v, values):
        """Проверяет, что время окончания после времени начала"""
        if v and 'start_time' in values and values['start_time']:
            if v <= values['start_time']:
                raise ValueError('Время окончания должно быть после времени начала')
        return v

    @validator('total_minutes')
    def validate_total_minutes(cls, v, values):
        """Проверяет, что общее время равно сумме активного и пассивного"""
        if 'active_minutes' in values and 'passive_minutes' in values:
            expected_total = values['active_minutes'] + values['passive_minutes']
            if v != expected_total:
                raise ValueError(f'Общее время ({v}) должно равняться сумме активного и пассивного времени ({expected_total})')
        return v


class ScreenTimeCreate(ScreenTimeBase):
    """Схема для создания записи экранного времени"""
    user_id: int = Field(..., description="ID пользователя")


class ScreenTimeUpdate(BaseModel):
    """Схема для обновления записи экранного времени"""
    end_time: Optional[datetime] = None
    total_minutes: Optional[int] = Field(None, ge=0)
    active_minutes: Optional[int] = Field(None, ge=0)
    passive_minutes: Optional[int] = Field(None, ge=0)
    device_type: Optional[str] = Field(None, max_length=50)
    device_name: Optional[str] = Field(None, max_length=100)
    platform: Optional[str] = Field(None, max_length=50)
    app_usage_data: Optional[str] = None
    most_used_app: Optional[str] = Field(None, max_length=100)
    most_used_app_minutes: Optional[int] = Field(None, ge=0)
    pickups_count: Optional[int] = Field(None, ge=0)
    notifications_count: Optional[int] = Field(None, ge=0)
    average_session_length: Optional[float] = Field(None, ge=0)
    productivity_minutes: Optional[int] = Field(None, ge=0)
    social_media_minutes: Optional[int] = Field(None, ge=0)
    entertainment_minutes: Optional[int] = Field(None, ge=0)
    other_minutes: Optional[int] = Field(None, ge=0)
    daily_limit_minutes: Optional[int] = Field(None, ge=0)
    limit_exceeded: Optional[bool] = None
    limit_exceeded_minutes: Optional[int] = Field(None, ge=0)


class ScreenTimeResponse(ScreenTimeBase):
    """Схема для ответа с данными экранного времени"""
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    # Вычисляемые поля
    total_hours: float
    active_hours: float
    productivity_percentage: float
    social_media_percentage: float
    is_within_limit: bool
    limit_usage_percentage: float

    class Config:
        from_attributes = True


class ScreenTimeList(BaseModel):
    """Схема для списка записей экранного времени"""
    items: list[ScreenTimeResponse]
    total: int
    page: int
    size: int
    pages: int


class ScreenTimeStats(BaseModel):
    """Схема для статистики экранного времени"""
    user_id: int
    period: str  # day, week, month
    start_date: date
    end_date: date
    
    # Общая статистика
    total_minutes: int
    total_hours: float
    average_daily_minutes: float
    average_daily_hours: float
    
    # Категории
    productivity_minutes: int
    social_media_minutes: int
    entertainment_minutes: int
    other_minutes: int
    
    # Проценты
    productivity_percentage: float
    social_media_percentage: float
    entertainment_percentage: float
    other_percentage: float
    
    # Устройства
    device_breakdown: Dict[str, int]  # device_type -> minutes
    
    # Приложения
    top_apps: list[Dict[str, Any]]  # список топ приложений
    
    # Тренды
    daily_trend: list[Dict[str, Any]]  # тренд по дням
    
    # Цели
    limit_compliance: float  # процент соблюдения лимитов
    limit_exceeded_days: int  # количество дней превышения лимита


class QuickScreenTimeEntry(BaseModel):
    """Схема для быстрого добавления экранного времени"""
    minutes: int = Field(..., gt=0, le=1440, description="Время в минутах (от 1 до 1440 минут)")
    device_type: Optional[str] = Field(None, max_length=50)
    activity_type: str = Field(..., description="Тип активности: productivity, social, entertainment, other")
    
    @validator('activity_type')
    def validate_activity_type(cls, v):
        """Проверяет корректность типа активности"""
        allowed_types = ['productivity', 'social', 'entertainment', 'other']
        if v not in allowed_types:
            raise ValueError(f'Тип активности должен быть одним из: {allowed_types}')
        return v
