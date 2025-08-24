"""
@file: user_settings.py
@description: Модель настроек пользователя
@dependencies: sqlalchemy, datetime, base
@created: 2024-08-24
"""

from datetime import datetime, time
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Integer, Time, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey

from .base import Base


class UserSettings(Base):
    """
    Модель настроек пользователя.
    Содержит персональные предпочтения и настройки для цифрового детокса.
    """
    __tablename__ = "user_settings"

    # Основные поля
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    
    # Настройки уведомлений
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_reminder_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    weekly_report_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Настройки тихих часов
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    quiet_hours_start: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    quiet_hours_end: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    
    # Настройки фокуса
    default_focus_duration: Mapped[int] = mapped_column(Integer, default=25, nullable=False)  # минуты
    default_break_duration: Mapped[int] = mapped_column(Integer, default=5, nullable=False)   # минуты
    long_break_duration: Mapped[int] = mapped_column(Integer, default=15, nullable=False)     # минуты
    
    # Настройки детокса
    daily_screen_time_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # минуты
    detox_goal_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)         # часы в день
    preferred_detox_days: Mapped[Optional[str]] = mapped_column(Text, nullable=True)        # JSON массив дней недели
    
    # Настройки языка и региона
    language: Mapped[str] = mapped_column(String(10), default="ru", nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow", nullable=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Связи
    user: Mapped["User"] = relationship(back_populates="settings")

    def __repr__(self) -> str:
        return f"UserSettings(user_id={self.user_id}, notifications={self.notifications_enabled})"
