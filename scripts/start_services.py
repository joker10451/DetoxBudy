#!/usr/bin/env python3
"""
@file: start_services.py
@description: Скрипт для запуска всех необходимых сервисов
@dependencies: redis, celery, database
@created: 2024-08-24
"""

import sys
import os
import subprocess
import time
import logging
from pathlib import Path

# Добавляем путь к src для импортов
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from detoxbuddy.core.config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def check_redis_installed():
    """Проверяет, установлен ли Redis"""
    try:
        result = subprocess.run(['redis-server', '--version'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def start_redis():
    """Запускает Redis сервер"""
    print("🔍 Проверка Redis...")
    
    if not check_redis_installed():
        print("❌ Redis не установлен!")
        print("💡 Установите Redis:")
        print("   Windows: https://github.com/microsoftarchive/redis/releases")
        print("   macOS: brew install redis")
        print("   Ubuntu: sudo apt-get install redis-server")
        return False
    
    try:
        # Проверяем, не запущен ли уже Redis
        from redis import Redis
        redis_client = Redis.from_url(settings.CELERY_BROKER_URL)
        redis_client.ping()
        print("✅ Redis уже запущен")
        return True
    except:
        print("🚀 Запуск Redis сервера...")
        try:
            # Запускаем Redis в фоновом режиме
            subprocess.Popen(['redis-server'], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            time.sleep(2)  # Ждем запуска
            
            # Проверяем подключение
            redis_client = Redis.from_url(settings.CELERY_BROKER_URL)
            redis_client.ping()
            print("✅ Redis запущен успешно")
            return True
        except Exception as e:
            print(f"❌ Ошибка запуска Redis: {e}")
            return False


def start_celery_services():
    """Запускает Celery worker и beat"""
    print("\n🚀 Запуск Celery сервисов...")
    
    try:
        # Запускаем Celery beat в фоне
        print("📅 Запуск Celery beat...")
        beat_process = subprocess.Popen([
            sys.executable, 'scripts/run_celery_beat.py'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        time.sleep(1)
        
        # Запускаем Celery worker в фоне
        print("👷 Запуск Celery worker...")
        worker_process = subprocess.Popen([
            sys.executable, 'scripts/run_celery.py'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        time.sleep(2)
        
        print("✅ Celery сервисы запущены")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка запуска Celery: {e}")
        return False


def start_telegram_bot():
    """Запускает Telegram бота"""
    print("\n🤖 Запуск Telegram бота...")
    
    try:
        # Запускаем бота в фоне
        bot_process = subprocess.Popen([
            sys.executable, 'main.py'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        time.sleep(2)
        print("✅ Telegram бот запущен")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")
        return False


def main():
    """Основная функция запуска сервисов"""
    print("🚀 Запуск всех сервисов DetoxBuddy")
    print("=" * 50)
    
    # Запускаем Redis
    redis_ok = start_redis()
    if not redis_ok:
        print("\n❌ Не удалось запустить Redis!")
        print("💡 Рекомендации:")
        print("1. Установите Redis")
        print("2. Или используйте альтернативный брокер (например, SQLite)")
        return
    
    # Запускаем Celery сервисы
    celery_ok = start_celery_services()
    if not celery_ok:
        print("\n❌ Не удалось запустить Celery!")
        return
    
    # Запускаем Telegram бота
    bot_ok = start_telegram_bot()
    if not bot_ok:
        print("\n❌ Не удалось запустить Telegram бота!")
        return
    
    print("\n" + "=" * 50)
    print("🎉 Все сервисы запущены успешно!")
    print("\n📋 Статус сервисов:")
    print(f"✅ Redis: {'Работает' if redis_ok else 'Ошибка'}")
    print(f"✅ Celery: {'Работает' if celery_ok else 'Ошибка'}")
    print(f"✅ Telegram бот: {'Работает' if bot_ok else 'Ошибка'}")
    
    print("\n💡 Теперь вы можете:")
    print("1. Отправить команду /start боту")
    print("2. Создать напоминание: /remind 5m Тестовое напоминание")
    print("3. Просмотреть напоминания: /reminders")
    
    print("\n🛑 Для остановки всех сервисов нажмите Ctrl+C")
    
    try:
        # Держим скрипт запущенным
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Остановка сервисов...")


if __name__ == "__main__":
    main()
