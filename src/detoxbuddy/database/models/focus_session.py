"""
@file: focus_session.py
@description: Модель сессии фокуса (Pomodoro)
@dependencies: sqlalchemy, datetime, base
@created: 2024-08-24
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Integer, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
import enum

from .base import Base


class FocusSessionStatus(enum.Enum):
    """Статусы сессии фокуса"""
    PLANNED = "planned"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class FocusSessionType(enum.Enum):
    """Типы сессий фокуса"""
    FOCUS = "focus"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"


class FocusSession(Base):
    """
    Модель сессии фокуса (Pomodoro).
    Отслеживает сессии фокусированной работы и перерывы.
    """
    __tablename__ = "focus_sessions"

    # Основные поля
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Информация о сессии
    session_type: Mapped[FocusSessionType] = mapped_column(
        Enum(FocusSessionType), nullable=False
    )
    status: Mapped[FocusSessionStatus] = mapped_column(
        Enum(FocusSessionStatus), default=FocusSessionStatus.PLANNED, nullable=False
    )
    
    # Длительность
    planned_duration: Mapped[int] = mapped_column(Integer, nullable=False)  # минуты
    actual_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # минуты
    paused_duration: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # минуты
    
    # Описание и заметки
    title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Временные метки
    planned_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    actual_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    actual_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_pause_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Статистика
    interruptions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_rate: Mapped[Optional[float]] = mapped_column(Integer, nullable=True)  # процент выполнения
    
    # Настройки
    auto_start_next: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Связи
    user: Mapped["User"] = relationship(back_populates="focus_sessions")

    def __repr__(self) -> str:
        return f"FocusSession(id={self.id}, type={self.session_type.value}, status={self.status.value})"

    @property
    def is_active(self) -> bool:
        """Проверяет, активна ли сессия"""
        return self.status == FocusSessionStatus.ACTIVE

    @property
    def is_completed(self) -> bool:
        """Проверяет, завершена ли сессия"""
        return self.status == FocusSessionStatus.COMPLETED

    @property
    def is_paused(self) -> bool:
        """Проверяет, приостановлена ли сессия"""
        return self.status == FocusSessionStatus.PAUSED

    @property
    def total_duration_minutes(self) -> int:
        """Возвращает общую длительность в минутах"""
        if self.actual_duration:
            return self.actual_duration
        return self.planned_duration

    @property
    def effective_duration_minutes(self) -> int:
        """Возвращает эффективную длительность (без пауз)"""
        if self.actual_duration:
            return self.actual_duration - self.paused_duration
        return self.planned_duration

    def calculate_completion_rate(self) -> float:
        """Вычисляет процент выполнения сессии"""
        if not self.actual_duration or not self.planned_duration:
            return 0.0
        
        return min(100.0, (self.actual_duration / self.planned_duration) * 100)
