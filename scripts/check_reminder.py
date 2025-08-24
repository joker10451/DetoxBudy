#!/usr/bin/env python3
"""
@file: check_reminder.py
@description: Проверка напоминаний в базе данных
@created: 2024-12-19
"""

import sys
from pathlib import Path

# Добавляем путь к src для импортов
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from detoxbuddy.database.database import SessionLocal
from detoxbuddy.database.models.reminder import Reminder, ReminderStatus
from detoxbuddy.database.models.user import User


def check_reminders():
    """Проверяет все напоминания в базе данных"""
    print("🔍 Проверка напоминаний в базе данных...")
    
    try:
        with SessionLocal() as db:
            # Получаем все напоминания
            reminders = db.query(Reminder).order_by(Reminder.id.desc()).limit(10).all()
            
            if not reminders:
                print("❌ Напоминаний не найдено")
                return
            
            print(f"✅ Найдено {len(reminders)} напоминаний:")
            print()
            
            for reminder in reminders:
                user = reminder.user
                print(f"📝 ID: {reminder.id}")
                print(f"   👤 Пользователь: {user.first_name if user else 'N/A'} ({user.telegram_id if user else 'N/A'})")
                print(f"   📋 Заголовок: {reminder.title}")
                print(f"   💬 Сообщение: '{reminder.message}'")
                print(f"   🎯 Тип: {reminder.reminder_type.value}")
                print(f"   📅 Время: {reminder.scheduled_time}")
                print(f"   📊 Статус: {reminder.status.value}")
                print(f"   ✅ Включено: {reminder.is_enabled}")
                print()
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    check_reminders()
