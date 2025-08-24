"""
@file: screen_time.py
@description: CRUD операции для экранного времени
@dependencies: sqlalchemy, datetime, typing, base
@created: 2024-08-24
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc, asc
from sqlalchemy.sql import text

from .base import CRUDBase
from ..models.screen_time import ScreenTime
from ..schemas.screen_time import ScreenTimeCreate, ScreenTimeUpdate


class CRUDScreenTime(CRUDBase[ScreenTime, ScreenTimeCreate, ScreenTimeUpdate]):
    """CRUD операции для экранного времени"""
    
    def get_by_user_and_date(
        self, db: Session, user_id: int, target_date: date
    ) -> Optional[ScreenTime]:
        """Получает запись экранного времени для пользователя на конкретную дату"""
        return db.query(ScreenTime).filter(
            and_(
                ScreenTime.user_id == user_id,
                ScreenTime.date == target_date
            )
        ).first()
    
    def get_user_records(
        self, 
        db: Session, 
        user_id: int, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ScreenTime]:
        """Получает записи экранного времени пользователя за период"""
        query = db.query(ScreenTime).filter(ScreenTime.user_id == user_id)
        
        if start_date:
            query = query.filter(ScreenTime.date >= start_date)
        if end_date:
            query = query.filter(ScreenTime.date <= end_date)
            
        return query.order_by(desc(ScreenTime.date)).offset(skip).limit(limit).all()
    
    def get_daily_stats(
        self, 
        db: Session, 
        user_id: int, 
        target_date: date
    ) -> Dict[str, Any]:
        """Получает дневную статистику экранного времени"""
        record = self.get_by_user_and_date(db, user_id, target_date)
        
        if not record:
            return {
                "total_minutes": 0,
                "total_hours": 0.0,
                "productivity_minutes": 0,
                "social_media_minutes": 0,
                "entertainment_minutes": 0,
                "other_minutes": 0,
                "productivity_percentage": 0.0,
                "social_media_percentage": 0.0,
                "entertainment_percentage": 0.0,
                "other_percentage": 0.0,
                "pickups_count": 0,
                "notifications_count": 0,
                "is_within_limit": True,
                "limit_usage_percentage": 0.0
            }
        
        total = record.total_minutes
        return {
            "total_minutes": total,
            "total_hours": record.total_hours,
            "productivity_minutes": record.productivity_minutes,
            "social_media_minutes": record.social_media_minutes,
            "entertainment_minutes": record.entertainment_minutes,
            "other_minutes": record.other_minutes,
            "productivity_percentage": record.productivity_percentage,
            "social_media_percentage": record.social_media_percentage,
            "entertainment_percentage": (record.entertainment_minutes / total * 100) if total > 0 else 0.0,
            "other_percentage": (record.other_minutes / total * 100) if total > 0 else 0.0,
            "pickups_count": record.pickups_count,
            "notifications_count": record.notifications_count,
            "is_within_limit": record.is_within_limit,
            "limit_usage_percentage": record.limit_usage_percentage
        }
    
    def get_weekly_stats(
        self, 
        db: Session, 
        user_id: int, 
        start_date: date
    ) -> Dict[str, Any]:
        """Получает недельную статистику экранного времени"""
        end_date = start_date + timedelta(days=6)
        records = self.get_user_records(db, user_id, start_date, end_date)
        
        if not records:
            return self._empty_weekly_stats(start_date, end_date)
        
        total_minutes = sum(r.total_minutes for r in records)
        total_hours = total_minutes / 60.0
        
        # Агрегация по категориям
        productivity_minutes = sum(r.productivity_minutes for r in records)
        social_media_minutes = sum(r.social_media_minutes for r in records)
        entertainment_minutes = sum(r.entertainment_minutes for r in records)
        other_minutes = sum(r.other_minutes for r in records)
        
        # Устройства
        device_breakdown = {}
        for record in records:
            if record.device_type:
                device_breakdown[record.device_type] = device_breakdown.get(record.device_type, 0) + record.total_minutes
        
        # Тренд по дням
        daily_trend = []
        for record in records:
            daily_trend.append({
                "date": record.date.isoformat(),
                "total_minutes": record.total_minutes,
                "productivity_minutes": record.productivity_minutes,
                "social_media_minutes": record.social_media_minutes,
                "entertainment_minutes": record.entertainment_minutes,
                "other_minutes": record.other_minutes
            })
        
        # Соблюдение лимитов
        limit_exceeded_days = sum(1 for r in records if r.limit_exceeded)
        limit_compliance = ((len(records) - limit_exceeded_days) / len(records) * 100) if records else 100.0
        
        return {
            "period": "week",
            "start_date": start_date,
            "end_date": end_date,
            "total_minutes": total_minutes,
            "total_hours": total_hours,
            "average_daily_minutes": total_minutes / len(records) if records else 0,
            "average_daily_hours": total_hours / len(records) if records else 0.0,
            "productivity_minutes": productivity_minutes,
            "social_media_minutes": social_media_minutes,
            "entertainment_minutes": entertainment_minutes,
            "other_minutes": other_minutes,
            "productivity_percentage": (productivity_minutes / total_minutes * 100) if total_minutes > 0 else 0.0,
            "social_media_percentage": (social_media_minutes / total_minutes * 100) if total_minutes > 0 else 0.0,
            "entertainment_percentage": (entertainment_minutes / total_minutes * 100) if total_minutes > 0 else 0.0,
            "other_percentage": (other_minutes / total_minutes * 100) if total_minutes > 0 else 0.0,
            "device_breakdown": device_breakdown,
            "top_apps": self._get_top_apps(records),
            "daily_trend": daily_trend,
            "limit_compliance": limit_compliance,
            "limit_exceeded_days": limit_exceeded_days
        }
    
    def get_monthly_stats(
        self, 
        db: Session, 
        user_id: int, 
        year: int, 
        month: int
    ) -> Dict[str, Any]:
        """Получает месячную статистику экранного времени"""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)
        
        records = self.get_user_records(db, user_id, start_date, end_date)
        
        if not records:
            return self._empty_monthly_stats(start_date, end_date)
        
        total_minutes = sum(r.total_minutes for r in records)
        total_hours = total_minutes / 60.0
        
        # Агрегация по категориям
        productivity_minutes = sum(r.productivity_minutes for r in records)
        social_media_minutes = sum(r.social_media_minutes for r in records)
        entertainment_minutes = sum(r.entertainment_minutes for r in records)
        other_minutes = sum(r.other_minutes for r in records)
        
        # Устройства
        device_breakdown = {}
        for record in records:
            if record.device_type:
                device_breakdown[record.device_type] = device_breakdown.get(record.device_type, 0) + record.total_minutes
        
        # Тренд по дням
        daily_trend = []
        for record in records:
            daily_trend.append({
                "date": record.date.isoformat(),
                "total_minutes": record.total_minutes,
                "productivity_minutes": record.productivity_minutes,
                "social_media_minutes": record.social_media_minutes,
                "entertainment_minutes": record.entertainment_minutes,
                "other_minutes": record.other_minutes
            })
        
        # Соблюдение лимитов
        limit_exceeded_days = sum(1 for r in records if r.limit_exceeded)
        limit_compliance = ((len(records) - limit_exceeded_days) / len(records) * 100) if records else 100.0
        
        return {
            "period": "month",
            "start_date": start_date,
            "end_date": end_date,
            "total_minutes": total_minutes,
            "total_hours": total_hours,
            "average_daily_minutes": total_minutes / len(records) if records else 0,
            "average_daily_hours": total_hours / len(records) if records else 0.0,
            "productivity_minutes": productivity_minutes,
            "social_media_minutes": social_media_minutes,
            "entertainment_minutes": entertainment_minutes,
            "other_minutes": other_minutes,
            "productivity_percentage": (productivity_minutes / total_minutes * 100) if total_minutes > 0 else 0.0,
            "social_media_percentage": (social_media_minutes / total_minutes * 100) if total_minutes > 0 else 0.0,
            "entertainment_percentage": (entertainment_minutes / total_minutes * 100) if total_minutes > 0 else 0.0,
            "other_percentage": (other_minutes / total_minutes * 100) if total_minutes > 0 else 0.0,
            "device_breakdown": device_breakdown,
            "top_apps": self._get_top_apps(records),
            "daily_trend": daily_trend,
            "limit_compliance": limit_compliance,
            "limit_exceeded_days": limit_exceeded_days
        }
    
    def create_quick_entry(
        self, 
        db: Session, 
        user_id: int, 
        minutes: int, 
        activity_type: str,
        device_type: Optional[str] = None
    ) -> ScreenTime:
        """Создает быструю запись экранного времени"""
        today = date.today()
        existing_record = self.get_by_user_and_date(db, user_id, today)
        
        if existing_record:
            # Обновляем существующую запись
            if activity_type == "productivity":
                existing_record.productivity_minutes += minutes
            elif activity_type == "social":
                existing_record.social_media_minutes += minutes
            elif activity_type == "entertainment":
                existing_record.entertainment_minutes += minutes
            else:  # other
                existing_record.other_minutes += minutes
            
            existing_record.total_minutes += minutes
            existing_record.active_minutes += minutes  # Предполагаем, что быстрые записи - активные
            
            if device_type:
                existing_record.device_type = device_type
            
            db.commit()
            db.refresh(existing_record)
            return existing_record
        else:
            # Создаем новую запись
            record_data = {
                "user_id": user_id,
                "date": today,
                "start_time": datetime.utcnow(),
                "total_minutes": minutes,
                "active_minutes": minutes,
                "passive_minutes": 0,
                "device_type": device_type,
                "productivity_minutes": minutes if activity_type == "productivity" else 0,
                "social_media_minutes": minutes if activity_type == "social" else 0,
                "entertainment_minutes": minutes if activity_type == "entertainment" else 0,
                "other_minutes": minutes if activity_type == "other" else 0
            }
            
            return self.create(db, obj_in=ScreenTimeCreate(**record_data))
    
    def _empty_weekly_stats(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Возвращает пустую недельную статистику"""
        return {
            "period": "week",
            "start_date": start_date,
            "end_date": end_date,
            "total_minutes": 0,
            "total_hours": 0.0,
            "average_daily_minutes": 0,
            "average_daily_hours": 0.0,
            "productivity_minutes": 0,
            "social_media_minutes": 0,
            "entertainment_minutes": 0,
            "other_minutes": 0,
            "productivity_percentage": 0.0,
            "social_media_percentage": 0.0,
            "entertainment_percentage": 0.0,
            "other_percentage": 0.0,
            "device_breakdown": {},
            "top_apps": [],
            "daily_trend": [],
            "limit_compliance": 100.0,
            "limit_exceeded_days": 0
        }
    
    def _empty_monthly_stats(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Возвращает пустую месячную статистику"""
        return {
            "period": "month",
            "start_date": start_date,
            "end_date": end_date,
            "total_minutes": 0,
            "total_hours": 0.0,
            "average_daily_minutes": 0,
            "average_daily_hours": 0.0,
            "productivity_minutes": 0,
            "social_media_minutes": 0,
            "entertainment_minutes": 0,
            "other_minutes": 0,
            "productivity_percentage": 0.0,
            "social_media_percentage": 0.0,
            "entertainment_percentage": 0.0,
            "other_percentage": 0.0,
            "device_breakdown": {},
            "top_apps": [],
            "daily_trend": [],
            "limit_compliance": 100.0,
            "limit_exceeded_days": 0
        }
    
    def _get_top_apps(self, records: List[ScreenTime]) -> List[Dict[str, Any]]:
        """Извлекает топ приложений из записей"""
        app_usage = {}
        for record in records:
            if record.most_used_app and record.most_used_app_minutes:
                app_usage[record.most_used_app] = app_usage.get(record.most_used_app, 0) + record.most_used_app_minutes
        
        # Сортируем по времени использования
        sorted_apps = sorted(app_usage.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"app_name": app_name, "total_minutes": minutes}
            for app_name, minutes in sorted_apps[:10]  # Топ 10 приложений
        ]


# Создаем экземпляр для использования
screen_time_crud = CRUDScreenTime(ScreenTime)
