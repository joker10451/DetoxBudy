"""
@file: achievement.py
@description: Модели для системы достижений и геймификации
@dependencies: sqlalchemy, datetime, base
@created: 2024-12-19
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Boolean, Integer, Text, Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from .base import Base


class AchievementType(enum.Enum):
    """Типы достижений"""
    FOCUS_SESSIONS = "focus_sessions"  # Сессии фокуса
    SCREEN_TIME_REDUCTION = "screen_time_reduction"  # Сокращение экранного времени
    STREAK_DAYS = "streak_days"  # Серия дней
    REMINDERS_COMPLETED = "reminders_completed"  # Выполненные напоминания
    DETOX_PLANS = "detox_plans"  # Планы детокса
    FIRST_TIME = "first_time"  # Первые шаги
    MILESTONE = "milestone"  # Достижения


class Achievement(Base):
    """Модель достижения"""
    __tablename__ = "achievements"

    # Основные поля
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[AchievementType] = mapped_column(Enum(AchievementType), nullable=False)
    
    # Условия получения
    condition_value: Mapped[int] = mapped_column(Integer, nullable=False)  # Значение для получения
    condition_period: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # Период (day, week, month)
    
    # Награды
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Очки опыта
    badge_icon: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # Эмодзи бейджа
    
    # Статус
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Связи
    user_achievements: Mapped[List["UserAchievement"]] = relationship(
        back_populates="achievement", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Achievement(id={self.id}, name='{self.name}', type={self.type.value})"


class UserAchievement(Base):
    """Модель достижений пользователя"""
    __tablename__ = "user_achievements"

    # Основные поля
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    achievement_id: Mapped[int] = mapped_column(Integer, ForeignKey("achievements.id"), nullable=False, index=True)
    
    # Прогресс
    current_progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="achievements")
    achievement: Mapped[Achievement] = relationship("Achievement", back_populates="user_achievements")

    def __repr__(self) -> str:
        return f"UserAchievement(user_id={self.user_id}, achievement_id={self.achievement_id}, progress={self.current_progress})"


class UserLevel(Base):
    """Модель уровней пользователя"""
    __tablename__ = "user_levels"

    # Основные поля
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Уровень и опыт
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Статистика
    achievements_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_streak_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Связи
    user: Mapped["User"] = relationship("User", back_populates="level")

    def __repr__(self) -> str:
        return f"UserLevel(user_id={self.user_id}, level={self.level}, exp={self.experience})"

    @property
    def experience_to_next_level(self) -> int:
        """Опыт, необходимый для следующего уровня"""
        return self.level * 100  # Простая формула: уровень * 100

    @property
    def progress_to_next_level(self) -> float:
        """Прогресс до следующего уровня (0.0 - 1.0)"""
        exp_needed = self.experience_to_next_level
        if exp_needed == 0:
            return 1.0
        return min(self.experience / exp_needed, 1.0)
