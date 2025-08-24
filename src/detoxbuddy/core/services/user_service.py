"""
@file: user_service.py
@description: Сервис для работы с пользователями
@dependencies: sqlalchemy, app.crud, app.schemas, telegram
@created: 2024-08-24
"""

from typing import Optional, Tuple
from sqlalchemy.orm import Session
from telegram import User as TelegramUser

from detoxbuddy.database.crud.user import user_crud
from detoxbuddy.database.crud.user_settings import user_settings_crud
from detoxbuddy.database.schemas.user import UserCreate, UserResponse
from detoxbuddy.database.models.user import User
from detoxbuddy.database.database import get_db_session


class UserService:
    """Сервис для работы с пользователями"""
    
    def __init__(self):
        pass
    
    def get_or_create_user_from_telegram(
        self, 
        telegram_user: TelegramUser,
        db: Optional[Session] = None
    ) -> Tuple[User, bool]:
        """
        Получить или создать пользователя из данных Telegram.
        
        Args:
            telegram_user: Объект пользователя Telegram
            db: Сессия базы данных (опционально)
            
        Returns:
            Tuple[User, bool]: Пользователь и флаг "был ли создан"
        """
        # Используем переданную сессию или создаем новую
        if db is None:
            db = get_db_session()
            close_db = True
        else:
            close_db = False
        
        try:
            # Пытаемся найти существующего пользователя
            existing_user = user_crud.get_by_telegram_id(
                db=db, 
                telegram_id=telegram_user.id
            )
            
            if existing_user:
                # Обновляем информацию пользователя из Telegram
                updated_user = self._update_user_from_telegram(
                    db=db, 
                    user=existing_user, 
                    telegram_user=telegram_user
                )
                return updated_user, False
            
            # Создаем нового пользователя
            user_data = UserCreate(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                is_active=True,
                is_premium=bool(telegram_user.is_premium) if hasattr(telegram_user, 'is_premium') and telegram_user.is_premium is not None else False
            )
            
            new_user = user_crud.create_with_settings(db=db, obj_in=user_data)
            return new_user, True
            
        finally:
            if close_db:
                db.close()
    
    def _update_user_from_telegram(
        self, 
        db: Session, 
        user: User, 
        telegram_user: TelegramUser
    ) -> User:
        """
        Обновить данные пользователя из Telegram.
        
        Args:
            db: Сессия базы данных
            user: Существующий пользователь
            telegram_user: Данные из Telegram
            
        Returns:
            User: Обновленный пользователь
        """
        # Проверяем, изменились ли данные
        update_needed = False
        
        if user.username != telegram_user.username:
            user.username = telegram_user.username
            update_needed = True
            
        if user.first_name != telegram_user.first_name:
            user.first_name = telegram_user.first_name
            update_needed = True
            
        if user.last_name != telegram_user.last_name:
            user.last_name = telegram_user.last_name
            update_needed = True
        
        # Обновляем премиум статус, если доступно
        if hasattr(telegram_user, 'is_premium') and telegram_user.is_premium is not None:
            new_premium_status = bool(telegram_user.is_premium)
            if user.is_premium != new_premium_status:
                user.is_premium = new_premium_status
                update_needed = True
        
        # Сохраняем изменения, если они есть
        if update_needed:
            from datetime import datetime
            user.updated_at = datetime.utcnow()
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Обновляем время последней активности
        user = user_crud.update_last_activity(db=db, user=user)
        
        return user
    
    def authenticate_telegram_user(
        self, 
        telegram_user: TelegramUser,
        db: Optional[Session] = None
    ) -> Optional[User]:
        """
        Аутентифицировать пользователя Telegram.
        
        Args:
            telegram_user: Объект пользователя Telegram
            db: Сессия базы данных (опционально)
            
        Returns:
            Optional[User]: Пользователь, если аутентификация успешна
        """
        user, created = self.get_or_create_user_from_telegram(
            telegram_user=telegram_user,
            db=db
        )
        
        # Проверяем, активен ли пользователь
        if not user.is_active:
            return None
        
        return user
    
    def get_user_by_telegram_id(
        self, 
        telegram_id: int,
        db: Optional[Session] = None
    ) -> Optional[User]:
        """
        Получить пользователя по Telegram ID.
        
        Args:
            telegram_id: ID пользователя в Telegram
            db: Сессия базы данных (опционально)
            
        Returns:
            Optional[User]: Пользователь, если найден
        """
        if db is None:
            db = get_db_session()
            close_db = True
        else:
            close_db = False
        
        try:
            return user_crud.get_by_telegram_id(db=db, telegram_id=telegram_id)
        finally:
            if close_db:
                db.close()
    
    def deactivate_user_by_telegram_id(
        self, 
        telegram_id: int,
        db: Optional[Session] = None
    ) -> bool:
        """
        Деактивировать пользователя по Telegram ID.
        
        Args:
            telegram_id: ID пользователя в Telegram
            db: Сессия базы данных (опционально)
            
        Returns:
            bool: True, если пользователь был деактивирован
        """
        if db is None:
            db = get_db_session()
            close_db = True
        else:
            close_db = False
        
        try:
            user = user_crud.get_by_telegram_id(db=db, telegram_id=telegram_id)
            if user and user.is_active:
                user_crud.deactivate_user(db=db, user=user)
                return True
            return False
        finally:
            if close_db:
                db.close()
    
    def get_user_settings_by_telegram_id(
        self, 
        telegram_id: int,
        db: Optional[Session] = None
    ) -> Optional[dict]:
        """
        Получить настройки пользователя по Telegram ID.
        
        Args:
            telegram_id: ID пользователя в Telegram
            db: Сессия базы данных (опционально)
            
        Returns:
            Optional[dict]: Настройки пользователя
        """
        if db is None:
            db = get_db_session()
            close_db = True
        else:
            close_db = False
        
        try:
            user = user_crud.get_by_telegram_id(db=db, telegram_id=telegram_id)
            if not user:
                return None
            
            settings = user_settings_crud.get_by_user_id(db=db, user_id=user.id)
            if not settings:
                # Создаем настройки по умолчанию
                from detoxbuddy.database.schemas.user_settings import UserSettingsCreate
                default_settings = UserSettingsCreate(user_id=user.id)
                settings = user_settings_crud.create(db=db, obj_in=default_settings)
            
            # Преобразуем в словарь для удобства
            return {
                "notifications_enabled": settings.notifications_enabled,
                "daily_reminder_time": settings.daily_reminder_time,
                "quiet_hours_enabled": settings.quiet_hours_enabled,
                "quiet_hours_start": settings.quiet_hours_start,
                "quiet_hours_end": settings.quiet_hours_end,
                "default_focus_duration": settings.default_focus_duration,
                "default_break_duration": settings.default_break_duration,
                "long_break_duration": settings.long_break_duration,
                "language": settings.language,
                "timezone": settings.timezone
            }
        finally:
            if close_db:
                db.close()
    
    def update_user_settings_by_telegram_id(
        self, 
        telegram_id: int,
        settings_update: dict,
        db: Optional[Session] = None
    ) -> bool:
        """
        Обновить настройки пользователя по Telegram ID.
        
        Args:
            telegram_id: ID пользователя в Telegram
            settings_update: Обновления настроек
            db: Сессия базы данных (опционально)
            
        Returns:
            bool: True, если настройки были обновлены
        """
        if db is None:
            db = get_db_session()
            close_db = True
        else:
            close_db = False
        
        try:
            user = user_crud.get_by_telegram_id(db=db, telegram_id=telegram_id)
            if not user:
                return False
            
            from detoxbuddy.database.schemas.user_settings import UserSettingsUpdate
            settings_schema = UserSettingsUpdate(**settings_update)
            
            user_settings_crud.create_or_update_by_user_id(
                db=db, 
                user_id=user.id, 
                obj_in=settings_schema
            )
            return True
        except Exception:
            return False
        finally:
            if close_db:
                db.close()


# Создаем экземпляр сервиса для использования
user_service = UserService()


def get_current_user():
    """
    Заглушка для функции аутентификации пользователя.
    В реальном приложении здесь должна быть логика получения текущего пользователя.
    """
    # TODO: Реализовать полноценную аутентификацию
    # Пока возвращаем None для тестирования
    return None


def authenticate_telegram_user(telegram_user):
    """
    Аутентификация пользователя Telegram.
    Обертка для удобства использования.
    """
    return user_service.authenticate_telegram_user(telegram_user)
