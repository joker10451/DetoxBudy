"""
@file: focus_session.py
@description: CRUD операции для сессий фокуса (Pomodoro)
@dependencies: sqlalchemy, datetime, models
@created: 2024-12-19
"""

from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from ..models.focus_session import FocusSession, FocusSessionStatus, FocusSessionType
from .base import CRUDBase


class CRUDFocusSession(CRUDBase[FocusSession, None, None]):
    """CRUD операции для сессий фокуса"""

    def get_active_session(self, db: Session, user_id: int) -> Optional[FocusSession]:
        """Получить активную сессию пользователя"""
        return db.query(FocusSession).filter(
            and_(
                FocusSession.user_id == user_id,
                FocusSession.status.in_([FocusSessionStatus.ACTIVE, FocusSessionStatus.PAUSED])
            )
        ).first()

    def get_user_sessions(
        self, 
        db: Session, 
        user_id: Optional[int] = None, 
        limit: int = 50,
        status: Optional[FocusSessionStatus] = None
    ) -> List[FocusSession]:
        """Получить сессии пользователя или все сессии"""
        query = db.query(FocusSession)
        
        if user_id is not None:
            query = query.filter(FocusSession.user_id == user_id)
        
        if status:
            query = query.filter(FocusSession.status == status)
        
        return query.order_by(desc(FocusSession.created_at)).limit(limit).all()

    def create_focus_session(
        self,
        db: Session,
        user_id: int,
        session_type: FocusSessionType = FocusSessionType.FOCUS,
        duration_minutes: int = 25,
        title: Optional[str] = None,
        description: Optional[str] = None,
        auto_start_next: bool = False
    ) -> FocusSession:
        """Создать новую сессию фокуса"""
        planned_start = datetime.now()
        
        session = FocusSession(
            user_id=user_id,
            session_type=session_type,
            planned_duration=duration_minutes,
            title=title or f"{session_type.value.title()} Session",
            description=description,
            planned_start=planned_start,
            auto_start_next=auto_start_next
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def start_session(self, db: Session, session_id: int) -> Optional[FocusSession]:
        """Запустить сессию"""
        session = self.get(db, session_id)
        if not session or session.status != FocusSessionStatus.PLANNED:
            return None
        
        session.status = FocusSessionStatus.ACTIVE
        session.actual_start = datetime.now()
        session.updated_at = datetime.now()
        
        db.commit()
        db.refresh(session)
        return session

    def pause_session(self, db: Session, session_id: int) -> Optional[FocusSession]:
        """Приостановить сессию"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Attempting to pause session {session_id}")
        session = self.get(db, session_id)
        logger.info(f"Retrieved session: {session}")
        
        if not session:
            logger.warning(f"Session {session_id} not found")
            return None
            
        if session.status != FocusSessionStatus.ACTIVE:
            logger.warning(f"Session {session_id} status is {session.status}, expected ACTIVE")
            return None
        
        session.status = FocusSessionStatus.PAUSED
        session.last_pause_start = datetime.now()
        session.updated_at = datetime.now()
        
        db.commit()
        db.refresh(session)
        logger.info(f"Successfully paused session {session_id}")
        return session

    def resume_session(self, db: Session, session_id: int) -> Optional[FocusSession]:
        """Возобновить сессию"""
        session = self.get(db, session_id)
        if not session or session.status != FocusSessionStatus.PAUSED:
            return None
        
        # Вычисляем время паузы
        if session.last_pause_start:
            pause_duration = int((datetime.now() - session.last_pause_start).total_seconds() / 60)
            session.paused_duration += pause_duration
        
        session.status = FocusSessionStatus.ACTIVE
        session.last_pause_start = None
        session.updated_at = datetime.now()
        
        db.commit()
        db.refresh(session)
        return session

    def complete_session(self, db: Session, session_id: int) -> Optional[FocusSession]:
        """Завершить сессию"""
        session = self.get(db, session_id)
        if not session or session.status not in [FocusSessionStatus.ACTIVE, FocusSessionStatus.PAUSED]:
            return None
        
        session.status = FocusSessionStatus.COMPLETED
        session.actual_end = datetime.now()
        
        # Вычисляем фактическую длительность
        if session.actual_start:
            total_duration = int((session.actual_end - session.actual_start).total_seconds() / 60)
            session.actual_duration = total_duration
        
        # Вычисляем процент выполнения
        session.completion_rate = session.calculate_completion_rate()
        session.updated_at = datetime.now()
        
        db.commit()
        db.refresh(session)
        
        # Проверяем достижения после завершения сессии
        try:
            from ..crud.achievement import achievement_service, user_level_crud
            
            # Проверяем достижения
            completed_achievements = achievement_service.check_focus_session_achievements(db, session.user_id)
            
            # Награждаем опытом за завершение сессии
            experience_gained = 10  # Базовый опыт за сессию
            if session.actual_duration and session.actual_duration >= 45:
                experience_gained += 5  # Бонус за длительную сессию
            
            user_level, level_increased = user_level_crud.add_experience(db, session.user_id, experience_gained)
            
            # Награждаем опытом за достижения
            for ua in completed_achievements:
                achievement_service.award_experience_for_achievement(db, session.user_id, ua.achievement)
            
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            import logging
            logging.error(f"Error checking achievements after session completion: {e}")
        
        return session

    def cancel_session(self, db: Session, session_id: int) -> Optional[FocusSession]:
        """Отменить сессию"""
        session = self.get(db, session_id)
        if not session or session.status == FocusSessionStatus.COMPLETED:
            return None
        
        session.status = FocusSessionStatus.CANCELLED
        session.actual_end = datetime.now()
        session.updated_at = datetime.now()
        
        db.commit()
        db.refresh(session)
        return session

    def get_user_stats(
        self, 
        db: Session, 
        user_id: int, 
        days: int = 7
    ) -> dict:
        """Получить статистику пользователя"""
        start_date = datetime.now() - timedelta(days=days)
        
        sessions = db.query(FocusSession).filter(
            and_(
                FocusSession.user_id == user_id,
                FocusSession.created_at >= start_date,
                FocusSession.status == FocusSessionStatus.COMPLETED
            )
        ).all()
        
        total_sessions = len(sessions)
        total_focus_time = sum(s.effective_duration_minutes for s in sessions)
        total_breaks = len([s for s in sessions if s.session_type != FocusSessionType.FOCUS])
        
        avg_completion_rate = 0
        if sessions:
            avg_completion_rate = sum(s.completion_rate or 0 for s in sessions) / len(sessions)
        
        return {
            "total_sessions": total_sessions,
            "total_focus_time_minutes": total_focus_time,
            "total_breaks": total_breaks,
            "avg_completion_rate": round(avg_completion_rate, 2),
            "period_days": days
        }

    def get_today_sessions(self, db: Session, user_id: int) -> List[FocusSession]:
        """Получить сессии за сегодня"""
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        return db.query(FocusSession).filter(
            and_(
                FocusSession.user_id == user_id,
                FocusSession.created_at >= today_start,
                FocusSession.created_at < today_end
            )
        ).order_by(FocusSession.created_at).all()

    def get_streak_days(self, db: Session, user_id: int) -> int:
        """Получить количество дней подряд с завершенными сессиями"""
        current_date = datetime.now().date()
        streak = 0
        
        for i in range(365):  # Максимум год назад
            check_date = current_date - timedelta(days=i)
            start_datetime = datetime.combine(check_date, datetime.min.time())
            end_datetime = start_datetime + timedelta(days=1)
            
            sessions = db.query(FocusSession).filter(
                and_(
                    FocusSession.user_id == user_id,
                    FocusSession.created_at >= start_datetime,
                    FocusSession.created_at < end_datetime,
                    FocusSession.status == FocusSessionStatus.COMPLETED
                )
            ).count()
            
            if sessions > 0:
                streak += 1
            else:
                break
        
        return streak


focus_session = CRUDFocusSession(FocusSession)
