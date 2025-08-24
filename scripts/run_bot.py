#!/usr/bin/env python3
"""
Скрипт для запуска только Telegram бота
"""

import asyncio
import logging
import os
import sys
import atexit
from app.bot.telegram_bot import TelegramBot
from app.config import settings
import structlog

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = structlog.get_logger()


def create_lock_file():
    """Создает файл блокировки для предотвращения множественных запусков"""
    lock_file = "bot.lock"
    
    if os.path.exists(lock_file):
        print("❌ Бот уже запущен! Найден файл блокировки.")
        print("💡 Если бот был завершен некорректно, удалите файл 'bot.lock'")
        sys.exit(1)
    
    # Создаем файл блокировки
    with open(lock_file, "w") as f:
        f.write(str(os.getpid()))
    
    # Регистрируем функцию для удаления файла при завершении
    atexit.register(remove_lock_file)
    print("🔒 Создан файл блокировки")


def remove_lock_file():
    """Удаляет файл блокировки"""
    lock_file = "bot.lock"
    if os.path.exists(lock_file):
        os.remove(lock_file)
        print("🔓 Файл блокировки удален")


async def main():
    """Основная функция"""
    # Создаем файл блокировки
    create_lock_file()
    
    if not settings.telegram_bot_token:
        logger.error("Telegram bot token not configured!")
        return
    
    bot = TelegramBot()
    
    try:
        logger.info("Starting Telegram bot...")
        await bot.start()
        
        # Запускаем polling
        logger.info("Starting polling...")
        await bot.run_polling()
        
    except KeyboardInterrupt:
        logger.info("Stopping bot...")
        await bot.stop()
    except Exception as e:
        logger.error(f"Error: {e}")
        await bot.stop()
    finally:
        remove_lock_file()


if __name__ == "__main__":
    asyncio.run(main())
