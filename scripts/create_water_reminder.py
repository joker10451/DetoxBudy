#!/usr/bin/env python3
"""
@file: create_water_reminder.py
@description: Создание правильного напоминания о воде
@created: 2024-12-19
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Добавляем путь к src для импортов
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from detoxbuddy.database.database import SessionLocal
from detoxbuddy.database.models.reminder import Reminder, ReminderType, ReminderStatus
from detoxbuddy.database.models.user import User


def create_water_reminder():
    """Создает правильное напоминание о воде"""
    print("🚰 Создание напоминания о воде...")
    
    # Ваш chat_id
    YOUR_CHAT_ID = 6141363106
    
    try:
        with SessionLocal() as db:
            # Находим пользователя
            user = db.query(User).filter(User.telegram_id == YOUR_CHAT_ID).first()
            
            if not user:
                print("❌ Пользователь не найден")
                return False
            
            # Создаем напоминание на прошлое время (будет отправлено сразу)
            past_time = datetime.now() - timedelta(minutes=1)
            
            reminder = Reminder(
                user_id=user.id,
                title="💧 Напоминание о воде",
                message="Время попить воды! 💧\n\nНе забывайте поддерживать водный баланс - это важно для здоровья! 🥤",
                reminder_type=ReminderType.CUSTOM,
                scheduled_time=past_time,
                status=ReminderStatus.ACTIVE,
                is_enabled=True,
                priority=3
            )
            
            db.add(reminder)
            db.commit()
            db.refresh(reminder)
            
            print(f"✅ Напоминание о воде создано!")
            print(f"   📝 ID: {reminder.id}")
            print(f"   📅 Время: {reminder.scheduled_time}")
            print(f"   👤 Получатель: {user.first_name} ({user.telegram_id})")
            print(f"   📋 Заголовок: {reminder.title}")
            print(f"   💬 Сообщение: {reminder.message}")
            
            print("\n🔔 Напоминание будет отправлено планировщиком в течение 1 минуты!")
            print("📱 Проверьте Telegram на наличие сообщения от @DetoxBudy_bot")
            
            return True
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False


if __name__ == "__main__":
    create_water_reminder()
