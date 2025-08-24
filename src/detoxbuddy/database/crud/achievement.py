"""
@file: achievement.py
@description: CRUD операции для системы достижений и геймификации
@dependencies: sqlalchemy, datetime, base
@created: 2024-12-19
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from ..models.achievement import Achievement, UserAchievement, UserLevel, AchievementType
from ..models.user import User
from ..models.focus_session import FocusSession, FocusSessionStatus
from ..models.screen_time import ScreenTime
from ..models.reminder import Reminder, ReminderStatus
from .base import CRUDBase


class CRUDAchievement(CRUDBase[Achievement, None, None]):
    """CRUD операции для достижений"""
    
    def get_all_active(self, db: Session) -> List[Achievement]:
        """Получить все активные достижения"""
        stmt = select(Achievement).where(Achievement.is_active == True)
        return db.execute(stmt).scalars().all()
    
    def get_by_type(self, db: Session, achievement_type: AchievementType) -> List[Achievement]:
        """Получить достижения по типу"""
        stmt = select(Achievement).where(
            and_(
                Achievement.type == achievement_type,
                Achievement.is_active == True
            )
        )
        return db.execute(stmt).scalars().all()


class CRUDUserAchievement(CRUDBase[UserAchievement, None, None]):
    """CRUD операции для достижений пользователей"""
    
    def get_user_achievements(self, db: Session, user_id: int) -> List[UserAchievement]:
        """Получить все достижения пользователя"""
        stmt = select(UserAchievement).where(UserAchievement.user_id == user_id)
        return db.execute(stmt).scalars().all()
    
    def get_completed_achievements(self, db: Session, user_id: int) -> List[UserAchievement]:
        """Получить завершенные достижения пользователя"""
        stmt = select(UserAchievement).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.is_completed == True
            )
        )
        return db.execute(stmt).scalars().all()
    
    def get_achievement_progress(self, db: Session, user_id: int, achievement_id: int) -> Optional[UserAchievement]:
        """Получить прогресс по конкретному достижению"""
        stmt = select(UserAchievement).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.achievement_id == achievement_id
            )
        )
        return db.execute(stmt).scalar_one_or_none()
    
    def update_progress(self, db: Session, user_id: int, achievement_id: int, progress: int) -> Optional[UserAchievement]:
        """Обновить прогресс по достижению"""
        user_achievement = self.get_achievement_progress(db, user_id, achievement_id)
        
        if not user_achievement:
            # Создаем новую запись прогресса
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement_id,
                current_progress=progress
            )
            db.add(user_achievement)
        else:
            user_achievement.current_progress = progress
        
        # Проверяем, достигнуто ли условие
        achievement = db.get(Achievement, achievement_id)
        if achievement and progress >= achievement.condition_value and not user_achievement.is_completed:
            user_achievement.is_completed = True
            user_achievement.completed_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user_achievement)
        return user_achievement
    
    def get_recent_achievements(self, db: Session, user_id: int, days: int = 7) -> List[UserAchievement]:
        """Получить недавно полученные достижения"""
        since = datetime.utcnow() - timedelta(days=days)
        stmt = select(UserAchievement).where(
            and_(
                UserAchievement.user_id == user_id,
                UserAchievement.is_completed == True,
                UserAchievement.completed_at >= since
            )
        ).order_by(UserAchievement.completed_at.desc())
        return db.execute(stmt).scalars().all()


class CRUDUserLevel(CRUDBase[UserLevel, None, None]):
    """CRUD операции для уровней пользователей"""
    
    def get_user_level(self, db: Session, user_id: int) -> Optional[UserLevel]:
        """Получить уровень пользователя"""
        stmt = select(UserLevel).where(UserLevel.user_id == user_id)
        return db.execute(stmt).scalar_one_or_none()
    
    def create_user_level(self, db: Session, user_id: int) -> UserLevel:
        """Создать уровень для пользователя"""
        user_level = UserLevel(user_id=user_id)
        db.add(user_level)
        db.commit()
        db.refresh(user_level)
        return user_level
    
    def add_experience(self, db: Session, user_id: int, experience: int) -> Tuple[UserLevel, bool]:
        """Добавить опыт пользователю. Возвращает (уровень, повысился_ли_уровень)"""
        user_level = self.get_user_level(user_id)
        if not user_level:
            user_level = self.create_user_level(db, user_id)
        
        old_level = user_level.level
        user_level.experience += experience
        user_level.total_experience += experience
        user_level.last_activity = datetime.utcnow()
        
        # Проверяем повышение уровня
        level_increased = False
        while user_level.experience >= user_level.experience_to_next_level:
            user_level.experience -= user_level.experience_to_next_level
            user_level.level += 1
            level_increased = True
        
        db.commit()
        db.refresh(user_level)
        
        return user_level, level_increased
    
    def update_achievements_count(self, db: Session, user_id: int, count: int) -> UserLevel:
        """Обновить количество достижений"""
        user_level = self.get_user_level(db, user_id)
        if not user_level:
            user_level = self.create_user_level(db, user_id)
        
        user_level.achievements_count = count
        db.commit()
        db.refresh(user_level)
        return user_level
    
    def update_streak_days(self, db: Session, user_id: int, streak_days: int) -> UserLevel:
        """Обновить серию дней"""
        user_level = self.get_user_level(user_id)
        if not user_level:
            user_level = self.create_user_level(db, user_id)
        
        user_level.streak_days = streak_days
        if streak_days > user_level.max_streak_days:
            user_level.max_streak_days = streak_days
        
        db.commit()
        db.refresh(user_level)
        return user_level


class AchievementService:
    """Сервис для работы с достижениями"""
    
    def __init__(self):
        self.achievement_crud = CRUDAchievement(Achievement)
        self.user_achievement_crud = CRUDUserAchievement(UserAchievement)
        self.user_level_crud = CRUDUserLevel(UserLevel)
    
    def check_focus_session_achievements(self, db: Session, user_id: int) -> List[UserAchievement]:
        """Проверить достижения по сессиям фокуса"""
        # Получаем все достижения по сессиям фокуса
        achievements = self.achievement_crud.get_by_type(db, AchievementType.FOCUS_SESSIONS)
        completed_achievements = []
        
        for achievement in achievements:
            # Подсчитываем количество завершенных сессий
            stmt = select(func.count(FocusSession.id)).where(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.status == FocusSessionStatus.COMPLETED
                )
            )
            completed_sessions = db.execute(stmt).scalar()
            
            # Обновляем прогресс
            user_achievement = self.user_achievement_crud.update_progress(
                db, user_id, achievement.id, completed_sessions
            )
            
            if user_achievement and user_achievement.is_completed:
                completed_achievements.append(user_achievement)
        
        return completed_achievements
    
    def check_screen_time_achievements(self, db: Session, user_id: int) -> List[UserAchievement]:
        """Проверить достижения по сокращению экранного времени"""
        achievements = self.achievement_crud.get_by_type(db, AchievementType.SCREEN_TIME_REDUCTION)
        completed_achievements = []
        
        for achievement in achievements:
            # Подсчитываем среднее время за последние 7 дней
            week_ago = datetime.utcnow() - timedelta(days=7)
            stmt = select(func.avg(ScreenTime.total_minutes)).where(
                and_(
                    ScreenTime.user_id == user_id,
                    ScreenTime.date >= week_ago
                )
            )
            avg_time = db.execute(stmt).scalar() or 0
            
            # Обновляем прогресс (меньше времени = больше прогресса)
            progress = max(0, int(480 - avg_time))  # 8 часов = 480 минут
            user_achievement = self.user_achievement_crud.update_progress(
                db, user_id, achievement.id, progress
            )
            
            if user_achievement and user_achievement.is_completed:
                completed_achievements.append(user_achievement)
        
        return completed_achievements
    
    def check_streak_achievements(self, db: Session, user_id: int) -> List[UserAchievement]:
        """Проверить достижения по сериям дней"""
        achievements = self.achievement_crud.get_by_type(db, AchievementType.STREAK_DAYS)
        completed_achievements = []
        
        # Получаем текущую серию дней пользователя
        user_level = self.user_level_crud.get_user_level(db, user_id)
        streak_days = user_level.streak_days if user_level else 0
        
        for achievement in achievements:
            user_achievement = self.user_achievement_crud.update_progress(
                db, user_id, achievement.id, streak_days
            )
            
            if user_achievement and user_achievement.is_completed:
                completed_achievements.append(user_achievement)
        
        return completed_achievements
    
    def check_reminder_achievements(self, db: Session, user_id: int) -> List[UserAchievement]:
        """Проверить достижения по выполненным напоминаниям"""
        achievements = self.achievement_crud.get_by_type(db, AchievementType.REMINDERS_COMPLETED)
        completed_achievements = []
        
        for achievement in achievements:
            # Подсчитываем выполненные напоминания
            stmt = select(func.count(Reminder.id)).where(
                and_(
                    Reminder.user_id == user_id,
                    Reminder.status == ReminderStatus.SENT
                )
            )
            completed_reminders = db.execute(stmt).scalar()
            
            user_achievement = self.user_achievement_crud.update_progress(
                db, user_id, achievement.id, completed_reminders
            )
            
            if user_achievement and user_achievement.is_completed:
                completed_achievements.append(user_achievement)
        
        return completed_achievements
    
    def check_all_achievements(self, db: Session, user_id: int) -> List[UserAchievement]:
        """Проверить все достижения пользователя"""
        all_completed = []
        
        all_completed.extend(self.check_focus_session_achievements(db, user_id))
        all_completed.extend(self.check_screen_time_achievements(db, user_id))
        all_completed.extend(self.check_streak_achievements(db, user_id))
        all_completed.extend(self.check_reminder_achievements(db, user_id))
        
        # Обновляем количество достижений в уровне
        completed_count = len(self.user_achievement_crud.get_completed_achievements(db, user_id))
        self.user_level_crud.update_achievements_count(db, user_id, completed_count)
        
        return all_completed
    
    def award_experience_for_achievement(self, db: Session, user_id: int, achievement: Achievement) -> Tuple[UserLevel, bool]:
        """Наградить опытом за достижение"""
        return self.user_level_crud.add_experience(db, user_id, achievement.points)


# Создаем экземпляры для использования
achievement_crud = CRUDAchievement(Achievement)
user_achievement_crud = CRUDUserAchievement(UserAchievement)
user_level_crud = CRUDUserLevel(UserLevel)
achievement_service = AchievementService()
