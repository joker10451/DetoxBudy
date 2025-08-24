"""
@file: reminder_scheduler.py
@description: Планировщик напоминаний с использованием APScheduler
@dependencies: apscheduler, sqlalchemy, telegram_bot, models, crud
@created: 2024-12-19
@updated: 2024-12-19 - Интеграция APScheduler
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from threading import Thread, Event

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from sqlalchemy.orm import Session

from detoxbuddy.database.database import SessionLocal, engine
from detoxbuddy.database.crud.reminder import reminder_crud
from detoxbuddy.database.models.reminder import Reminder, ReminderStatus, ReminderType
from detoxbuddy.core.config_simple import settings

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Планировщик напоминаний с использованием APScheduler"""
    
    def __init__(self):
        self.running = False
        self.stop_event = Event()
        self.telegram_bot = None
        
        # Настройка APScheduler
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///reminder_jobs.sqlite')
        }
        
        job_defaults = {
            'coalesce': False,
            'max_instances': 3,
            'misfire_grace_time': 300  # 5 минут
        }
        
        self.scheduler = BackgroundScheduler(
            jobstores=jobstores,
            job_defaults=job_defaults,
            timezone=timezone.utc
        )
        
    async def initialize_bot(self):
        """Инициализирует Telegram бота"""
        try:
            from detoxbuddy.telegram.bot.telegram_bot import TelegramBot
            self.telegram_bot = TelegramBot()
            logger.info("Telegram бот инициализирован для напоминаний")
        except Exception as e:
            logger.error(f"Ошибка инициализации Telegram бота: {e}")
    
    async def start(self):
        """Запускает планировщик"""
        if self.running:
            logger.warning("Планировщик уже запущен")
            return
        
        try:
            # Инициализируем бота
            await self.initialize_bot()
            
            # Запускаем APScheduler
            self.scheduler.start()
            
            # Загружаем существующие напоминания
            self._load_existing_reminders()
            
            self.running = True
            logger.info("Планировщик напоминаний запущен с APScheduler")
            
        except Exception as e:
            logger.error(f"Ошибка запуска планировщика: {e}")
            raise
    
    def stop(self):
        """Останавливает планировщик"""
        if not self.running:
            return
            
        self.running = False
        self.stop_event.set()
        
        if self.scheduler.running:
            self.scheduler.shutdown()
        
        logger.info("Планировщик напоминаний остановлен")
    
    def _load_existing_reminders(self):
        """Загружает существующие активные напоминания в планировщик"""
        try:
            with SessionLocal() as db:
                active_reminders = reminder_crud.get_active_reminders(db)
                
                for reminder in active_reminders:
                    self._schedule_reminder(reminder)
                
                logger.info(f"Загружено {len(active_reminders)} активных напоминаний")
                
        except Exception as e:
            logger.error(f"Ошибка загрузки существующих напоминаний: {e}")
    
    def _schedule_reminder(self, reminder: Reminder):
        """Планирует напоминание в APScheduler"""
        try:
            job_id = f"reminder_{reminder.id}"
            
            # Удаляем существующую задачу если есть
            try:
                self.scheduler.remove_job(job_id)
            except:
                pass
            
            if reminder.is_recurring and reminder.repeat_interval:
                # Повторяющееся напоминание
                trigger = IntervalTrigger(
                    minutes=reminder.repeat_interval,
                    start_date=reminder.scheduled_time,
                    end_date=reminder.expires_at
                )
            elif reminder.reminder_type == ReminderType.DAILY and reminder.reminder_time:
                # Ежедневное напоминание
                trigger = CronTrigger(
                    hour=reminder.reminder_time.hour,
                    minute=reminder.reminder_time.minute
                )
            elif reminder.reminder_type == ReminderType.WEEKLY and reminder.repeat_days:
                # Еженедельное напоминание
                try:
                    days = json.loads(reminder.repeat_days)
                    trigger = CronTrigger(
                        day_of_week=','.join(days),
                        hour=reminder.scheduled_time.hour,
                        minute=reminder.scheduled_time.minute
                    )
                except:
                    # Fallback к однократному
                    trigger = DateTrigger(run_date=reminder.scheduled_time)
            else:
                # Однократное напоминание
                trigger = DateTrigger(run_date=reminder.scheduled_time)
            
            # Добавляем задачу в планировщик
            self.scheduler.add_job(
                func=self._send_reminder_job,
                trigger=trigger,
                id=job_id,
                args=[reminder.id],
                replace_existing=True,
                max_instances=1
            )
            
            logger.info(f"Напоминание {reminder.id} запланировано в APScheduler")
            
        except Exception as e:
            logger.error(f"Ошибка планирования напоминания {reminder.id}: {e}")
    
    def _send_reminder_job(self, reminder_id: int):
        """Задача для отправки напоминания (вызывается APScheduler)"""
        try:
            with SessionLocal() as db:
                reminder = reminder_crud.get(db, reminder_id)
                if not reminder:
                    logger.warning(f"Напоминание {reminder_id} не найдено")
                    return
                
                if not reminder.is_active:
                    logger.info(f"Напоминание {reminder_id} неактивно")
                    return
                
                # Отправляем напоминание
                self._send_reminder(reminder, db)
                
                # Если это повторяющееся напоминание, планируем следующее
                if reminder.is_recurring and reminder.repeat_interval:
                    self._schedule_next_recurring_reminder(reminder, db)
                
        except Exception as e:
            logger.error(f"Ошибка в задаче отправки напоминания {reminder_id}: {e}")
    
    def _send_reminder(self, reminder: Reminder, db: Session):
        """Отправляет напоминание через Telegram"""
        try:
            user = reminder.user
            if not user or not user.telegram_id:
                logger.warning(f"Пользователь не найден для напоминания {reminder.id}")
                return
            
            # Создаем новую задачу для асинхронной отправки
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                loop.run_until_complete(self._send_telegram_reminder(reminder, user.telegram_id))
                
                # Помечаем как отправленное
                reminder_crud.mark_as_sent(db, reminder.id)
                logger.info(f"Напоминание {reminder.id} отправлено")
                
            finally:
                loop.close()
                
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания {reminder.id}: {e}")
            reminder_crud.mark_as_failed(db, reminder.id)
    
    async def _send_telegram_reminder(self, reminder: Reminder, user_telegram_id: int):
        """Отправляет напоминание через Telegram"""
        try:
            from detoxbuddy.telegram.bot.telegram_bot import TelegramBot
            
            bot = TelegramBot()
            
            # Формируем сообщение
            message = self._format_reminder_message(reminder)
            
            # Отправляем сообщение
            await bot.send_message(
                chat_id=user_telegram_id,
                text=message,
                parse_mode="Markdown"
            )
            
            logger.info(f"Напоминание отправлено пользователю {user_telegram_id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки напоминания через Telegram: {e}")
            raise
    
    def _schedule_next_recurring_reminder(self, reminder: Reminder, db: Session):
        """Планирует следующее повторяющееся напоминание"""
        try:
            # Создаем новое напоминание для следующего раза
            next_time = datetime.now() + timedelta(minutes=reminder.repeat_interval)
            
            new_reminder = Reminder(
                user_id=reminder.user_id,
                title=reminder.title,
                message=reminder.message,
                reminder_type=reminder.reminder_type,
                scheduled_time=next_time,
                is_recurring=reminder.is_recurring,
                repeat_interval=reminder.repeat_interval,
                repeat_days=reminder.repeat_days,
                reminder_time=reminder.reminder_time,
                expires_at=reminder.expires_at,
                max_send_count=reminder.max_send_count,
                priority=reminder.priority,
                action_url=reminder.action_url,
                extra_data=reminder.extra_data,
                status=ReminderStatus.ACTIVE,
                is_enabled=True
            )
            
            db.add(new_reminder)
            db.commit()
            
            # Планируем новое напоминание
            self._schedule_reminder(new_reminder)
            
            logger.info(f"Запланировано следующее напоминание {new_reminder.id} на {next_time}")
            
        except Exception as e:
            logger.error(f"Ошибка планирования следующего напоминания: {e}")
    
    def _format_reminder_message(self, reminder: Reminder) -> str:
        """Форматирует сообщение напоминания"""
        message = f"🔔 *{reminder.title}*\n\n"
        
        if reminder.message and reminder.message != reminder.title and reminder.message != "None":
            message += f"📝 {reminder.message}\n\n"
        
        message += f"⏰ Время: {reminder.scheduled_time.strftime('%H:%M')}\n"
        
        # Добавляем информацию о типе
        type_emoji = {
            "daily": "📅",
            "weekly": "📆", 
            "custom": "⚙️",
            "detox_reminder": "🧘",
            "focus_reminder": "🎯",
            "break_reminder": "☕",
            "quiet_hours": "🤫"
        }
        
        emoji = type_emoji.get(reminder.reminder_type.value, "🔔")
        message += f"{emoji} Тип: {reminder.reminder_type.value}\n"
        
        if reminder.is_recurring:
            message += f"🔄 Повторяющееся\n"
            if reminder.repeat_interval:
                message += f"⏱️ Интервал: {reminder.repeat_interval} мин.\n"
        
        if reminder.priority > 1:
            message += f"⭐ Приоритет: {reminder.priority}\n"
        
        if reminder.action_url:
            message += f"🔗 [Открыть действие]({reminder.action_url})"
        
        return message
    
    def add_reminder(self, reminder: Reminder):
        """Добавляет новое напоминание в планировщик"""
        try:
            self._schedule_reminder(reminder)
            logger.info(f"Напоминание {reminder.id} добавлено в планировщик")
        except Exception as e:
            logger.error(f"Ошибка добавления напоминания {reminder.id}: {e}")
    
    def remove_reminder(self, reminder_id: int):
        """Удаляет напоминание из планировщика"""
        try:
            job_id = f"reminder_{reminder_id}"
            self.scheduler.remove_job(job_id)
            logger.info(f"Напоминание {reminder_id} удалено из планировщика")
        except Exception as e:
            logger.error(f"Ошибка удаления напоминания {reminder_id}: {e}")
    
    def update_reminder(self, reminder: Reminder):
        """Обновляет напоминание в планировщике"""
        try:
            self._schedule_reminder(reminder)
            logger.info(f"Напоминание {reminder.id} обновлено в планировщике")
        except Exception as e:
            logger.error(f"Ошибка обновления напоминания {reminder.id}: {e}")
    
    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Возвращает список запланированных задач"""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'next_run_time': job.next_run_time,
                    'trigger': str(job.trigger)
                })
            return jobs
        except Exception as e:
            logger.error(f"Ошибка получения списка задач: {e}")
            return []
    
    def cleanup_expired_reminders(self):
        """Очищает истекшие напоминания"""
        try:
            with SessionLocal() as db:
                expired_reminders = reminder_crud.get_expired_reminders(db)
                
                if expired_reminders:
                    for reminder in expired_reminders:
                        reminder_crud.mark_as_expired(db, reminder.id)
                        self.remove_reminder(reminder.id)
                    
                    logger.info(f"Очищено {len(expired_reminders)} истекших напоминаний")
                    
        except Exception as e:
            logger.error(f"Ошибка очистки истекших напоминаний: {e}")


# Глобальный экземпляр планировщика
scheduler = ReminderScheduler()


async def start_reminder_scheduler():
    """Запускает планировщик напоминаний"""
    await scheduler.start()


def stop_reminder_scheduler():
    """Останавливает планировщик напоминаний"""
    scheduler.stop()


def add_reminder_to_scheduler(reminder: Reminder):
    """Добавляет напоминание в планировщик"""
    scheduler.add_reminder(reminder)


def remove_reminder_from_scheduler(reminder_id: int):
    """Удаляет напоминание из планировщика"""
    scheduler.remove_reminder(reminder_id)


def update_reminder_in_scheduler(reminder: Reminder):
    """Обновляет напоминание в планировщике"""
    scheduler.update_reminder(reminder)


def get_scheduled_jobs():
    """Возвращает список запланированных задач"""
    return scheduler.get_scheduled_jobs()


def cleanup_expired_now():
    """Принудительно очищает истекшие напоминания"""
    scheduler.cleanup_expired_reminders()
