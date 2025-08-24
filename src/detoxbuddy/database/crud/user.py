"""
@file: user.py
@description: CRUD операции для пользователей
@dependencies: sqlalchemy, app.models, app.schemas
@created: 2024-08-24
"""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from detoxbuddy.database.crud.base import CRUDBase
from detoxbuddy.database.models.user import User
from detoxbuddy.database.models.user_settings import UserSettings
from detoxbuddy.database.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """CRUD операции для пользователей"""
    
    def get_by_telegram_id(self, db: Session, *, telegram_id: int) -> Optional[User]:
        """Получить пользователя по Telegram ID"""
        return db.query(User).filter(User.telegram_id == telegram_id).first()
    
    def get_by_username(self, db: Session, *, username: str) -> Optional[User]:
        """Получить пользователя по имени пользователя"""
        return db.query(User).filter(User.username == username).first()
    
    def create_with_settings(self, db: Session, *, obj_in: UserCreate) -> User:
        """Создать пользователя с настройками по умолчанию"""
        # Создаем пользователя
        user = self.create(db=db, obj_in=obj_in)
        
        # Создаем настройки по умолчанию
        user_settings = UserSettings(user_id=user.id)
        db.add(user_settings)
        db.commit()
        db.refresh(user_settings)
        
        # Обновляем объект пользователя, чтобы загрузить связанные настройки
        db.refresh(user)
        return user
    
    def get_active_users(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[User]:
        """Получить только активных пользователей"""
        return db.query(User).filter(
            User.is_active == True
        ).offset(skip).limit(limit).all()
    
    def get_premium_users(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[User]:
        """Получить только премиум пользователей"""
        return db.query(User).filter(
            and_(User.is_active == True, User.is_premium == True)
        ).offset(skip).limit(limit).all()
    
    def search_users(
        self, 
        db: Session, 
        *, 
        query: str, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[User]:
        """Поиск пользователей по имени или username"""
        search_query = f"%{query.lower()}%"
        return db.query(User).filter(
            or_(
                User.username.ilike(search_query),
                User.first_name.ilike(search_query),
                User.last_name.ilike(search_query)
            )
        ).offset(skip).limit(limit).all()
    
    def update_last_activity(self, db: Session, *, user: User) -> User:
        """Обновить время последней активности пользователя"""
        from datetime import datetime
        user.last_activity = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    def deactivate_user(self, db: Session, *, user: User) -> User:
        """Деактивировать пользователя"""
        user.is_active = False
        from datetime import datetime
        user.updated_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    def activate_user(self, db: Session, *, user: User) -> User:
        """Активировать пользователя"""
        user.is_active = True
        from datetime import datetime
        user.updated_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    def set_premium_status(self, db: Session, *, user: User, is_premium: bool) -> User:
        """Установить премиум статус пользователя"""
        user.is_premium = is_premium
        from datetime import datetime
        user.updated_at = datetime.utcnow()
        db.add(user)
        db.commit()
        db.refresh(user)
        return user


# Создаем экземпляр CRUD для использования
user_crud = CRUDUser(User)
