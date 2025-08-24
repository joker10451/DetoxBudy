"""
@file: user.py
@description: Модель пользователя для Telegram бота
@dependencies: sqlalchemy, datetime, base
@created: 2024-08-24
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class User(Base):
    """
    Модель пользователя Telegram бота.
    Содержит основную информацию о пользователе и его настройки.
    """
    __tablename__ = "users"

    # Основные поля
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Статус и настройки
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Временные метки
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Связи с другими моделями
    detox_plans: Mapped[List["DetoxPlan"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    focus_sessions: Mapped[List["FocusSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    screen_times: Mapped[List["ScreenTime"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    reminders: Mapped[List["Reminder"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    settings: Mapped["UserSettings"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    achievements: Mapped[List["UserAchievement"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    level: Mapped["UserLevel"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})"

    @property
    def full_name(self) -> str:
        """Полное имя пользователя"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return self.username
        else:
            return f"User {self.telegram_id}"
