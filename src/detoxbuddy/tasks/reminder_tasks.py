"""
@file: reminder_tasks.py
@description: Задачи Celery для системы напоминаний
@dependencies: celery, sqlalchemy, telegram_bot, models
@created: 2024-08-24
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from celery import current_task
from sqlalchemy.orm import Session

from detoxbuddy.core.celery_app import celery_app
from detoxbuddy.database.database import SessionLocal
from detoxbuddy.database.models.reminder import Reminder, ReminderStatus, ReminderType
from detoxbuddy.database.models.user import User
from detoxbuddy.telegram.bot.telegram_bot import TelegramBot
from detoxbuddy.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.tasks.reminder_tasks.check_due_reminders")
def check_due_reminders(self):
    """
    Проверяет и отправляет напоминания, которые должны быть отправлены
    """
    try:
        logger.info("Начинаю проверку напоминаний")
        
        with SessionLocal() as db:
            # Получаем все активные напоминания, которые должны быть отправлены
            due_reminders = (
                db.query(Reminder)
                .filter(
                    Reminder.status == ReminderStatus.ACTIVE,
                    Reminder.is_enabled == True,
                    Reminder.scheduled_time <= datetime.utcnow(),
                    (Reminder.expires_at.is_(None) | (Reminder.expires_at > datetime.utcnow())),
                    (Reminder.max_send_count.is_(None) | (Reminder.sent_count < Reminder.max_send_count))
                )
                .all()
            )
            
            logger.info(f"Найдено {len(due_reminders)} напоминаний для отправки")
            
            for reminder in due_reminders:
                try:
                    # Отправляем напоминание
                    send_telegram_reminder.delay(reminder.id)
                    
                    # Обновляем статус
                    reminder.status = ReminderStatus.SENT
                    reminder.sent_at = datetime.utcnow()
                    reminder.sent_count += 1
                    
                    # Если это повторяющееся напоминание, планируем следующее
                    if reminder.is_recurring and reminder.repeat_interval:
                        next_time = reminder.sent_at + timedelta(minutes=reminder.repeat_interval)
                        reminder.scheduled_time = next_time
                        reminder.status = ReminderStatus.ACTIVE
                    
                    db.commit()
                    logger.info(f"Напоминание {reminder.id} обработано")
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке напоминания {reminder.id}: {e}")
                    db.rollback()
                    continue
        
        logger.info("Проверка напоминаний завершена")
        return {"status": "success", "processed": len(due_reminders)}
        
    except Exception as e:
        logger.error(f"Ошибка при проверке напоминаний: {e}")
        raise


@celery_app.task(bind=True, name="app.tasks.reminder_tasks.send_telegram_reminder")
def send_telegram_reminder(self, reminder_id: int):
    """
    Отправляет напоминание через Telegram
    """
    try:
        logger.info(f"Отправляю напоминание {reminder_id}")
        
        with SessionLocal() as db:
            reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if not reminder:
                logger.error(f"Напоминание {reminder_id} не найдено")
                return {"status": "error", "message": "Reminder not found"}
            
            user = db.query(User).filter(User.id == reminder.user_id).first()
            if not user:
                logger.error(f"Пользователь {reminder.user_id} не найден")
                return {"status": "error", "message": "User not found"}
            
            # Формируем сообщение
            message = f"🔔 *{reminder.title}*\n\n"
            if reminder.message:
                message += f"{reminder.message}\n\n"
            
            # Добавляем информацию о типе напоминания
            type_emoji = {
                ReminderType.DAILY: "📅",
                ReminderType.WEEKLY: "📆",
                ReminderType.CUSTOM: "⚙️",
                ReminderType.DETOX_REMINDER: "🧘",
                ReminderType.FOCUS_REMINDER: "🎯",
                ReminderType.BREAK_REMINDER: "☕",
                ReminderType.QUIET_HOURS: "🤫"
            }
            
            emoji = type_emoji.get(reminder.reminder_type, "🔔")
            message += f"{emoji} Тип: {reminder.reminder_type.value}\n"
            
            if reminder.action_url:
                message += f"🔗 [Открыть действие]({reminder.action_url})"
            
            # Отправляем через Telegram бота
            from telegram import Bot
            bot = Bot(token=settings.telegram_bot_token)
            
            try:
                # Используем asyncio для отправки сообщения
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                result = loop.run_until_complete(
                    bot.send_message(
                        chat_id=user.telegram_id,
                        text=message,
                        parse_mode="Markdown"
                    )
                )
                loop.close()
                
                success = True
                logger.info(f"Сообщение отправлено: {result.message_id}")
                
            except Exception as e:
                logger.error(f"Ошибка отправки сообщения: {e}")
                success = False
            
            if success:
                logger.info(f"Напоминание {reminder_id} отправлено пользователю {user.telegram_id}")
                return {"status": "success", "reminder_id": reminder_id}
            else:
                logger.error(f"Не удалось отправить напоминание {reminder_id}")
                return {"status": "error", "message": "Failed to send message"}
                
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания {reminder_id}: {e}")
        raise


@celery_app.task(bind=True, name="app.tasks.reminder_tasks.cleanup_expired_reminders")
def cleanup_expired_reminders(self):
    """
    Очищает истекшие напоминания
    """
    try:
        logger.info("Начинаю очистку истекших напоминаний")
        
        with SessionLocal() as db:
            # Находим истекшие напоминания
            expired_reminders = (
                db.query(Reminder)
                .filter(
                    Reminder.expires_at <= datetime.utcnow(),
                    Reminder.status == ReminderStatus.ACTIVE
                )
                .all()
            )
            
            logger.info(f"Найдено {len(expired_reminders)} истекших напоминаний")
            
            for reminder in expired_reminders:
                reminder.status = ReminderStatus.EXPIRED
                logger.info(f"Напоминание {reminder.id} помечено как истекшее")
            
            db.commit()
        
        logger.info("Очистка истекших напоминаний завершена")
        return {"status": "success", "expired_count": len(expired_reminders)}
        
    except Exception as e:
        logger.error(f"Ошибка при очистке истекших напоминаний: {e}")
        raise


@celery_app.task(bind=True, name="app.tasks.reminder_tasks.create_reminder")
def create_reminder(
    self,
    user_id: int,
    title: str,
    message: Optional[str],
    reminder_type: str,
    scheduled_time: str,
    is_recurring: bool = False,
    repeat_interval: Optional[int] = None,
    expires_at: Optional[str] = None,
    max_send_count: Optional[int] = None,
    priority: int = 1,
    action_url: Optional[str] = None
):
    """
    Создает новое напоминание
    """
    try:
        logger.info(f"Создаю напоминание для пользователя {user_id}")
        
        with SessionLocal() as db:
            # Проверяем существование пользователя
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"Пользователь {user_id} не найден")
                return {"status": "error", "message": "User not found"}
            
            # Создаем напоминание
            reminder = Reminder(
                user_id=user_id,
                title=title,
                message=message,
                reminder_type=ReminderType(reminder_type),
                scheduled_time=datetime.fromisoformat(scheduled_time),
                is_recurring=is_recurring,
                repeat_interval=repeat_interval,
                expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
                max_send_count=max_send_count,
                priority=priority,
                action_url=action_url,
                status=ReminderStatus.ACTIVE,
                is_enabled=True
            )
            
            db.add(reminder)
            db.commit()
            db.refresh(reminder)
            
            logger.info(f"Напоминание {reminder.id} создано")
            return {"status": "success", "reminder_id": reminder.id}
            
    except Exception as e:
        logger.error(f"Ошибка при создании напоминания: {e}")
        raise


@celery_app.task(bind=True, name="app.tasks.reminder_tasks.cancel_reminder")
def cancel_reminder(self, reminder_id: int):
    """
    Отменяет напоминание
    """
    try:
        logger.info(f"Отменяю напоминание {reminder_id}")
        
        with SessionLocal() as db:
            reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()
            if not reminder:
                logger.error(f"Напоминание {reminder_id} не найдено")
                return {"status": "error", "message": "Reminder not found"}
            
            reminder.status = ReminderStatus.CANCELLED
            db.commit()
            
            logger.info(f"Напоминание {reminder_id} отменено")
            return {"status": "success", "reminder_id": reminder_id}
            
    except Exception as e:
        logger.error(f"Ошибка при отмене напоминания {reminder_id}: {e}")
        raise


@celery_app.task(bind=True, name="app.tasks.reminder_tasks.get_user_reminders")
def get_user_reminders(self, user_id: int, status: Optional[str] = None):
    """
    Получает напоминания пользователя
    """
    try:
        logger.info(f"Получаю напоминания пользователя {user_id}")
        
        with SessionLocal() as db:
            query = db.query(Reminder).filter(Reminder.user_id == user_id)
            
            if status:
                query = query.filter(Reminder.status == ReminderStatus(status))
            
            reminders = query.order_by(Reminder.scheduled_time.desc()).all()
            
            result = []
            for reminder in reminders:
                result.append({
                    "id": reminder.id,
                    "title": reminder.title,
                    "message": reminder.message,
                    "reminder_type": reminder.reminder_type.value,
                    "status": reminder.status.value,
                    "scheduled_time": reminder.scheduled_time.isoformat(),
                    "sent_at": reminder.sent_at.isoformat() if reminder.sent_at else None,
                    "is_recurring": reminder.is_recurring,
                    "priority": reminder.priority,
                    "created_at": reminder.created_at.isoformat()
                })
            
            logger.info(f"Найдено {len(result)} напоминаний для пользователя {user_id}")
            return {"status": "success", "reminders": result}
            
    except Exception as e:
        logger.error(f"Ошибка при получении напоминаний пользователя {user_id}: {e}")
        raise
