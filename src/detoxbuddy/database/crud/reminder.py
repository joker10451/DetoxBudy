"""
@file: reminder.py
@description: CRUD операции для напоминаний
@dependencies: sqlalchemy, models, schemas
@created: 2024-08-24
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc

from detoxbuddy.database.crud.base import CRUDBase
from detoxbuddy.database.models.reminder import Reminder, ReminderStatus, ReminderType
from detoxbuddy.database.schemas.reminder import ReminderCreate, ReminderUpdate, ReminderFilter


class CRUDReminder(CRUDBase[Reminder, ReminderCreate, ReminderUpdate]):
    """CRUD операции для напоминаний"""
    
    def get_by_user(
        self, 
        db: Session, 
        user_id: int, 
        skip: int = 0, 
        limit: int = 100,
        status: Optional[ReminderStatus] = None,
        reminder_type: Optional[ReminderType] = None
    ) -> List[Reminder]:
        """Получает напоминания пользователя с фильтрацией"""
        query = db.query(self.model).filter(self.model.user_id == user_id)
        
        if status:
            query = query.filter(self.model.status == status)
        
        if reminder_type:
            query = query.filter(self.model.reminder_type == reminder_type)
        
        return query.offset(skip).limit(limit).all()
    
    def get_active_reminders(self, db: Session) -> List[Reminder]:
        """Получает все активные напоминания для отправки"""
        return (
            db.query(self.model)
            .filter(
                and_(
                    self.model.status == ReminderStatus.ACTIVE,
                    self.model.is_enabled == True,
                    self.model.scheduled_time <= datetime.now(),
                    or_(
                        self.model.expires_at.is_(None),
                        self.model.expires_at > datetime.now()
                    ),
                    or_(
                        self.model.max_send_count.is_(None),
                        self.model.sent_count < self.model.max_send_count
                    )
                )
            )
            .order_by(asc(self.model.scheduled_time))
            .all()
        )
    
    def get_expired_reminders(self, db: Session) -> List[Reminder]:
        """Получает истекшие напоминания"""
        return (
            db.query(self.model)
            .filter(
                and_(
                    self.model.expires_at <= datetime.now(),
                    self.model.status == ReminderStatus.ACTIVE
                )
            )
            .all()
        )
    
    def get_reminders_with_filters(
        self,
        db: Session,
        user_id: int,
        filters: ReminderFilter,
        skip: int = 0,
        limit: int = 100,
        sort_by: str = "scheduled_time",
        sort_order: str = "desc"
    ) -> tuple[List[Reminder], int]:
        """Получает напоминания с расширенной фильтрацией"""
        query = db.query(self.model).filter(self.model.user_id == user_id)
        
        # Применяем фильтры
        if filters.status:
            query = query.filter(self.model.status == filters.status)
        
        if filters.reminder_type:
            query = query.filter(self.model.reminder_type == filters.reminder_type)
        
        if filters.is_recurring is not None:
            query = query.filter(self.model.is_recurring == filters.is_recurring)
        
        if filters.priority:
            query = query.filter(self.model.priority == filters.priority)
        
        if filters.created_after:
            query = query.filter(self.model.created_at >= filters.created_after)
        
        if filters.created_before:
            query = query.filter(self.model.created_at <= filters.created_before)
        
        if filters.scheduled_after:
            query = query.filter(self.model.scheduled_time >= filters.scheduled_after)
        
        if filters.scheduled_before:
            query = query.filter(self.model.scheduled_time <= filters.scheduled_before)
        
        # Получаем общее количество
        total = query.count()
        
        # Применяем сортировку
        if sort_order == "desc":
            query = query.order_by(desc(getattr(self.model, sort_by)))
        else:
            query = query.order_by(asc(getattr(self.model, sort_by)))
        
        # Применяем пагинацию
        reminders = query.offset(skip).limit(limit).all()
        
        return reminders, total
    
    def get_user_stats(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Получает статистику напоминаний пользователя"""
        # Общая статистика
        total = db.query(func.count(self.model.id)).filter(self.model.user_id == user_id).scalar()
        active = db.query(func.count(self.model.id)).filter(
            and_(self.model.user_id == user_id, self.model.status == ReminderStatus.ACTIVE)
        ).scalar()
        sent = db.query(func.count(self.model.id)).filter(
            and_(self.model.user_id == user_id, self.model.status == ReminderStatus.SENT)
        ).scalar()
        cancelled = db.query(func.count(self.model.id)).filter(
            and_(self.model.user_id == user_id, self.model.status == ReminderStatus.CANCELLED)
        ).scalar()
        expired = db.query(func.count(self.model.id)).filter(
            and_(self.model.user_id == user_id, self.model.status == ReminderStatus.EXPIRED)
        ).scalar()
        
        # Статистика по типам
        by_type = {}
        type_stats = (
            db.query(self.model.reminder_type, func.count(self.model.id))
            .filter(self.model.user_id == user_id)
            .group_by(self.model.reminder_type)
            .all()
        )
        for reminder_type, count in type_stats:
            by_type[reminder_type.value] = count
        
        # Статистика по приоритетам
        by_priority = {}
        priority_stats = (
            db.query(self.model.priority, func.count(self.model.id))
            .filter(self.model.user_id == user_id)
            .group_by(self.model.priority)
            .all()
        )
        for priority, count in priority_stats:
            by_priority[str(priority)] = count
        
        return {
            "total": total,
            "active": active,
            "sent": sent,
            "cancelled": cancelled,
            "expired": expired,
            "by_type": by_type,
            "by_priority": by_priority
        }
    
    def mark_as_sent(self, db: Session, reminder_id: int) -> Optional[Reminder]:
        """Отмечает напоминание как отправленное"""
        reminder = db.query(self.model).filter(self.model.id == reminder_id).first()
        if reminder:
            reminder.status = ReminderStatus.SENT
            reminder.sent_at = datetime.now()
            reminder.sent_count += 1
            db.commit()
            db.refresh(reminder)
        return reminder
    
    def mark_as_failed(self, db: Session, reminder_id: int) -> Optional[Reminder]:
        """Отмечает напоминание как неудачное"""
        reminder = db.query(self.model).filter(self.model.id == reminder_id).first()
        if reminder:
            reminder.status = ReminderStatus.FAILED
            reminder.failed_at = datetime.now()
            reminder.failed_count += 1
            db.commit()
            db.refresh(reminder)
        return reminder
    
    def mark_as_expired(self, db: Session, reminder_id: int) -> Optional[Reminder]:
        """Отмечает напоминание как истекшее"""
        reminder = db.query(self.model).filter(self.model.id == reminder_id).first()
        if reminder:
            reminder.status = ReminderStatus.EXPIRED
            db.commit()
            db.refresh(reminder)
        return reminder
    
    def cancel_reminder(self, db: Session, reminder_id: int) -> Optional[Reminder]:
        """Отменяет напоминание"""
        reminder = db.query(self.model).filter(self.model.id == reminder_id).first()
        if reminder:
            reminder.status = ReminderStatus.CANCELLED
            db.commit()
            db.refresh(reminder)
        return reminder
    
    def enable_reminder(self, db: Session, reminder_id: int) -> Optional[Reminder]:
        """Включает напоминание"""
        reminder = db.query(self.model).filter(self.model.id == reminder_id).first()
        if reminder:
            reminder.is_enabled = True
            db.commit()
            db.refresh(reminder)
        return reminder
    
    def disable_reminder(self, db: Session, reminder_id: int) -> Optional[Reminder]:
        """Отключает напоминание"""
        reminder = db.query(self.model).filter(self.model.id == reminder_id).first()
        if reminder:
            reminder.is_enabled = False
            db.commit()
            db.refresh(reminder)
        return reminder
    
    def get_reminders_for_telegram_bot(
        self, 
        db: Session, 
        user_id: int, 
        limit: int = 10
    ) -> List[Reminder]:
        """Получает напоминания для отображения в Telegram боте"""
        return (
            db.query(self.model)
            .filter(
                and_(
                    self.model.user_id == user_id,
                    self.model.status.in_([ReminderStatus.ACTIVE, ReminderStatus.SENT])
                )
            )
            .order_by(desc(self.model.scheduled_time))
            .limit(limit)
            .all()
        )
    
    def create_quick_reminder(
        self,
        db: Session,
        user_id: int,
        title: str,
        message: Optional[str],
        delay_minutes: int = 15,
        reminder_type: ReminderType = ReminderType.CUSTOM
    ) -> Reminder:
        """Создает быстрое напоминание с задержкой"""
        scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)
        
        # Если сообщение не указано, используем заголовок
        if not message:
            message = title
        
        reminder = Reminder(
            user_id=user_id,
            title=title,
            message=message,
            reminder_type=reminder_type,
            scheduled_time=scheduled_time,
            status=ReminderStatus.ACTIVE,
            is_enabled=True,
            priority=1
        )
        
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        return reminder
    
    def cancel_all_active_reminders(self, db: Session, user_id: int) -> int:
        """Отменяет все активные напоминания пользователя"""
        result = (
            db.query(self.model)
            .filter(
                and_(
                    self.model.user_id == user_id,
                    self.model.status == ReminderStatus.ACTIVE
                )
            )
            .update({
                self.model.status: ReminderStatus.CANCELLED,
                self.model.updated_at: datetime.now()
            })
        )
        db.commit()
        return result
    
    def get_reminders_stats(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Получает статистику напоминаний для отображения в боте"""
        # Общая статистика
        total = db.query(func.count(self.model.id)).filter(self.model.user_id == user_id).scalar()
        active = db.query(func.count(self.model.id)).filter(
            and_(self.model.user_id == user_id, self.model.status == ReminderStatus.ACTIVE)
        ).scalar()
        sent = db.query(func.count(self.model.id)).filter(
            and_(self.model.user_id == user_id, self.model.status == ReminderStatus.SENT)
        ).scalar()
        cancelled = db.query(func.count(self.model.id)).filter(
            and_(self.model.user_id == user_id, self.model.status == ReminderStatus.CANCELLED)
        ).scalar()
        expired = db.query(func.count(self.model.id)).filter(
            and_(self.model.user_id == user_id, self.model.status == ReminderStatus.EXPIRED)
        ).scalar()
        
        # За последние 7 дней
        week_ago = datetime.now() - timedelta(days=7)
        last_7_days = db.query(func.count(self.model.id)).filter(
            and_(
                self.model.user_id == user_id,
                self.model.created_at >= week_ago
            )
        ).scalar()
        
        # Статистика повторяющихся напоминаний
        recurring = db.query(func.count(self.model.id)).filter(
            and_(
                self.model.user_id == user_id,
                self.model.is_recurring == True
            )
        ).scalar()
        
        return {
            "total": total or 0,
            "active": active or 0,
            "sent": sent or 0,
            "cancelled": cancelled or 0,
            "expired": expired or 0,
            "last_7_days": last_7_days or 0,
            "recurring": recurring or 0
        }
    
    def create_recurring_reminder(
        self,
        db: Session,
        user_id: int,
        title: str,
        message: Optional[str],
        reminder_type: ReminderType,
        repeat_interval: int,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        max_send_count: Optional[int] = None,
        priority: int = 1,
        repeat_days: Optional[str] = None,
        reminder_time: Optional[datetime.time] = None
    ) -> Reminder:
        """Создает повторяющееся напоминание"""
        # Если сообщение не указано, используем заголовок
        if not message:
            message = title
        
        reminder = Reminder(
            user_id=user_id,
            title=title,
            message=message,
            reminder_type=reminder_type,
            scheduled_time=start_time,
            is_recurring=True,
            repeat_interval=repeat_interval,
            repeat_days=repeat_days,
            reminder_time=reminder_time,
            expires_at=end_time,
            max_send_count=max_send_count,
            priority=priority,
            status=ReminderStatus.ACTIVE,
            is_enabled=True
        )
        
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        return reminder
    
    def create_daily_reminder(
        self,
        db: Session,
        user_id: int,
        title: str,
        message: Optional[str],
        reminder_time: datetime.time,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_send_count: Optional[int] = None,
        priority: int = 1
    ) -> Reminder:
        """Создает ежедневное напоминание"""
        if not message:
            message = title
        
        # Если не указана дата начала, используем сегодня
        if not start_date:
            start_date = datetime.now().replace(
                hour=reminder_time.hour,
                minute=reminder_time.minute,
                second=0,
                microsecond=0
            )
            # Если время уже прошло сегодня, планируем на завтра
            if start_date <= datetime.now():
                start_date += timedelta(days=1)
        
        reminder = Reminder(
            user_id=user_id,
            title=title,
            message=message,
            reminder_type=ReminderType.DAILY,
            scheduled_time=start_date,
            reminder_time=reminder_time,
            is_recurring=True,
            expires_at=end_date,
            max_send_count=max_send_count,
            priority=priority,
            status=ReminderStatus.ACTIVE,
            is_enabled=True
        )
        
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        return reminder
    
    def create_weekly_reminder(
        self,
        db: Session,
        user_id: int,
        title: str,
        message: Optional[str],
        days_of_week: List[str],
        reminder_time: datetime.time,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        max_send_count: Optional[int] = None,
        priority: int = 1
    ) -> Reminder:
        """Создает еженедельное напоминание"""
        if not message:
            message = title
        
        # Если не указана дата начала, используем следующий подходящий день
        if not start_date:
            start_date = self._get_next_weekly_date(days_of_week, reminder_time)
        
        reminder = Reminder(
            user_id=user_id,
            title=title,
            message=message,
            reminder_type=ReminderType.WEEKLY,
            scheduled_time=start_date,
            reminder_time=reminder_time,
            repeat_days=','.join(days_of_week),
            is_recurring=True,
            expires_at=end_date,
            max_send_count=max_send_count,
            priority=priority,
            status=ReminderStatus.ACTIVE,
            is_enabled=True
        )
        
        db.add(reminder)
        db.commit()
        db.refresh(reminder)
        return reminder
    
    def _get_next_weekly_date(self, days_of_week: List[str], reminder_time: datetime.time) -> datetime:
        """Вычисляет следующую дату для еженедельного напоминания"""
        from datetime import date
        
        # Маппинг дней недели
        day_mapping = {
            'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6,
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        today = date.today()
        current_weekday = today.weekday()
        
        # Находим следующий подходящий день
        for day_name in days_of_week:
            day_num = day_mapping.get(day_name.lower())
            if day_num is not None:
                days_ahead = day_num - current_weekday
                if days_ahead <= 0:  # Если день уже прошел на этой неделе
                    days_ahead += 7
                
                next_date = today + timedelta(days=days_ahead)
                return datetime.combine(next_date, reminder_time)
        
        # Fallback - следующий понедельник
        return datetime.combine(today + timedelta(days=7), reminder_time)
    
    def get_recurring_reminders(self, db: Session, user_id: int) -> List[Reminder]:
        """Получает все повторяющиеся напоминания пользователя"""
        return (
            db.query(self.model)
            .filter(
                and_(
                    self.model.user_id == user_id,
                    self.model.is_recurring == True,
                    self.model.status == ReminderStatus.ACTIVE
                )
            )
            .order_by(asc(self.model.scheduled_time))
            .all()
        )
    
    def pause_recurring_reminder(self, db: Session, reminder_id: int) -> Optional[Reminder]:
        """Приостанавливает повторяющееся напоминание"""
        reminder = db.query(self.model).filter(self.model.id == reminder_id).first()
        if reminder and reminder.is_recurring:
            reminder.is_enabled = False
            db.commit()
            db.refresh(reminder)
        return reminder
    
    def resume_recurring_reminder(self, db: Session, reminder_id: int) -> Optional[Reminder]:
        """Возобновляет повторяющееся напоминание"""
        reminder = db.query(self.model).filter(self.model.id == reminder_id).first()
        if reminder and reminder.is_recurring:
            reminder.is_enabled = True
            db.commit()
            db.refresh(reminder)
        return reminder


# Создаем экземпляр CRUD
reminder_crud = CRUDReminder(Reminder)
