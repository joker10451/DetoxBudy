"""
@file: screen_time_service.py
@description: Сервис для работы с экранным временем
@dependencies: sqlalchemy, datetime, typing, crud, schemas
@created: 2024-08-24
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from ...database.crud.screen_time import screen_time_crud
from ...database.schemas.screen_time import (
    ScreenTimeCreate, 
    ScreenTimeUpdate, 
    ScreenTimeResponse,
    ScreenTimeStats,
    QuickScreenTimeEntry
)
from ...database.models.screen_time import ScreenTime


class ScreenTimeService:
    """Сервис для работы с экранным временем"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_screen_time(self, screen_time_data: ScreenTimeCreate) -> ScreenTimeResponse:
        """Создает новую запись экранного времени"""
        screen_time = screen_time_crud.create(self.db, obj_in=screen_time_data)
        return ScreenTimeResponse.model_validate(screen_time)
    
    def get_screen_time(self, screen_time_id: int) -> Optional[ScreenTimeResponse]:
        """Получает запись экранного времени по ID"""
        screen_time = screen_time_crud.get(self.db, id=screen_time_id)
        if screen_time:
            return ScreenTimeResponse.model_validate(screen_time)
        return None
    
    def get_user_screen_time(
        self, 
        user_id: int, 
        target_date: date
    ) -> Optional[ScreenTimeResponse]:
        """Получает запись экранного времени пользователя на конкретную дату"""
        screen_time = screen_time_crud.get_by_user_and_date(self.db, user_id, target_date)
        if screen_time:
            return ScreenTimeResponse.model_validate(screen_time)
        return None
    
    def update_screen_time(
        self, 
        screen_time_id: int, 
        update_data: ScreenTimeUpdate
    ) -> Optional[ScreenTimeResponse]:
        """Обновляет запись экранного времени"""
        screen_time = screen_time_crud.update(self.db, id=screen_time_id, obj_in=update_data)
        if screen_time:
            return ScreenTimeResponse.model_validate(screen_time)
        return None
    
    def delete_screen_time(self, screen_time_id: int) -> bool:
        """Удаляет запись экранного времени"""
        return screen_time_crud.remove(self.db, id=screen_time_id)
    
    def get_user_records(
        self, 
        user_id: int, 
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[ScreenTimeResponse]:
        """Получает записи экранного времени пользователя за период"""
        records = screen_time_crud.get_user_records(
            self.db, user_id, start_date, end_date, skip, limit
        )
        return [ScreenTimeResponse.model_validate(record) for record in records]
    
    def get_daily_stats(self, user_id: int, target_date: date) -> Dict[str, Any]:
        """Получает дневную статистику экранного времени"""
        return screen_time_crud.get_daily_stats(self.db, user_id, target_date)
    
    def get_weekly_stats(self, user_id: int, start_date: date) -> Dict[str, Any]:
        """Получает недельную статистику экранного времени"""
        return screen_time_crud.get_weekly_stats(self.db, user_id, start_date)
    
    def get_monthly_stats(self, user_id: int, year: int, month: int) -> Dict[str, Any]:
        """Получает месячную статистику экранного времени"""
        return screen_time_crud.get_monthly_stats(self.db, user_id, year, month)
    
    def create_quick_entry(
        self, 
        user_id: int, 
        quick_entry: QuickScreenTimeEntry
    ) -> ScreenTimeResponse:
        """Создает быструю запись экранного времени"""
        screen_time = screen_time_crud.create_quick_entry(
            self.db,
            user_id=user_id,
            minutes=quick_entry.minutes,
            activity_type=quick_entry.activity_type,
            device_type=quick_entry.device_type
        )
        return ScreenTimeResponse.model_validate(screen_time)
    
    def get_today_summary(self, user_id: int) -> Dict[str, Any]:
        """Получает сводку за сегодня"""
        today = date.today()
        stats = self.get_daily_stats(user_id, today)
        
        # Добавляем рекомендации
        recommendations = self._generate_recommendations(stats)
        stats["recommendations"] = recommendations
        
        return stats
    
    def get_weekly_summary(self, user_id: int) -> Dict[str, Any]:
        """Получает недельную сводку"""
        # Находим начало текущей недели (понедельник)
        today = date.today()
        days_since_monday = today.weekday()
        start_of_week = today - timedelta(days=days_since_monday)
        
        stats = self.get_weekly_stats(user_id, start_of_week)
        
        # Добавляем рекомендации
        recommendations = self._generate_weekly_recommendations(stats)
        stats["recommendations"] = recommendations
        
        return stats
    
    def get_monthly_summary(self, user_id: int) -> Dict[str, Any]:
        """Получает месячную сводку"""
        today = date.today()
        stats = self.get_monthly_stats(user_id, today.year, today.month)
        
        # Добавляем рекомендации
        recommendations = self._generate_monthly_recommendations(stats)
        stats["recommendations"] = recommendations
        
        return stats
    
    def _generate_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Генерирует рекомендации на основе дневной статистики"""
        recommendations = []
        
        total_hours = stats["total_hours"]
        social_percentage = stats["social_media_percentage"]
        productivity_percentage = stats["productivity_percentage"]
        
        # Рекомендации по общему времени
        if total_hours > 8:
            recommendations.append("Сегодня вы провели за экраном более 8 часов. Попробуйте сократить время использования устройств.")
        elif total_hours < 2:
            recommendations.append("Отличная работа! Вы провели за экраном менее 2 часов сегодня.")
        
        # Рекомендации по соцсетям
        if social_percentage > 50:
            recommendations.append(f"Социальные сети занимают {social_percentage:.1f}% вашего времени. Попробуйте установить лимиты.")
        
        # Рекомендации по продуктивности
        if productivity_percentage < 30:
            recommendations.append("Продуктивное время составляет менее 30%. Попробуйте сосредоточиться на важных задачах.")
        elif productivity_percentage > 70:
            recommendations.append("Отличная продуктивность! Вы эффективно используете время за экраном.")
        
        # Рекомендации по лимитам
        if not stats["is_within_limit"]:
            recommendations.append("Вы превысили дневной лимит экранного времени. Завтра попробуйте сократить использование.")
        
        if not recommendations:
            recommendations.append("Хороший баланс! Продолжайте в том же духе.")
        
        return recommendations
    
    def _generate_weekly_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Генерирует рекомендации на основе недельной статистики"""
        recommendations = []
        
        avg_daily_hours = stats["average_daily_hours"]
        social_percentage = stats["social_media_percentage"]
        limit_compliance = stats["limit_compliance"]
        
        # Рекомендации по среднему времени
        if avg_daily_hours > 6:
            recommendations.append(f"В среднем вы проводите за экраном {avg_daily_hours:.1f} часов в день. Попробуйте сократить до 4-5 часов.")
        elif avg_daily_hours < 3:
            recommendations.append("Отличная неделя! Вы эффективно контролируете экранное время.")
        
        # Рекомендации по соцсетям
        if social_percentage > 40:
            recommendations.append(f"Социальные сети занимают {social_percentage:.1f}% вашего времени. Установите приоритеты.")
        
        # Рекомендации по соблюдению лимитов
        if limit_compliance < 80:
            recommendations.append(f"Вы соблюдали лимиты только {limit_compliance:.1f}% дней. Попробуйте быть более дисциплинированным.")
        
        if not recommendations:
            recommendations.append("Отличная неделя! Вы хорошо контролируете экранное время.")
        
        return recommendations
    
    def _generate_monthly_recommendations(self, stats: Dict[str, Any]) -> List[str]:
        """Генерирует рекомендации на основе месячной статистики"""
        recommendations = []
        
        avg_daily_hours = stats["average_daily_hours"]
        total_hours = stats["total_hours"]
        limit_exceeded_days = stats["limit_exceeded_days"]
        
        # Рекомендации по общему времени
        if total_hours > 200:  # Более 200 часов в месяц
            recommendations.append(f"За месяц вы провели за экраном {total_hours:.0f} часов. Это много! Попробуйте найти альтернативы.")
        
        # Рекомендации по среднему времени
        if avg_daily_hours > 5:
            recommendations.append(f"В среднем {avg_daily_hours:.1f} часов в день. Попробуйте сократить до 3-4 часов.")
        
        # Рекомендации по превышению лимитов
        if limit_exceeded_days > 10:
            recommendations.append(f"Вы превышали лимиты {limit_exceeded_days} дней из {stats.get('total_days', 30)}. Установите более реалистичные цели.")
        
        if not recommendations:
            recommendations.append("Отличный месяц! Вы хорошо контролируете экранное время.")
        
        return recommendations
    
    def get_user_insights(self, user_id: int) -> Dict[str, Any]:
        """Получает инсайты для пользователя"""
        today = date.today()
        
        # Получаем статистику за последние 7 дней
        days_since_monday = today.weekday()
        start_of_week = today - timedelta(days=days_since_monday)
        weekly_stats = self.get_weekly_stats(user_id, start_of_week)
        
        # Получаем статистику за сегодня
        daily_stats = self.get_daily_stats(user_id, today)
        
        insights = {
            "today": daily_stats,
            "this_week": weekly_stats,
            "trends": self._analyze_trends(user_id),
            "goals": self._get_user_goals(user_id),
            "achievements": self._get_achievements(user_id)
        }
        
        return insights
    
    def _analyze_trends(self, user_id: int) -> Dict[str, Any]:
        """Анализирует тренды пользователя"""
        # Получаем данные за последние 30 дней
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        
        records = screen_time_crud.get_user_records(self.db, user_id, start_date, end_date)
        
        if not records:
            return {"message": "Недостаточно данных для анализа трендов"}
        
        # Анализируем тренды
        total_minutes_by_day = {}
        for record in records:
            total_minutes_by_day[record.date] = record.total_minutes
        
        # Сортируем по дате
        sorted_days = sorted(total_minutes_by_day.items())
        
        # Вычисляем тренд
        if len(sorted_days) >= 2:
            first_day = sorted_days[0][1]
            last_day = sorted_days[-1][1]
            trend_direction = "уменьшение" if last_day < first_day else "увеличение" if last_day > first_day else "стабильность"
            trend_percentage = abs((last_day - first_day) / first_day * 100) if first_day > 0 else 0
        else:
            trend_direction = "недостаточно данных"
            trend_percentage = 0
        
        return {
            "trend_direction": trend_direction,
            "trend_percentage": trend_percentage,
            "data_points": len(sorted_days),
            "average_daily_minutes": sum(total_minutes_by_day.values()) / len(total_minutes_by_day) if total_minutes_by_day else 0
        }
    
    def _get_user_goals(self, user_id: int) -> Dict[str, Any]:
        """Получает цели пользователя"""
        # Здесь можно добавить логику получения целей из базы данных
        # Пока возвращаем базовые цели
        return {
            "daily_limit_minutes": 240,  # 4 часа
            "weekly_limit_hours": 28,    # 4 часа в день
            "productivity_goal_percentage": 60,
            "social_media_limit_percentage": 30
        }
    
    def _get_achievements(self, user_id: int) -> List[Dict[str, Any]]:
        """Получает достижения пользователя"""
        achievements = []
        
        # Получаем статистику за последние 7 дней
        today = date.today()
        days_since_monday = today.weekday()
        start_of_week = today - timedelta(days=days_since_monday)
        weekly_stats = self.get_weekly_stats(user_id, start_of_week)
        
        # Проверяем достижения
        if weekly_stats["limit_compliance"] == 100:
            achievements.append({
                "title": "Идеальная неделя",
                "description": "Вы соблюдали лимиты все 7 дней",
                "icon": "🎯"
            })
        
        if weekly_stats["productivity_percentage"] > 70:
            achievements.append({
                "title": "Продуктивность",
                "description": "Более 70% времени было продуктивным",
                "icon": "⚡"
            })
        
        if weekly_stats["average_daily_hours"] < 3:
            achievements.append({
                "title": "Цифровой минимализм",
                "description": "Менее 3 часов в день в среднем",
                "icon": "🌱"
            })
        
        return achievements
