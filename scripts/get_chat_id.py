#!/usr/bin/env python3
"""
@file: get_chat_id.py
@description: Получение chat_id пользователя Telegram
@created: 2024-12-19
"""

import sys
import os
import asyncio
from pathlib import Path

# Добавляем путь к src для импортов
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from detoxbuddy.core.config import settings


async def get_chat_id():
    """Получает chat_id из последних обновлений бота"""
    try:
        from telegram import Bot
        
        bot = Bot(token=settings.telegram_bot_token)
        
        async with bot:
            # Получаем последние обновления
            updates = await bot.get_updates()
            
            print("🔍 Поиск chat_id в последних сообщениях...")
            print(f"📊 Найдено обновлений: {len(updates)}")
            
            if not updates:
                print("\n❌ Обновления не найдены!")
                print("💡 Для получения chat_id:")
                print("   1. Напишите боту @DetoxBudy_bot любое сообщение (например: /start)")
                print("   2. Запустите этот скрипт снова")
                return
            
            print("\n📋 Найденные chat_id:")
            
            unique_chats = set()
            for update in updates:
                if update.message:
                    chat_id = update.message.chat.id
                    chat_type = update.message.chat.type
                    user_name = update.message.from_user.first_name if update.message.from_user else "Неизвестно"
                    username = update.message.from_user.username if update.message.from_user and update.message.from_user.username else "Нет"
                    
                    if chat_id not in unique_chats:
                        unique_chats.add(chat_id)
                        print(f"   💬 Chat ID: {chat_id}")
                        print(f"      👤 Имя: {user_name}")
                        print(f"      🏷️ Username: @{username}")
                        print(f"      📝 Тип: {chat_type}")
                        print()
            
            if unique_chats:
                print("✅ Скопируйте один из chat_id выше для использования в тестах!")
                print("🔧 Замените YOUR_CHAT_ID в тестовых скриптах на найденный chat_id")
            else:
                print("❌ Chat ID не найден в сообщениях")
    
    except Exception as e:
        print(f"❌ Ошибка получения chat_id: {e}")


if __name__ == "__main__":
    asyncio.run(get_chat_id())
