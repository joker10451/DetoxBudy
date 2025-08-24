#!/usr/bin/env python3
"""
@file: main.py
@description: Главный файл запуска Detox Buddy Telegram бота
@dependencies: telegram-bot, celery, database
@created: 2024-08-24
"""

import sys
import asyncio
import logging
from pathlib import Path

# Добавляем путь к src для импортов
sys.path.insert(0, str(Path(__file__).parent / "src"))

from detoxbuddy.core.config import settings
from detoxbuddy.telegram.bot.telegram_bot import TelegramBot
from detoxbuddy.database.database import init_db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('detoxbuddy.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска приложения"""
    try:
        logger.info("Запуск Detox Buddy...")
        
        # Проверяем наличие токена
        if not settings.telegram_bot_token:
            logger.error("Telegram bot token не найден! Проверьте переменную окружения TELEGRAM_BOT_TOKEN")
            sys.exit(1)
        
        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        init_db()
        
        # Создание и запуск бота
        logger.info("Создание Telegram бота...")
        bot = TelegramBot()
        
        # Запуск планировщика напоминаний
        logger.info("Запуск планировщика напоминаний...")
        # Планировщик будет запущен внутри бота
        
        logger.info(f"Detox Buddy запущен! Токен: {settings.telegram_bot_token[:10]}...")
        logger.info("Telegram бот активен")
        logger.info("Планировщик напоминаний запущен")
        logger.info("Бот готов к работе!")
        
        await bot.start()
        await bot.run_polling()
        
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
