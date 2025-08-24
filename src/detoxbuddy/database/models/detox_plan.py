"""
@file: detox_plan.py
@description: Модель плана цифрового детокса
@dependencies: sqlalchemy, datetime, base
@created: 2024-08-24
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, Integer, Date, Text, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
import enum

from .base import Base


class DetoxPlanStatus(enum.Enum):
    """Статусы плана детокса"""
    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class DetoxPlanType(enum.Enum):
    """Типы планов детокса"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"


class DetoxPlan(Base):
    """
    Модель плана цифрового детокса.
    Содержит информацию о персональном плане детокса пользователя.
    """
    __tablename__ = "detox_plans"

    # Основные поля
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    
    # Информация о плане
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_type: Mapped[DetoxPlanType] = mapped_column(
        Enum(DetoxPlanType), default=DetoxPlanType.DAILY, nullable=False
    )
    status: Mapped[DetoxPlanStatus] = mapped_column(
        Enum(DetoxPlanStatus), default=DetoxPlanStatus.ACTIVE, nullable=False
    )
    
    # Цели и ограничения
    target_screen_time: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # минуты в день
    target_apps_to_limit: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # JSON массив приложений
    target_activities: Mapped[Optional[str]] = mapped_column(Text, nullable=True)       # JSON массив активностей
    
    # Временные рамки
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    daily_start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    daily_end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Прогресс
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_completed_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Настройки
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Связи
    user: Mapped["User"] = relationship(back_populates="detox_plans")

    def __repr__(self) -> str:
        return f"DetoxPlan(id={self.id}, name='{self.name}', status={self.status.value})"

    @property
    def is_active(self) -> bool:
        """Проверяет, активен ли план"""
        return self.status == DetoxPlanStatus.ACTIVE

    @property
    def is_completed(self) -> bool:
        """Проверяет, завершен ли план"""
        return self.status == DetoxPlanStatus.COMPLETED

    @property
    def progress_percentage(self) -> float:
        """Возвращает процент выполнения плана"""
        if not self.end_date or not self.start_date:
            return 0.0
        
        total_days = (self.end_date - self.start_date).days + 1
        if total_days <= 0:
            return 0.0
        
        return min(100.0, (self.total_completed_days / total_days) * 100)
