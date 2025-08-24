"""
@file: user.py
@description: Pydantic схемы для пользователей
@dependencies: pydantic, datetime
@created: 2024-08-24
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class UserBase(BaseModel):
    """Базовая схема пользователя"""
    telegram_id: int = Field(..., description="ID пользователя в Telegram")
    username: Optional[str] = Field(None, max_length=100, description="Имя пользователя в Telegram")
    first_name: Optional[str] = Field(None, max_length=100, description="Имя пользователя")
    last_name: Optional[str] = Field(None, max_length=100, description="Фамилия пользователя")


class UserCreate(UserBase):
    """Схема для создания пользователя"""
    is_active: bool = Field(True, description="Активен ли пользователь")
    is_premium: bool = Field(False, description="Премиум статус пользователя")


class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""
    username: Optional[str] = Field(None, max_length=100, description="Имя пользователя в Telegram")
    first_name: Optional[str] = Field(None, max_length=100, description="Имя пользователя")
    last_name: Optional[str] = Field(None, max_length=100, description="Фамилия пользователя")
    is_active: Optional[bool] = Field(None, description="Активен ли пользователь")
    is_premium: Optional[bool] = Field(None, description="Премиум статус пользователя")


class UserInDB(UserBase):
    """Схема пользователя в базе данных"""
    id: int = Field(..., description="ID пользователя в базе данных")
    is_active: bool = Field(..., description="Активен ли пользователь")
    is_premium: bool = Field(..., description="Премиум статус пользователя")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата последнего обновления")
    last_activity: Optional[datetime] = Field(None, description="Последняя активность")
    
    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserInDB):
    """Схема ответа с информацией о пользователе"""
    full_name: Optional[str] = Field(None, description="Полное имя пользователя")
    
    @property
    def full_name_computed(self) -> str:
        """Вычисляемое полное имя"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return self.username
        else:
            return f"User {self.telegram_id}"


class UserList(BaseModel):
    """Схема для списка пользователей"""
    users: list[UserResponse] = Field(..., description="Список пользователей")
    total: int = Field(..., description="Общее количество пользователей")
    page: int = Field(..., description="Номер страницы")
    size: int = Field(..., description="Размер страницы")
    pages: int = Field(..., description="Общее количество страниц")
