#!/usr/bin/env python3
"""
@file: start_bot.py
@description: Запуск Telegram бота DetoxBuddy
@created: 2024-12-19
"""

import sys
import os
import asyncio
import logging
from pathlib import Path

# Добавляем путь к src для импортов
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from detoxbuddy.telegram.bot.telegram_bot import TelegramBot
from detoxbuddy.core.reminder_scheduler import start_reminder_scheduler

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Запускает Telegram бота и планировщик напоминаний"""
    print("🚀 Запуск DetoxBuddy Telegram бота...")
    
    try:
        # Создаем экземпляр бота
        bot = TelegramBot()
        
        # Запускаем бота
        await bot.start()
        
        # Запускаем планировщик напоминаний
        print("📅 Запуск планировщика напоминаний...")
        await start_reminder_scheduler()
        
        print("✅ Бот запущен успешно!")
        print("📱 Теперь вы можете писать боту @DetoxBudy_bot")
        print("🔔 Планировщик напоминаний активен")
        print("\n💡 Доступные команды:")
        print("   /start - Начать работу с ботом")
        print("   /help - Помощь")
        print("   /remind - Создать напоминание")
        print("   /reminders - Показать мои напоминания")
        print("\n🛑 Для остановки бота нажмите Ctrl+C")
        
        # Запускаем polling
        await bot.run_polling()
        
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал остановки...")
        await bot.stop()
        print("✅ Бот остановлен")
    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")
        print(f"❌ Ошибка запуска бота: {e}")


if __name__ == "__main__":
    asyncio.run(main())
