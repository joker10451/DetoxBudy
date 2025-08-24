#!/usr/bin/env python3
"""
Telegram бот с webhook
"""

import asyncio
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Токен бота
TOKEN = "8450226618:AAEn_f7no_CA9oHmERdDN7n0ctuPsyveZsk"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    await update.message.reply_text(
        "🤖 Привет! Я бот DetoxBuddy!\n\n"
        "Отправьте /help для получения справки."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
    await update.message.reply_text(
        "📚 Доступные команды:\n"
        "/start - Запустить бота\n"
        "/help - Показать эту справку\n"
        "/test - Тестовая команда"
    )

async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /test"""
    await update.message.reply_text("✅ Тестовая команда работает!")

async def main():
    """Основная функция"""
    print("Запуск бота с webhook...")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("test", test_command))
    
    # Устанавливаем команды бота
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("help", "Помощь"),
        BotCommand("test", "Тестовая команда"),
    ]
    await application.bot.set_my_commands(commands)
    
    print("Бот запущен! Отправьте /start в Telegram")
    
    # Удаляем webhook и запускаем polling
    await application.bot.delete_webhook()
    
    # Запускаем бота с простым polling
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Держим бота запущенным
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("Остановка бота...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
