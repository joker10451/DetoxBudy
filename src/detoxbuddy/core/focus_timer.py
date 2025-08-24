"""
@file: focus_timer.py
@description: Планировщик таймера фокуса (Pomodoro) с использованием APScheduler
@dependencies: apscheduler, datetime, telegram
@created: 2024-12-19
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from ..database.crud.focus_session import focus_session
from ..database.models.focus_session import FocusSession, FocusSessionStatus, FocusSessionType
# Убираем циклический импорт - будем использовать TYPE_CHECKING
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..telegram.bot.telegram_bot import TelegramBot
from ..core.config import get_settings

logger = logging.getLogger(__name__)


class FocusTimer:
    """
    Планировщик таймера фокуса с техникой Pomodoro.
    Управляет сессиями фокуса, перерывами и уведомлениями.
    """
    
    def __init__(self, telegram_bot: "TelegramBot"):
        self.telegram_bot = telegram_bot
        self.scheduler = AsyncIOScheduler()
        self.active_sessions: Dict[int, Dict[str, Any]] = {}  # user_id -> session_info
        self.settings = get_settings()
        
        # Кэш для пользователей (уменьшает нагрузку на БД)
        self._user_cache: Dict[int, Dict[str, Any]] = {}
        self._cache_ttl = 300  # 5 минут
        
        # Настройки Pomodoro (по умолчанию)
        self.focus_duration = 25  # минуты
        self.short_break_duration = 5  # минуты
        self.long_break_duration = 15  # минуты
        self.sessions_before_long_break = 4
        
    async def start(self):
        """Запустить планировщик"""
        try:
            self.scheduler.start()
            logger.info("Focus timer scheduler started successfully")
            
            # Восстанавливаем активные сессии из базы данных
            await self._restore_active_sessions()
            
        except Exception as e:
            logger.error(f"Failed to start focus timer scheduler: {e}")
    
    async def _restore_active_sessions(self):
        """Восстановить активные сессии из базы данных"""
        try:
            from ..database.database import get_db
            
            db = next(get_db())
            
            # Получаем все активные и приостановленные сессии
            active_sessions = focus_session.get_user_sessions(
                db, 
                user_id=None,  # Получаем все сессии
                status=None,   # Все статусы
                limit=100
            )
            
            for session in active_sessions:
                if session.status in [FocusSessionStatus.ACTIVE, FocusSessionStatus.PAUSED]:
                    # Восстанавливаем информацию о сессии в памяти
                    self.active_sessions[session.user_id] = {
                        "session_id": session.id,
                        "start_time": session.actual_start or session.created_at,
                        "duration_minutes": session.planned_duration,
                        "session_type": session.session_type,
                        "sessions_completed": 0
                    }
                    
                    logger.info(f"Restored active session for user {session.user_id}: {session.id}")
            
            logger.info(f"Restored {len(self.active_sessions)} active sessions from database")
            
        except Exception as e:
            logger.error(f"Error restoring active sessions: {e}")
    
    async def stop(self):
        """Остановить планировщик"""
        try:
            self.scheduler.shutdown()
            logger.info("Focus timer scheduler stopped")
        except Exception as e:
            logger.error(f"Failed to stop focus timer scheduler: {e}")
    
    def start_focus_session(
        self, 
        user_id: int, 
        duration_minutes: int = 25,
        title: Optional[str] = None,
        auto_start_next: bool = True
    ) -> Optional[FocusSession]:
        """Запустить сессию фокуса"""
        try:
            from ..database.database import get_db
            
            db = next(get_db())
            
            # Проверяем, нет ли уже активной сессии
            active_session = focus_session.get_active_session(db, user_id)
            if active_session:
                logger.warning(f"User {user_id} already has an active session")
                return active_session
            
            # Создаем новую сессию
            session = focus_session.create_focus_session(
                db=db,
                user_id=user_id,
                session_type=FocusSessionType.FOCUS,
                duration_minutes=duration_minutes,
                title=title or f"Focus Session ({duration_minutes}min)",
                auto_start_next=auto_start_next
            )
            
            # Запускаем сессию
            session = focus_session.start_session(db, session.id)
            if not session:
                logger.error(f"Failed to start session for user {user_id}")
                return None
            
            # Сохраняем информацию о сессии
            self.active_sessions[user_id] = {
                "session_id": session.id,
                "start_time": datetime.now(),
                "duration_minutes": duration_minutes,
                "session_type": FocusSessionType.FOCUS,
                "sessions_completed": 0
            }
            
            # Планируем завершение сессии
            end_time = datetime.now() + timedelta(minutes=duration_minutes)
            self.scheduler.add_job(
                self._complete_focus_session,
                DateTrigger(run_date=end_time),
                args=[user_id],
                id=f"focus_complete_{user_id}_{session.id}",
                replace_existing=True
            )
            
            # Планируем промежуточные уведомления
            self._schedule_progress_notifications(user_id, duration_minutes, session.id)
            
            logger.info(f"Started focus session for user {user_id}, duration: {duration_minutes}min")
            return session
            
        except Exception as e:
            logger.error(f"Error starting focus session for user {user_id}: {e}")
            return None
    
    def pause_session(self, user_id: int) -> bool:
        """Приостановить сессию"""
        try:
            from ..database.database import get_db
            
            db = next(get_db())
            
            logger.info(f"Attempting to pause session for user {user_id}")
            logger.info(f"Active sessions: {list(self.active_sessions.keys())}")
            
            if user_id not in self.active_sessions:
                logger.warning(f"User {user_id} not in active_sessions")
                return False
            
            session_info = self.active_sessions[user_id]
            logger.info(f"Session info for user {user_id}: {session_info}")
            
            session = focus_session.pause_session(db, session_info["session_id"])
            logger.info(f"Pause session result: {session}")
            
            if session:
                # Останавливаем планировщик завершения
                job_id = f"focus_complete_{user_id}_{session_info['session_id']}"
                try:
                    self.scheduler.remove_job(job_id)
                except Exception:
                    # Задача может не существовать, это нормально
                    pass
                
                # Останавливаем уведомления о прогрессе
                self._remove_progress_notifications(user_id, session_info['session_id'])
                
                logger.info(f"Paused focus session for user {user_id}")
                return True
            
            logger.warning(f"Failed to pause session for user {user_id} - session object is None")
            return False
            
        except Exception as e:
            logger.error(f"Error pausing session for user {user_id}: {e}")
            return False
    
    def resume_session(self, user_id: int) -> bool:
        """Возобновить сессию"""
        try:
            from ..database.database import get_db
            
            db = next(get_db())
            
            if user_id not in self.active_sessions:
                return False
            
            session_info = self.active_sessions[user_id]
            session = focus_session.resume_session(db, session_info["session_id"])
            
            if session:
                # Вычисляем оставшееся время
                elapsed_time = datetime.now() - session_info["start_time"]
                remaining_minutes = max(0, session_info["duration_minutes"] - int(elapsed_time.total_seconds() / 60))
                
                if remaining_minutes > 0:
                    # Планируем завершение сессии
                    end_time = datetime.now() + timedelta(minutes=remaining_minutes)
                    self.scheduler.add_job(
                        self._complete_focus_session,
                        DateTrigger(run_date=end_time),
                        args=[user_id],
                        id=f"focus_complete_{user_id}_{session_info['session_id']}",
                        replace_existing=True
                    )
                    
                    # Планируем промежуточные уведомления
                    self._schedule_progress_notifications(user_id, remaining_minutes, session_info['session_id'])
                
                logger.info(f"Resumed focus session for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error resuming session for user {user_id}: {e}")
            return False
    
    def cancel_session(self, user_id: int) -> bool:
        """Отменить сессию"""
        try:
            from ..database.database import get_db
            
            db = next(get_db())
            
            if user_id not in self.active_sessions:
                return False
            
            session_info = self.active_sessions[user_id]
            session = focus_session.cancel_session(db, session_info["session_id"])
            
            if session:
                # Останавливаем планировщик
                job_id = f"focus_complete_{user_id}_{session_info['session_id']}"
                try:
                    self.scheduler.remove_job(job_id)
                except Exception:
                    # Задача может не существовать, это нормально
                    pass
                
                # Останавливаем уведомления
                self._remove_progress_notifications(user_id, session_info['session_id'])
                
                # Удаляем из активных сессий
                del self.active_sessions[user_id]
                
                logger.info(f"Cancelled focus session for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error cancelling session for user {user_id}: {e}")
            return False
    
    async def _complete_focus_session(self, user_id: int):
        """Завершить сессию фокуса"""
        try:
            from ..database.database import get_db
            
            db = next(get_db())
            
            if user_id not in self.active_sessions:
                return
            
            session_info = self.active_sessions[user_id]
            session = focus_session.complete_session(db, session_info["session_id"])
            
            if session:
                # Увеличиваем счетчик завершенных сессий
                session_info["sessions_completed"] += 1
                
                # Отправляем уведомление о завершении
                await self._send_session_complete_notification(user_id, session)
                
                # Проверяем, нужно ли начать перерыв
                if session_info["sessions_completed"] % self.sessions_before_long_break == 0:
                    await self._start_long_break(user_id)
                else:
                    await self._start_short_break(user_id)
                
                # Удаляем из активных сессий
                del self.active_sessions[user_id]
                
                logger.info(f"Completed focus session for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error completing focus session for user {user_id}: {e}")
    
    async def _start_short_break(self, user_id: int):
        """Начать короткий перерыв"""
        try:
            from ..database.database import get_db
            
            db = next(get_db())
            
            # Создаем сессию короткого перерыва
            session = focus_session.create_focus_session(
                db=db,
                user_id=user_id,
                session_type=FocusSessionType.SHORT_BREAK,
                duration_minutes=self.short_break_duration,
                title="Short Break",
                auto_start_next=True
            )
            
            # Запускаем сессию
            session = focus_session.start_session(db, session.id)
            
            if session:
                # Сохраняем информацию о перерыве
                self.active_sessions[user_id] = {
                    "session_id": session.id,
                    "start_time": datetime.now(),
                    "duration_minutes": self.short_break_duration,
                    "session_type": FocusSessionType.SHORT_BREAK,
                    "sessions_completed": 0
                }
                
                # Планируем завершение перерыва
                end_time = datetime.now() + timedelta(minutes=self.short_break_duration)
                self.scheduler.add_job(
                    self._complete_break_session,
                    DateTrigger(run_date=end_time),
                    args=[user_id],
                    id=f"break_complete_{user_id}_{session.id}",
                    replace_existing=True
                )
                
                # Отправляем уведомление о начале перерыва
                await self._send_break_start_notification(user_id, "short")
                
                logger.info(f"Started short break for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error starting short break for user {user_id}: {e}")
    
    async def _start_long_break(self, user_id: int):
        """Начать длинный перерыв"""
        try:
            from ..database.database import get_db
            
            db = next(get_db())
            
            # Создаем сессию длинного перерыва
            session = focus_session.create_focus_session(
                db=db,
                user_id=user_id,
                session_type=FocusSessionType.LONG_BREAK,
                duration_minutes=self.long_break_duration,
                title="Long Break",
                auto_start_next=True
            )
            
            # Запускаем сессию
            session = focus_session.start_session(db, session.id)
            
            if session:
                # Сохраняем информацию о перерыве
                self.active_sessions[user_id] = {
                    "session_id": session.id,
                    "start_time": datetime.now(),
                    "duration_minutes": self.long_break_duration,
                    "session_type": FocusSessionType.LONG_BREAK,
                    "sessions_completed": 0
                }
                
                # Планируем завершение перерыва
                end_time = datetime.now() + timedelta(minutes=self.long_break_duration)
                self.scheduler.add_job(
                    self._complete_break_session,
                    DateTrigger(run_date=end_time),
                    args=[user_id],
                    id=f"break_complete_{user_id}_{session.id}",
                    replace_existing=True
                )
                
                # Отправляем уведомление о начале перерыва
                await self._send_break_start_notification(user_id, "long")
                
                logger.info(f"Started long break for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error starting long break for user {user_id}: {e}")
    
    async def _complete_break_session(self, user_id: int):
        """Завершить перерыв"""
        try:
            from ..database.database import get_db
            
            db = next(get_db())
            
            if user_id not in self.active_sessions:
                return
            
            session_info = self.active_sessions[user_id]
            session = focus_session.complete_session(db, session_info["session_id"])
            
            if session:
                # Отправляем уведомление о завершении перерыва
                await self._send_break_complete_notification(user_id, session_info["session_type"])
                
                # Удаляем из активных сессий
                del self.active_sessions[user_id]
                
                logger.info(f"Completed break session for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error completing break session for user {user_id}: {e}")
    
    def _schedule_progress_notifications(self, user_id: int, duration_minutes: int, session_id: int):
        """Планировать уведомления о прогрессе"""
        # Уведомления каждые 5 минут
        for i in range(5, duration_minutes, 5):
            notification_time = datetime.now() + timedelta(minutes=i)
            self.scheduler.add_job(
                self._send_progress_notification,
                DateTrigger(run_date=notification_time),
                args=[user_id, i, duration_minutes],
                id=f"progress_{user_id}_{session_id}_{i}",
                replace_existing=True
            )
    
    def _remove_progress_notifications(self, user_id: int, session_id: int):
        """Удалить уведомления о прогрессе"""
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            if job.id.startswith(f"progress_{user_id}_{session_id}_"):
                try:
                    self.scheduler.remove_job(job.id)
                except Exception:
                    # Задача может не существовать, это нормально
                    pass
    
    def _remove_user_notifications(self, user_id: int):
        """Удалить все уведомления для пользователя"""
        try:
            jobs = self.scheduler.get_jobs()
            removed_count = 0
            for job in jobs:
                if f"_{user_id}_" in job.id:
                    try:
                        self.scheduler.remove_job(job.id)
                        removed_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove job {job.id}: {e}")
            
            if removed_count > 0:
                logger.info(f"Removed {removed_count} notification jobs for user {user_id}")
            else:
                logger.debug(f"No notification jobs found for user {user_id}")
                
        except Exception as e:
            logger.error(f"Error removing notifications for user {user_id}: {e}")
    
    async def _send_session_complete_notification(self, user_id: int, session: FocusSession):
        """Отправить уведомление о завершении сессии"""
        try:
            message = (
                f"🎉 *Сессия фокуса завершена!*\n\n"
                f"📊 **Статистика сессии:**\n"
                f"• Длительность: {session.effective_duration_minutes} мин\n"
                f"• Процент выполнения: {session.completion_rate or 0:.1f}%\n"
                f"• Перерывы: {session.paused_duration} мин\n\n"
                f"Отличная работа! 💪"
            )
            
            result = await self.telegram_bot.send_message(user_id, message, parse_mode="Markdown")
            if result is None:
                logger.warning(f"Failed to send session complete notification to user {user_id} (chat not found or bot blocked)")
            
        except Exception as e:
            error_msg = str(e).lower()
            if "chat not found" in error_msg or "bot was blocked" in error_msg or "forbidden" in error_msg:
                logger.warning(f"User {user_id} blocked bot or chat not found: {e}")
            else:
                logger.error(f"Error sending session complete notification to user {user_id}: {e}")
    
    async def _send_break_start_notification(self, user_id: int, break_type: str):
        """Отправить уведомление о начале перерыва"""
        try:
            if break_type == "short":
                message = (
                    f"☕ *Короткий перерыв!*\n\n"
                    f"⏰ Длительность: {self.short_break_duration} минут\n\n"
                    f"Время расслабиться и восстановить силы! 😌"
                )
            else:
                message = (
                    f"🌴 *Длинный перерыв!*\n\n"
                    f"⏰ Длительность: {self.long_break_duration} минут\n\n"
                    f"Отличная работа! Время для полноценного отдыха! 🎉"
                )
            
            result = await self.telegram_bot.send_message(user_id, message, parse_mode="Markdown")
            if result is None:
                logger.warning(f"Failed to send break start notification to user {user_id} (chat not found or bot blocked)")
            
        except Exception as e:
            error_msg = str(e).lower()
            if "chat not found" in error_msg or "bot was blocked" in error_msg or "forbidden" in error_msg:
                logger.warning(f"User {user_id} blocked bot or chat not found: {e}")
            else:
                logger.error(f"Error sending break start notification to user {user_id}: {e}")
    
    async def _send_break_complete_notification(self, user_id: int, session_type: FocusSessionType):
        """Отправить уведомление о завершении перерыва"""
        try:
            if session_type == FocusSessionType.SHORT_BREAK:
                message = (
                    f"⏰ *Перерыв завершен!*\n\n"
                    f"Готовы к следующей сессии фокуса? 🚀\n\n"
                    f"Используйте /focus для начала новой сессии"
                )
            else:
                message = (
                    f"⏰ *Длинный перерыв завершен!*\n\n"
                    f"Отдохнули? Время вернуться к работе! 💪\n\n"
                    f"Используйте /focus для начала новой сессии"
                )
            
            result = await self.telegram_bot.send_message(user_id, message, parse_mode="Markdown")
            if result is None:
                logger.warning(f"Failed to send break complete notification to user {user_id} (chat not found or bot blocked)")
            
        except Exception as e:
            error_msg = str(e).lower()
            if "chat not found" in error_msg or "bot was blocked" in error_msg or "forbidden" in error_msg:
                logger.warning(f"User {user_id} blocked bot or chat not found: {e}")
            else:
                logger.error(f"Error sending break complete notification to user {user_id}: {e}")
    
    async def _send_progress_notification(self, user_id: int, elapsed_minutes: int, total_minutes: int):
        """Отправить уведомление о прогрессе"""
        try:
            progress_percent = (elapsed_minutes / total_minutes) * 100
            remaining_minutes = total_minutes - elapsed_minutes
            
            message = (
                f"⏱️ *Прогресс сессии*\n\n"
                f"📈 Выполнено: {progress_percent:.0f}%\n"
                f"⏰ Прошло: {elapsed_minutes} мин\n"
                f"🕐 Осталось: {remaining_minutes} мин\n\n"
                f"Продолжайте в том же духе! 💪"
            )
            
            result = await self.telegram_bot.send_message(user_id, message, parse_mode="Markdown")
            
            # Если сообщение не отправлено (пользователь заблокировал бота или чат не найден), 
            # прекращаем отправку уведомлений для этого пользователя
            if result is None:
                logger.warning(f"Failed to send progress notification to user {user_id} (chat not found or bot blocked), stopping notifications")
                # Удаляем все запланированные уведомления для этого пользователя
                self._remove_user_notifications(user_id)
                # Также удаляем пользователя из активных сессий, если он там есть
                if user_id in self.active_sessions:
                    del self.active_sessions[user_id]
                return
            
        except Exception as e:
            error_msg = str(e).lower()
            if "chat not found" in error_msg or "bot was blocked" in error_msg or "forbidden" in error_msg:
                logger.warning(f"User {user_id} blocked bot or chat not found: {e}")
                # Удаляем все запланированные уведомления для этого пользователя
                self._remove_user_notifications(user_id)
                # Также удаляем пользователя из активных сессий, если он там есть
                if user_id in self.active_sessions:
                    del self.active_sessions[user_id]
            else:
                logger.error(f"Error sending progress notification to user {user_id}: {e}")
                # При критических ошибках также прекращаем уведомления
                self._remove_user_notifications(user_id)
    
    def get_session_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о текущей сессии пользователя"""
        return self.active_sessions.get(user_id)
    
    def is_user_in_session(self, user_id: int) -> bool:
        """Проверить, находится ли пользователь в сессии"""
        return user_id in self.active_sessions
    
    def _get_cached_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить пользователя из кэша"""
        if user_id in self._user_cache:
            cache_entry = self._user_cache[user_id]
            # Проверяем TTL
            if (datetime.now() - cache_entry['timestamp']).total_seconds() < self._cache_ttl:
                return cache_entry['data']
            else:
                # Удаляем устаревшую запись
                del self._user_cache[user_id]
        return None
    
    def _cache_user(self, user_id: int, user_data: Dict[str, Any]):
        """Кэшировать данные пользователя"""
        self._user_cache[user_id] = {
            'data': user_data,
            'timestamp': datetime.now()
        }
    
    def _clear_user_cache(self, user_id: int = None):
        """Очистить кэш пользователя"""
        if user_id:
            self._user_cache.pop(user_id, None)
        else:
            self._user_cache.clear()
