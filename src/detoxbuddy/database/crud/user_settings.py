"""
@file: user_settings.py
@description: CRUD операции для настроек пользователей
@dependencies: sqlalchemy, app.models, app.schemas
@created: 2024-08-24
"""

from typing import Optional
from sqlalchemy.orm import Session

from detoxbuddy.database.crud.base import CRUDBase
from detoxbuddy.database.models.user_settings import UserSettings
from detoxbuddy.database.schemas.user_settings import UserSettingsCreate, UserSettingsUpdate


class CRUDUserSettings(CRUDBase[UserSettings, UserSettingsCreate, UserSettingsUpdate]):
    """CRUD операции для настроек пользователей"""
    
    def get_by_user_id(self, db: Session, *, user_id: int) -> Optional[UserSettings]:
        """Получить настройки пользователя по user_id"""
        return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    
    def create_or_update_by_user_id(
        self, 
        db: Session, 
        *, 
        user_id: int, 
        obj_in: UserSettingsUpdate
    ) -> UserSettings:
        """Создать или обновить настройки пользователя"""
        existing_settings = self.get_by_user_id(db=db, user_id=user_id)
        
        if existing_settings:
            # Обновляем существующие настройки
            return self.update(db=db, db_obj=existing_settings, obj_in=obj_in)
        else:
            # Создаем новые настройки
            create_data = UserSettingsCreate(user_id=user_id, **obj_in.model_dump(exclude_unset=True))
            return self.create(db=db, obj_in=create_data)
    
    def reset_to_defaults(self, db: Session, *, user_id: int) -> UserSettings:
        """Сбросить настройки пользователя к значениям по умолчанию"""
        settings = self.get_by_user_id(db=db, user_id=user_id)
        
        if settings:
            # Обновляем настройки значениями по умолчанию
            default_update = UserSettingsUpdate(
                notifications_enabled=True,
                daily_reminder_time=None,
                weekly_report_enabled=True,
                quiet_hours_enabled=False,
                quiet_hours_start=None,
                quiet_hours_end=None,
                default_focus_duration=25,
                default_break_duration=5,
                long_break_duration=15,
                daily_screen_time_limit=None,
                detox_goal_hours=None,
                preferred_detox_days=None,
                language="ru",
                timezone="Europe/Moscow"
            )
            return self.update(db=db, db_obj=settings, obj_in=default_update)
        else:
            # Создаем новые настройки по умолчанию
            default_create = UserSettingsCreate(user_id=user_id)
            return self.create(db=db, obj_in=default_create)
    
    def toggle_notifications(self, db: Session, *, user_id: int) -> UserSettings:
        """Переключить уведомления для пользователя"""
        settings = self.get_by_user_id(db=db, user_id=user_id)
        
        if settings:
            settings.notifications_enabled = not settings.notifications_enabled
            from datetime import datetime
            settings.updated_at = datetime.utcnow()
            db.add(settings)
            db.commit()
            db.refresh(settings)
            return settings
        else:
            # Создаем настройки с выключенными уведомлениями
            create_data = UserSettingsCreate(user_id=user_id, notifications_enabled=False)
            return self.create(db=db, obj_in=create_data)
    
    def set_focus_settings(
        self, 
        db: Session, 
        *, 
        user_id: int,
        focus_duration: int,
        break_duration: int,
        long_break_duration: int
    ) -> UserSettings:
        """Установить настройки фокуса для пользователя"""
        update_data = UserSettingsUpdate(
            default_focus_duration=focus_duration,
            default_break_duration=break_duration,
            long_break_duration=long_break_duration
        )
        return self.create_or_update_by_user_id(db=db, user_id=user_id, obj_in=update_data)
    
    def set_quiet_hours(
        self, 
        db: Session, 
        *, 
        user_id: int,
        enabled: bool,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> UserSettings:
        """Установить тихие часы для пользователя"""
        from datetime import time
        
        quiet_start = None
        quiet_end = None
        
        if enabled and start_time and end_time:
            try:
                # Парсим время в формате HH:MM
                start_parts = start_time.split(":")
                end_parts = end_time.split(":")
                quiet_start = time(int(start_parts[0]), int(start_parts[1]))
                quiet_end = time(int(end_parts[0]), int(end_parts[1]))
            except (ValueError, IndexError):
                # Если не удалось распарсить время, отключаем тихие часы
                enabled = False
        
        update_data = UserSettingsUpdate(
            quiet_hours_enabled=enabled,
            quiet_hours_start=quiet_start,
            quiet_hours_end=quiet_end
        )
        return self.create_or_update_by_user_id(db=db, user_id=user_id, obj_in=update_data)


# Создаем экземпляр CRUD для использования
user_settings_crud = CRUDUserSettings(UserSettings)
