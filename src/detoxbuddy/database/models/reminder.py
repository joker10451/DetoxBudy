"""
@file: reminder.py
@description: Модель напоминаний для пользователей
@dependencies: sqlalchemy, datetime, base
@created: 2024-08-24
"""

from datetime import datetime, time
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Integer, Time, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
import enum

from .base import Base


class ReminderType(enum.Enum):
    """Типы напоминаний"""
    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"
    DETOX_REMINDER = "detox_reminder"
    FOCUS_REMINDER = "focus_reminder"
    BREAK_REMINDER = "break_reminder"
    QUIET_HOURS = "quiet_hours"


class ReminderStatus(enum.Enum):
    """Статусы напоминаний"""
    ACTIVE = "active"
    SENT = "sent"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    FAILED = "failed"


class Reminder(Base):
    """
    Модель напоминаний для пользователей.
    Управляет системой уведомлений и напоминаний.
    """
    __tablename__ = "reminders"

    # Основные поля
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Информация о напоминании
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reminder_type: Mapped[ReminderType] = mapped_column(
        Enum(ReminderType), nullable=False
    )
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(ReminderStatus), default=ReminderStatus.ACTIVE, nullable=False
    )
    
    # Время и расписание
    scheduled_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    reminder_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)  # для ежедневных напоминаний
    repeat_days: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON массив дней недели
    repeat_interval: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # интервал в минутах
    
    # Выполнение
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    failed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_send_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Настройки
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 1-5, где 5 - высший приоритет
    
    # Дополнительные данные
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON с дополнительными данными
    action_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)  # URL для действия
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Связи
    user: Mapped["User"] = relationship(back_populates="reminders")

    def __repr__(self) -> str:
        return f"Reminder(id={self.id}, title='{self.title}', type={self.reminder_type.value}, status={self.status.value})"

    @property
    def is_active(self) -> bool:
        """Проверяет, активно ли напоминание"""
        return self.status == ReminderStatus.ACTIVE and self.is_enabled

    @property
    def is_sent(self) -> bool:
        """Проверяет, отправлено ли напоминание"""
        return self.status == ReminderStatus.SENT

    @property
    def is_expired(self) -> bool:
        """Проверяет, истекло ли напоминание"""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False

    @property
    def can_send(self) -> bool:
        """Проверяет, можно ли отправить напоминание"""
        if not self.is_active or self.is_expired:
            return False
        
        if self.max_send_count and self.sent_count >= self.max_send_count:
            return False
        
        return datetime.utcnow() >= self.scheduled_time

    @property
    def next_send_time(self) -> Optional[datetime]:
        """Возвращает время следующей отправки"""
        if not self.is_recurring or not self.repeat_interval:
            return None
        
        if not self.sent_at:
            return self.scheduled_time
        
        return self.sent_at + datetime.timedelta(minutes=self.repeat_interval)
