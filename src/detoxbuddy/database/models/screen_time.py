"""
@file: screen_time.py
@description: Модель для отслеживания экранного времени
@dependencies: sqlalchemy, datetime, base
@created: 2024-08-24
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, DateTime, Integer, Date, Text, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from .base import Base


class ScreenTime(Base):
    """
    Модель для отслеживания экранного времени пользователя.
    Содержит данные о времени использования устройств и приложений.
    """
    __tablename__ = "screen_times"

    # Основные поля
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Дата и время
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Длительность использования
    total_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    active_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passive_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    
    # Информация об устройстве
    device_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # phone, tablet, laptop, desktop
    device_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    platform: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # iOS, Android, Windows, macOS, Linux
    
    # Детализация по приложениям
    app_usage_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON с данными по приложениям
    most_used_app: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    most_used_app_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Статистика
    pickups_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notifications_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_session_length: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # минуты
    
    # Категории активности
    productivity_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    social_media_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    entertainment_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    other_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Цели и ограничения
    daily_limit_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    limit_exceeded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    limit_exceeded_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Связи
    user: Mapped["User"] = relationship(back_populates="screen_times")

    def __repr__(self) -> str:
        return f"ScreenTime(id={self.id}, user_id={self.user_id}, date={self.date}, total_minutes={self.total_minutes})"

    @property
    def total_hours(self) -> float:
        """Возвращает общее время в часах"""
        return self.total_minutes / 60.0

    @property
    def active_hours(self) -> float:
        """Возвращает активное время в часах"""
        return self.active_minutes / 60.0

    @property
    def productivity_percentage(self) -> float:
        """Возвращает процент продуктивного времени"""
        if self.total_minutes == 0:
            return 0.0
        return (self.productivity_minutes / self.total_minutes) * 100

    @property
    def social_media_percentage(self) -> float:
        """Возвращает процент времени в соцсетях"""
        if self.total_minutes == 0:
            return 0.0
        return (self.social_media_minutes / self.total_minutes) * 100

    @property
    def is_within_limit(self) -> bool:
        """Проверяет, не превышен ли дневной лимит"""
        if not self.daily_limit_minutes:
            return True
        return self.total_minutes <= self.daily_limit_minutes

    @property
    def limit_usage_percentage(self) -> float:
        """Возвращает процент использования дневного лимита"""
        if not self.daily_limit_minutes:
            return 0.0
        return min(100.0, (self.total_minutes / self.daily_limit_minutes) * 100)
