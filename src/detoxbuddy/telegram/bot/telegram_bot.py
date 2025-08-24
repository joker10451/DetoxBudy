"""
Основной класс Telegram бота для DetoxBuddy
"""

import asyncio
import logging
import threading
from typing import Optional
from datetime import timedelta
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
import structlog

from detoxbuddy.core.config_simple import settings, constants
from detoxbuddy.core.services.user_service import user_service
from detoxbuddy.database.models.user import User
from detoxbuddy.database.models.achievement import Achievement, UserAchievement, UserLevel, AchievementType
from detoxbuddy.database.crud.achievement import achievement_service, user_achievement_crud, user_level_crud
from detoxbuddy.core.focus_timer import FocusTimer


logger = structlog.get_logger()


class TelegramBot:
    """Основной класс Telegram бота"""
    
    def __init__(self):
        """Инициализация бота"""
        self.application: Optional[Application] = None
        self.token = settings.telegram_bot_token
        self.polling_thread: Optional[threading.Thread] = None
        self.focus_timer: Optional[FocusTimer] = None
        
    async def start(self):
        """Запуск бота"""
        if not self.token:
            logger.warning("Telegram bot token not configured, skipping bot startup")
            return
            
        try:
            # Создание приложения
            self.application = Application.builder().token(self.token).build()
            
            # Инициализация FocusTimer
            self.focus_timer = FocusTimer(self)
            await self.focus_timer.start()
            
            # Регистрация обработчиков команд
            await self._setup_handlers()
            
            # Установка команд бота
            await self._setup_commands()
            
            # Запуск бота
            await self.application.initialize()
            await self.application.start()
            
            logger.info("Telegram bot started successfully")
            
        except Exception as e:
            logger.error("Failed to start Telegram bot", error=str(e))
            raise
    
    async def run_polling(self):
        """Запуск polling"""
        if not self.application:
            logger.error("Application not initialized")
            return
            
        try:
            # Удаляем webhook и запускаем polling
            await self.application.bot.delete_webhook()
            await self.application.updater.start_polling()
            
            # Держим бота запущенным
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logger.error("Polling error", error=str(e))
    
    async def stop(self):
        """Остановка бота"""
        if self.focus_timer:
            await self.focus_timer.stop()
        
        if self.application:
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram bot stopped")
    
    async def _setup_handlers(self):
        """Настройка обработчиков команд"""
        if not self.application:
            return
        
        # Команды
        self.application.add_handler(CommandHandler("start", self._start_command))
        self.application.add_handler(CommandHandler("help", self._help_command))
        self.application.add_handler(CommandHandler("test", self._test_command))
        self.application.add_handler(CommandHandler("remind", self._remind_command))
        self.application.add_handler(CommandHandler("reminders", self._reminders_command))
        self.application.add_handler(CommandHandler("detox", self._detox_command))
        self.application.add_handler(CommandHandler("focus", self._focus_command))
        self.application.add_handler(CommandHandler("quiet", self._quiet_command))
        self.application.add_handler(CommandHandler("content", self._content_command))
        self.application.add_handler(CommandHandler("analytics", self._analytics_command))
        self.application.add_handler(CommandHandler("addtime", self._addtime_command))
        self.application.add_handler(CommandHandler("settings", self._settings_command))
        self.application.add_handler(CommandHandler("recurring", self._recurring_command))
        self.application.add_handler(CommandHandler("daily", self._daily_command))
        self.application.add_handler(CommandHandler("weekly", self._weekly_command))
        self.application.add_handler(CommandHandler("achievements", self._achievements_command))
        self.application.add_handler(CommandHandler("level", self._level_command))
        self.application.add_handler(CommandHandler("profile", self._profile_command))
        
        # Обработка callback queries (inline кнопки)
        self.application.add_handler(CallbackQueryHandler(self._handle_callback_query))
        
        # Обработка неизвестных команд
        self.application.add_handler(MessageHandler(filters.COMMAND, self._unknown_command))
        
        # Обработка текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_text))
        
        logger.info("Telegram bot handlers setup completed")
    
    async def _setup_commands(self):
        """Установка команд бота"""
        if not self.application:
            return
        
        commands = [
            BotCommand(constants.COMMAND_START, "Запустить бота"),
            BotCommand(constants.COMMAND_HELP, "Помощь"),
            BotCommand("test", "Тестовая команда"),
            BotCommand("remind", "Создать напоминание"),
            BotCommand("reminders", "Мои напоминания"),
            BotCommand("recurring", "Повторяющиеся напоминания"),
            BotCommand("daily", "Ежедневные напоминания"),
            BotCommand("weekly", "Еженедельные напоминания"),
            BotCommand("achievements", "Достижения"),
            BotCommand("level", "Уровень и опыт"),
            BotCommand("profile", "Профиль"),
            BotCommand(constants.COMMAND_DETOX, "План детокса"),
            BotCommand(constants.COMMAND_FOCUS, "Таймер фокуса"),
            BotCommand(constants.COMMAND_QUIET, "Тихие часы"),
            BotCommand(constants.COMMAND_CONTENT, "Полезный контент"),
            BotCommand(constants.COMMAND_ANALYTICS, "Аналитика"),
            BotCommand("addtime", "Добавить время"),
            BotCommand(constants.COMMAND_SETTINGS, "Настройки"),
        ]
        
        await self.application.bot.set_my_commands(commands)
        logger.info("Telegram bot commands setup completed")
    
    async def _authenticate_user(self, update: Update) -> Optional[User]:
        """
        Аутентификация пользователя через Telegram.
        Автоматически создает пользователя, если его нет в базе.
        """
        if not update.effective_user:
            return None
        
        try:
            user = user_service.authenticate_telegram_user(update.effective_user)
            if user:
                logger.info(
                    "User authenticated",
                    user_id=user.id,
                    telegram_id=user.telegram_id,
                    username=user.username
                )
            return user
        except Exception as e:
            logger.error(f"Failed to authenticate user: {e}")
            return None

    async def _start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        # Аутентификация пользователя
        user = await self._authenticate_user(update)
        if not user:
            await update.message.reply_text(
                "❌ Произошла ошибка при регистрации. Попробуйте позже."
            )
            return
        
        telegram_user = update.effective_user
        chat_id = update.effective_chat.id
        
        # Проверяем, новый ли это пользователь (созданный менее минуты назад)
        from datetime import datetime, timedelta
        is_new_user = (datetime.utcnow() - user.created_at) < timedelta(minutes=1)
        
        if is_new_user:
            welcome_message = f"""
🎉 Добро пожаловать в {settings.project_name}, {telegram_user.first_name}!

Вы успешно зарегистрированы! Теперь я помогу вам осознанно подходить к цифровому потреблению и улучшить цифровую гигиену.

🎯 Что я умею:
• Создавать персональные планы детокса
• Помогать с таймером фокуса (Pomodoro)
• Напоминать о "тихих часах"
• Предлагать полезный контент
• Анализировать экранное время

Используйте /help для получения справки по командам.
            """
        else:
            welcome_message = f"""
👋 С возвращением, {user.full_name}!

Рад видеть вас снова. Используйте /help для просмотра доступных команд.
            """
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_message.strip()
        )
        
        logger.info(
            "User started bot",
            user_id=user.id,
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            is_new_user=is_new_user
        )
    
    async def _help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /help"""
        chat_id = update.effective_chat.id
        
        help_message = """
📚 Доступные команды:

/start - Запустить бота
/help - Показать эту справку
/test - Тестовая команда
/remind - Создать напоминание
/reminders - Мои напоминания
/addtime - Добавить время использования
/analytics - Аналитика экранного времени
/detox - Управление планом детокса
/focus - Таймер фокуса (Pomodoro)
/quiet - Настройка тихих часов
/content - Полезный контент
/settings - Настройки профиля

🏆 Система достижений:
/achievements - Ваши достижения
/level - Уровень и опыт
/profile - Профиль пользователя

💡 Советы:
• /addtime 30 productivity - добавить 30 минут работы
• /remind 15m Сделать перерыв - создать напоминание
• /analytics - посмотреть статистику
• /achievements - посмотреть достижения
        """
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=help_message.strip()
        )
    
    async def _test_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /test"""
        chat_id = update.effective_chat.id
        
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ Тестовая команда работает! Бот DetoxBuddy функционирует корректно."
        )
    
    async def _detox_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /detox"""
        chat_id = update.effective_chat.id
        
        message = """
🧘‍♀️ План детокса

Здесь вы сможете:
• Создать персональный план детокса
• Отслеживать прогресс
• Получать рекомендации

🚧 Функция в разработке
        """
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=message.strip()
        )
    
    async def _focus_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /focus"""
        # Аутентификация пользователя
        user = await self._authenticate_user(update)
        if not user:
            await update.message.reply_text(
                "❌ Ошибка аутентификации. Попробуйте команду /start"
            )
            return
        
        chat_id = update.effective_chat.id
        user_id = user.id
        
        try:
            # Проверяем, есть ли уже активная сессия
            if self.focus_timer and self.focus_timer.is_user_in_session(user_id):
                session_info = self.focus_timer.get_session_info(user_id)
                if session_info:
                    await self._show_active_session_controls(update, session_info)
                    return
            
            # Показываем меню выбора длительности сессии
            await self._show_focus_session_menu(update)
            
        except Exception as e:
            logger.error(f"Error in focus command: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при работе с таймером фокуса. Попробуйте позже."
            )
    
    async def _quiet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /quiet"""
        chat_id = update.effective_chat.id
        
        message = """
🌙 Тихие часы

Настройте время для:
• Отдыха от гаджетов
• Подготовки ко сну
• Цифрового детокса

🚧 Функция в разработке
        """
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=message.strip()
        )
    
    async def _content_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /content"""
        chat_id = update.effective_chat.id
        
        message = """
📖 Полезный контент

Получайте:
• Ежедневные статьи о цифровой гигиене
• Рекомендации по саморазвитию
• Позитивный контент

🚧 Функция в разработке
        """
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=message.strip()
        )
    
    async def _analytics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /analytics - аналитика экранного времени"""
        # Аутентификация пользователя
        user = await self._authenticate_user(update)
        if not user:
            await update.message.reply_text(
                "❌ Ошибка аутентификации. Попробуйте команду /start"
            )
            return
        
        chat_id = update.effective_chat.id
        
        try:
            # Получаем аналитику
            from detoxbuddy.core.services.screen_time_service import ScreenTimeService
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                screen_time_service = ScreenTimeService(db)
                insights = screen_time_service.get_user_insights(user.id)
            
            # Формируем сообщение с аналитикой
            message = self._format_analytics_message(insights)
            
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            message = """
📊 Аналитика экранного времени

❌ Произошла ошибка при получении данных.
Попробуйте позже или добавьте данные о времени использования.

💡 Используйте команды:
• /addtime 30 productivity - добавить 30 минут продуктивного времени
• /addtime 60 social - добавить 1 час в соцсетях
• /addtime 45 entertainment - добавить 45 минут развлечений
            """
        
        # Создаем inline кнопки для аналитики
        keyboard = [
            [
                InlineKeyboardButton("📈 Детальный отчет", callback_data="analytics_detailed"),
                InlineKeyboardButton("📊 Тренды", callback_data="analytics_trends")
            ],
            [
                InlineKeyboardButton("🎯 Цели", callback_data="analytics_goals"),
                InlineKeyboardButton("🏆 Достижения", callback_data="analytics_achievements")
            ],
            [
                InlineKeyboardButton("⏰ Добавить время", callback_data="add_time_quick")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=message.strip(),
            reply_markup=reply_markup
        )
    
    async def _remind_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /remind - создание быстрого напоминания"""
        # Аутентификация пользователя
        user = await self._authenticate_user(update)
        if not user:
            await update.message.reply_text(
                "❌ Ошибка аутентификации. Попробуйте команду /start"
            )
            return
        
        chat_id = update.effective_chat.id
        
        # Проверяем аргументы команды
        args = context.args
        if len(args) < 1:
            message = """
🔔 Создание напоминания

Использование: /remind <время> <текст> [repeat]

Примеры:
• /remind 15m Сделать перерыв
• /remind 1h Позвонить маме
• /remind 30m Выпить воды repeat
• /remind 2h Проверить почту repeat

Время можно указать в формате:
• 15m - 15 минут
• 1h - 1 час
• 2h30m - 2 часа 30 минут

Добавьте "repeat" в конце для создания повторяющегося напоминания
            """
        else:
            try:
                # Парсим время
                time_str = args[0]
                remaining_args = args[1:] if len(args) > 1 else []
                
                # Проверяем, есть ли флаг repeat
                is_recurring = False
                if remaining_args and remaining_args[-1].lower() == "repeat":
                    is_recurring = True
                    remaining_args = remaining_args[:-1]  # Убираем "repeat"
                
                text = " ".join(remaining_args) if remaining_args else "Напоминание"
                
                # Простой парсер времени
                delay_minutes = self._parse_time_string(time_str)
                if delay_minutes <= 0:
                    raise ValueError("Время должно быть больше 0")
                
                # Создаем напоминание
                from detoxbuddy.database.crud.reminder import reminder_crud
                from detoxbuddy.database.database import SessionLocal
                from detoxbuddy.database.models.reminder import ReminderType
                
                with SessionLocal() as db:
                    if is_recurring:
                        # Создаем повторяющееся напоминание
                        from datetime import datetime, timedelta
                        start_time = datetime.now() + timedelta(minutes=delay_minutes)
                        
                        reminder = reminder_crud.create_recurring_reminder(
                            db=db,
                            user_id=user.id,
                            title=text,
                            message=text,
                            reminder_type=ReminderType.CUSTOM,
                            repeat_interval=delay_minutes,
                            start_time=start_time
                        )
                        
                        # Добавляем в планировщик
                        from detoxbuddy.core.reminder_scheduler import add_reminder_to_scheduler
                        add_reminder_to_scheduler(reminder)
                        
                        message = f"""
✅ Повторяющееся напоминание создано!

📝 Текст: {text}
⏰ Первое напоминание: через {self._format_time(delay_minutes)}
🔄 Повторение: каждые {self._format_time(delay_minutes)}
🆔 ID: {reminder.id}

Используйте /recurring для управления повторяющимися напоминаниями.
                        """
                    else:
                        # Создаем обычное напоминание
                        reminder = reminder_crud.create_quick_reminder(
                            db=db,
                            user_id=user.id,
                            title=text,
                            message=text,
                            delay_minutes=delay_minutes,
                            reminder_type=ReminderType.CUSTOM
                        )
                        
                        message = f"""
✅ Напоминание создано!

📝 Текст: {text}
⏰ Время: через {self._format_time(delay_minutes)}
🆔 ID: {reminder.id}

Используйте /reminders для просмотра всех напоминаний.
                        """
                
            except ValueError as e:
                message = f"❌ Ошибка: {str(e)}\n\nИспользуйте /remind для получения справки."
            except Exception as e:
                logger.error(f"Error creating reminder: {e}")
                message = "❌ Произошла ошибка при создании напоминания. Попробуйте позже."
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=message.strip()
        )
    
    async def _reminders_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /reminders - просмотр напоминаний"""
        # Аутентификация пользователя
        user = await self._authenticate_user(update)
        if not user:
            await update.message.reply_text(
                "❌ Ошибка аутентификации. Попробуйте команду /start"
            )
            return
        
        chat_id = update.effective_chat.id
        
        try:
            # Получаем напоминания пользователя
            from detoxbuddy.database.crud.reminder import reminder_crud
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                reminders = reminder_crud.get_reminders_for_telegram_bot(db, user_id=user.id, limit=10)
            
            if not reminders:
                message = """
📝 У вас пока нет напоминаний

Создайте первое напоминание командой:
/remind 15m Сделать перерыв
                """
                
                # Кнопка для создания напоминания
                keyboard = [
                    [InlineKeyboardButton("➕ Создать напоминание", callback_data="create_reminder")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
            else:
                message = "📝 Ваши напоминания:\n\n"
                
                for reminder in reminders:
                    # Определяем эмодзи статуса
                    status_emoji = {
                        "active": "🟢",
                        "sent": "✅",
                        "cancelled": "❌",
                        "expired": "⏰"
                    }.get(reminder.status.value, "🔔")
                    
                    # Определяем эмодзи типа
                    type_emoji = {
                        "daily": "📅",
                        "weekly": "📆",
                        "custom": "⚙️",
                        "detox_reminder": "🧘",
                        "focus_reminder": "🎯",
                        "break_reminder": "☕",
                        "quiet_hours": "🤫"
                    }.get(reminder.reminder_type.value, "🔔")
                    
                    # Форматируем время
                    scheduled_time = reminder.scheduled_time.strftime("%d.%m %H:%M")
                    
                    message += f"{status_emoji} {type_emoji} {reminder.title}\n"
                    message += f"   ⏰ {scheduled_time} | ID: {reminder.id}\n"
                    if reminder.message and reminder.message != "None":
                        message += f"   📝 {reminder.message[:50]}{'...' if len(reminder.message) > 50 else ''}\n"
                    message += "\n"
                
                # Кнопки для управления напоминаниями
                keyboard = [
                    [
                        InlineKeyboardButton("➕ Создать", callback_data="create_reminder"),
                        InlineKeyboardButton("🔄 Обновить", callback_data="refresh_reminders")
                    ],
                    [
                        InlineKeyboardButton("❌ Отменить все", callback_data="cancel_all_reminders"),
                        InlineKeyboardButton("📊 Статистика", callback_data="reminders_stats")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
        
        except Exception as e:
            logger.error(f"Error getting reminders: {e}")
            message = "❌ Произошла ошибка при получении напоминаний. Попробуйте позже."
            reply_markup = None
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=message.strip(),
            reply_markup=reply_markup
        )
    
    def _parse_time_string(self, time_str: str) -> int:
        """Парсит строку времени в минуты"""
        time_str = time_str.lower().strip()
        total_minutes = 0
        
        # Парсим часы
        if 'h' in time_str:
            parts = time_str.split('h')
            if len(parts) == 2:
                try:
                    hours = int(parts[0])
                    total_minutes += hours * 60
                    time_str = parts[1]
                except ValueError:
                    raise ValueError("Неверный формат времени")
        
        # Парсим минуты
        if 'm' in time_str:
            parts = time_str.split('m')
            if len(parts) >= 1:
                try:
                    minutes = int(parts[0])
                    total_minutes += minutes
                except ValueError:
                    raise ValueError("Неверный формат времени")
        
        return total_minutes
    
    def _format_time(self, minutes: int) -> str:
        """Форматирует минуты в читаемый вид"""
        if minutes < 60:
            return f"{minutes} мин"
        else:
            hours = minutes // 60
            mins = minutes % 60
            if mins == 0:
                return f"{hours} ч"
            else:
                return f"{hours} ч {mins} мин"
    
    async def _settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /settings"""
        # Аутентификация пользователя
        user = await self._authenticate_user(update)
        if not user:
            await update.message.reply_text(
                "❌ Ошибка аутентификации. Попробуйте команду /start"
            )
            return
        
        chat_id = update.effective_chat.id
        
        # Получаем настройки пользователя
        settings_dict = user_service.get_user_settings_by_telegram_id(user.telegram_id)
        
        if settings_dict:
            settings_text = f"""
⚙️ Ваши текущие настройки:

👤 Профиль:
• Имя: {user.full_name}
• Telegram ID: {user.telegram_id}
• Премиум: {"Да" if user.is_premium else "Нет"}

🔔 Уведомления:
• Включены: {"Да" if settings_dict['notifications_enabled'] else "Нет"}
• Язык: {settings_dict['language']}
• Часовой пояс: {settings_dict['timezone']}

⏱️ Настройки фокуса:
• Длительность фокуса: {settings_dict['default_focus_duration']} мин
• Короткий перерыв: {settings_dict['default_break_duration']} мин
• Длинный перерыв: {settings_dict['long_break_duration']} мин

🤫 Тихие часы:
• Включены: {"Да" if settings_dict['quiet_hours_enabled'] else "Нет"}
"""
            if settings_dict['quiet_hours_enabled']:
                if settings_dict['quiet_hours_start'] and settings_dict['quiet_hours_end']:
                    settings_text += f"• Время: {settings_dict['quiet_hours_start']} - {settings_dict['quiet_hours_end']}\n"

            settings_text += "\n💡 Полная система настроек в разработке."
        else:
            settings_text = """
⚙️ Настройки

Управляйте:
• Профилем пользователя
• Настройками уведомлений
• Предпочтениями контента

🚧 Функция в разработке
            """
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=settings_text.strip()
        )
    
    async def _unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка неизвестных команд"""
        chat_id = update.effective_chat.id
        
        message = """
❓ Неизвестная команда

Используйте /help для просмотра доступных команд.
        """
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=message.strip()
        )
    
    async def _addtime_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /addtime - добавление времени использования"""
        # Аутентификация пользователя
        user = await self._authenticate_user(update)
        if not user:
            await update.message.reply_text(
                "❌ Ошибка аутентификации. Попробуйте команду /start"
            )
            return
        
        chat_id = update.effective_chat.id
        
        # Проверяем аргументы команды
        args = context.args
        if len(args) < 2:
            message = """
⏱️ Добавление времени использования

Использование: /addtime <минуты> <тип_активности>

Примеры:
• /addtime 30 productivity - добавить 30 минут продуктивного времени
• /addtime 60 social - добавить 1 час в соцсетях
• /addtime 45 entertainment - добавить 45 минут развлечений
• /addtime 20 other - добавить 20 минут другого времени

Типы активности:
• productivity - продуктивное время (работа, учеба)
• social - социальные сети
• entertainment - развлечения (игры, видео)
• other - другое время
            """
        else:
            try:
                # Парсим аргументы
                minutes = int(args[0])
                activity_type = args[1].lower()
                
                if minutes <= 0 or minutes > 1440:  # Максимум 24 часа
                    raise ValueError("Время должно быть от 1 до 1440 минут")
                
                # Проверяем тип активности
                valid_types = ['productivity', 'social', 'entertainment', 'other']
                if activity_type not in valid_types:
                    raise ValueError(f"Неверный тип активности. Доступные: {', '.join(valid_types)}")
                
                # Добавляем время
                from detoxbuddy.core.services.screen_time_service import ScreenTimeService
                from detoxbuddy.database.schemas.screen_time import QuickScreenTimeEntry
                from detoxbuddy.database.database import SessionLocal
                
                with SessionLocal() as db:
                    screen_time_service = ScreenTimeService(db)
                    quick_entry = QuickScreenTimeEntry(
                        minutes=minutes,
                        activity_type=activity_type
                    )
                    screen_time = screen_time_service.create_quick_entry(user.id, quick_entry)
                
                # Форматируем тип активности для отображения
                activity_names = {
                    'productivity': 'продуктивное время',
                    'social': 'социальные сети',
                    'entertainment': 'развлечения',
                    'other': 'другое время'
                }
                
                message = f"""
✅ Время добавлено!

⏱️ {self._format_time(minutes)} {activity_names[activity_type]}
📅 Дата: {screen_time.date.strftime('%d.%m.%Y')}
📊 Всего за день: {self._format_time(screen_time.total_minutes)}

💡 Используйте /analytics для просмотра статистики.
                """
                
            except ValueError as e:
                message = f"❌ Ошибка: {str(e)}\n\nИспользуйте /addtime для получения справки."
            except Exception as e:
                logger.error(f"Error adding screen time: {e}")
                message = "❌ Произошла ошибка при добавлении времени. Попробуйте позже."
        
        await context.bot.send_message(
            chat_id=chat_id,
            text=message.strip()
        )
    
    async def _safe_edit_message(self, query, text: str, reply_markup=None):
        """Безопасное обновление сообщения с проверкой изменений"""
        try:
            current_text = query.message.text
            current_reply_markup = query.message.reply_markup
            new_text = text.strip()
            
            # Проверяем изменения в тексте и reply_markup
            text_changed = current_text != new_text
            markup_changed = self._compare_reply_markup(current_reply_markup, reply_markup)
            
            if text_changed or markup_changed:
                await query.edit_message_text(
                    text=new_text,
                    reply_markup=reply_markup
                )
            else:
                # Если содержимое не изменилось, просто отвечаем на callback
                await query.answer("📊 Данные актуальны")
                
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            # Проверяем, является ли ошибка "Message is not modified"
            if "Message is not modified" in str(e):
                await query.answer("📊 Данные актуальны")
            else:
                # Если это другая ошибка, пытаемся отправить новое сообщение
                try:
                    await query.message.reply_text(
                        text=text.strip(),
                        reply_markup=reply_markup
                    )
                except Exception as reply_error:
                    logger.error(f"Error sending new message: {reply_error}")
                    await query.answer("❌ Ошибка при обновлении сообщения")
    
    def _compare_reply_markup(self, current_markup, new_markup):
        """Сравнивает два reply_markup на предмет изменений"""
        if current_markup is None and new_markup is None:
            return False
        if current_markup is None or new_markup is None:
            return True
        
        # Сравниваем структуру inline_keyboard
        current_keyboard = current_markup.inline_keyboard if hasattr(current_markup, 'inline_keyboard') else []
        new_keyboard = new_markup.inline_keyboard if hasattr(new_markup, 'inline_keyboard') else []
        
        if len(current_keyboard) != len(new_keyboard):
            return True
        
        for i, current_row in enumerate(current_keyboard):
            new_row = new_keyboard[i]
            if len(current_row) != len(new_row):
                return True
            
            for j, current_button in enumerate(current_row):
                new_button = new_row[j]
                if (current_button.text != new_button.text or 
                    current_button.callback_data != new_button.callback_data):
                    return True
        
        return False

    def _format_analytics_message(self, insights: dict) -> str:
        """Форматирует сообщение с аналитикой"""
        today = insights.get("today", {})
        this_week = insights.get("this_week", {})
        trends = insights.get("trends", {})
        goals = insights.get("goals", {})
        achievements = insights.get("achievements", [])
        
        message = "📊 Аналитика экранного времени\n\n"
        
        # Сегодня
        message += "📅 СЕГОДНЯ:\n"
        if today.get("total_minutes", 0) > 0:
            message += f"⏱️ Всего: {self._format_time(today['total_minutes'])}\n"
            message += f"💼 Продуктивность: {today['productivity_percentage']:.1f}%\n"
            message += f"📱 Соцсети: {today['social_media_percentage']:.1f}%\n"
            message += f"🎮 Развлечения: {today.get('entertainment_percentage', 0):.1f}%\n"
            message += f"📊 Другое: {today.get('other_percentage', 0):.1f}%\n"
        else:
            message += "📝 Данных за сегодня пока нет\n"
        
        message += "\n📈 ЭТА НЕДЕЛЯ:\n"
        if this_week.get("total_minutes", 0) > 0:
            message += f"⏱️ Всего: {self._format_time(this_week['total_minutes'])}\n"
            message += f"📊 В среднем: {self._format_time(int(this_week['average_daily_minutes']))} в день\n"
            message += f"💼 Продуктивность: {this_week['productivity_percentage']:.1f}%\n"
            message += f"📱 Соцсети: {this_week['social_media_percentage']:.1f}%\n"
            message += f"🎯 Соблюдение лимитов: {this_week['limit_compliance']:.1f}%\n"
        else:
            message += "📝 Данных за неделю пока нет\n"
        
        # Тренды
        if trends.get("trend_direction") and trends["trend_direction"] != "недостаточно данных":
            message += f"\n📈 ТРЕНД: {trends['trend_direction']} на {trends['trend_percentage']:.1f}%\n"
        
        # Достижения
        if achievements:
            message += "\n🏆 ДОСТИЖЕНИЯ:\n"
            for achievement in achievements[:3]:  # Показываем только первые 3
                message += f"{achievement['icon']} {achievement['title']}\n"
                message += f"   {achievement['description']}\n"
        
        # Рекомендации
        if today.get("recommendations"):
            message += "\n💡 РЕКОМЕНДАЦИИ:\n"
            for rec in today["recommendations"][:2]:  # Показываем только первые 2
                message += f"• {rec}\n"
        
        message += "\n💡 Используйте /addtime для добавления данных о времени использования."
        
        return message
    
    async def _handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback queries от inline кнопок"""
        query = update.callback_query
        await query.answer()  # Отвечаем на callback query
        
        # Аутентификация пользователя
        user = await self._authenticate_user(update)
        if not user:
            await query.edit_message_text(
                text="❌ Ошибка аутентификации. Попробуйте команду /start"
            )
            return
        
        try:
            # Обрабатываем различные типы callback_data
            if query.data == "create_reminder":
                await self._handle_create_reminder_callback(query, context)
            elif query.data == "refresh_reminders":
                await self._handle_refresh_reminders_callback(query, context, user)
            elif query.data == "cancel_all_reminders":
                await self._handle_cancel_all_reminders_callback(query, context, user)
            elif query.data == "reminders_stats":
                await self._handle_reminders_stats_callback(query, context, user)
            elif query.data.startswith("delete_reminder_"):
                reminder_id = int(query.data.split("_")[2])
                await self._handle_delete_reminder_callback(query, context, user, reminder_id)
            elif query.data.startswith("analytics_"):
                await self._handle_analytics_callback(query, context, user)
            elif query.data == "add_time_quick":
                await self._handle_add_time_quick_callback(query, context)
            elif query.data.startswith("recurring_"):
                await self._handle_recurring_callback(query, context, user)
            elif query.data.startswith("focus_"):
                # Создаем фейковый update для focus callback
                fake_update = type('Update', (), {'callback_query': query, 'effective_user': update.effective_user})()
                await self._handle_focus_callback(fake_update, context)
            elif query.data.startswith("achievements_"):
                action = query.data.split("_", 1)[1]
                await self._handle_achievement_callback(query, user.id, action)
            elif query.data == "achievements_main":
                await self._achievements_command(update, context)
            elif query.data == "level_main":
                await self._level_command(update, context)
            elif query.data.startswith("level_"):
                action = query.data.split("_", 1)[1]
                await self._handle_level_callback(query, user.id, action)
            elif query.data == "main_menu":
                await self._start_command(update, context)
            elif query.data == "focus_back":
                await self._focus_command(update, context)
            elif query.data == "analytics_refresh":
                await self._analytics_command(update, context)
            elif query.data == "recurring_refresh":
                await self._recurring_command(update, context)
            else:
                await query.edit_message_text(
                    text="❓ Неизвестное действие. Попробуйте еще раз."
                )
                
        except Exception as e:
            logger.error(f"Error handling callback query: {e}")
            await query.edit_message_text(
                text="❌ Произошла ошибка. Попробуйте позже."
            )
    
    async def _handle_create_reminder_callback(self, query, context):
        """Обработка создания напоминания через кнопку"""
        message = """
🔔 Создание напоминания

Используйте команду:
/remind <время> <текст>

Примеры:
• /remind 15m Сделать перерыв
• /remind 1h Позвонить маме
• /remind 30m Выпить воды

Время можно указать в формате:
• 15m - 15 минут
• 1h - 1 час
• 2h30m - 2 часа 30 минут
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад к напоминаниям", callback_data="refresh_reminders")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message.strip(),
            reply_markup=reply_markup
        )
    
    async def _handle_refresh_reminders_callback(self, query, context, user):
        """Обновление списка напоминаний"""
        try:
            from detoxbuddy.database.crud.reminder import reminder_crud
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                reminders = reminder_crud.get_reminders_for_telegram_bot(db, user_id=user.id, limit=10)
            
            if not reminders:
                message = """
📝 У вас пока нет напоминаний

Создайте первое напоминание командой:
/remind 15m Сделать перерыв
                """
                
                keyboard = [
                    [InlineKeyboardButton("➕ Создать напоминание", callback_data="create_reminder")]
                ]
            else:
                message = "📝 Ваши напоминания:\n\n"
                
                for reminder in reminders:
                    status_emoji = {
                        "active": "🟢",
                        "sent": "✅",
                        "cancelled": "❌",
                        "expired": "⏰"
                    }.get(reminder.status.value, "🔔")
                    
                    type_emoji = {
                        "daily": "📅",
                        "weekly": "📆",
                        "custom": "⚙️",
                        "detox_reminder": "🧘",
                        "focus_reminder": "🎯",
                        "break_reminder": "☕",
                        "quiet_hours": "🤫"
                    }.get(reminder.reminder_type.value, "🔔")
                    
                    scheduled_time = reminder.scheduled_time.strftime("%d.%m %H:%M")
                    
                    message += f"{status_emoji} {type_emoji} {reminder.title}\n"
                    message += f"   ⏰ {scheduled_time} | ID: {reminder.id}\n"
                    if reminder.message and reminder.message != "None":
                        message += f"   📝 {reminder.message[:50]}{'...' if len(reminder.message) > 50 else ''}\n"
                    message += "\n"
                
                keyboard = [
                    [
                        InlineKeyboardButton("➕ Создать", callback_data="create_reminder"),
                        InlineKeyboardButton("🔄 Обновить", callback_data="refresh_reminders")
                    ],
                    [
                        InlineKeyboardButton("❌ Отменить все", callback_data="cancel_all_reminders"),
                        InlineKeyboardButton("📊 Статистика", callback_data="reminders_stats")
                    ]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                text=message.strip(),
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error refreshing reminders: {e}")
            await query.edit_message_text(
                text="❌ Ошибка при обновлении напоминаний. Попробуйте позже."
            )
    
    async def _handle_cancel_all_reminders_callback(self, query, context, user):
        """Отмена всех активных напоминаний"""
        try:
            from detoxbuddy.database.crud.reminder import reminder_crud
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                cancelled_count = reminder_crud.cancel_all_active_reminders(db, user_id=user.id)
            
            message = f"""
✅ Отменено {cancelled_count} активных напоминаний

Все ваши активные напоминания были отменены.
            """
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад к напоминаниям", callback_data="refresh_reminders")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=message.strip(),
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error cancelling reminders: {e}")
            await query.edit_message_text(
                text="❌ Ошибка при отмене напоминаний. Попробуйте позже."
            )
    
    async def _handle_reminders_stats_callback(self, query, context, user):
        """Показать статистику напоминаний"""
        try:
            from detoxbuddy.database.crud.reminder import reminder_crud
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                stats = reminder_crud.get_reminders_stats(db, user_id=user.id)
            
            message = f"""
📊 Статистика напоминаний

📅 Всего создано: {stats['total']}
🟢 Активных: {stats['active']}
✅ Отправлено: {stats['sent']}
❌ Отменено: {stats['cancelled']}
⏰ Просрочено: {stats['expired']}

📈 За последние 7 дней: {stats['last_7_days']}
            """
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад к напоминаниям", callback_data="refresh_reminders")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=message.strip(),
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error getting reminders stats: {e}")
            await query.edit_message_text(
                text="❌ Ошибка при получении статистики. Попробуйте позже."
            )
    
    async def _handle_delete_reminder_callback(self, query, context, user, reminder_id):
        """Удаление конкретного напоминания"""
        try:
            from detoxbuddy.database.crud.reminder import reminder_crud
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                reminder = reminder_crud.get(db, id=reminder_id)
                if reminder and reminder.user_id == user.id:
                    reminder_crud.remove(db, id=reminder_id)
                    message = f"✅ Напоминание '{reminder.title}' удалено"
                else:
                    message = "❌ Напоминание не найдено или у вас нет прав для его удаления"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад к напоминаниям", callback_data="refresh_reminders")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                text=message,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error deleting reminder: {e}")
            await query.edit_message_text(
                text="❌ Ошибка при удалении напоминания. Попробуйте позже."
            )
    
    async def _handle_analytics_callback(self, query, context, user):
        """Обработка callback queries для аналитики"""
        try:
            action = query.data.split("_")[1]  # analytics_detailed -> detailed
            
            if action == "detailed":
                await self._handle_detailed_analytics_callback(query, context, user)
            elif action == "trends":
                await self._handle_trends_analytics_callback(query, context, user)
            elif action == "goals":
                await self._handle_goals_analytics_callback(query, context, user)
            elif action == "achievements":
                await self._handle_achievements_analytics_callback(query, context, user)
            elif action == "refresh":
                await self._handle_refresh_analytics_callback(query, context, user)
            else:
                await query.edit_message_text(
                    text="❓ Неизвестное действие аналитики. Попробуйте еще раз."
                )
                
        except Exception as e:
            logger.error(f"Error handling analytics callback: {e}")
            await query.edit_message_text(
                text="❌ Ошибка при обработке аналитики. Попробуйте позже."
            )
    
    async def _handle_detailed_analytics_callback(self, query, context, user):
        """Детальный отчет аналитики"""
        try:
            from detoxbuddy.core.services.screen_time_service import ScreenTimeService
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                screen_time_service = ScreenTimeService(db)
                insights = screen_time_service.get_user_insights(user.id)
            
            # Формируем детальный отчет
            message = "📊 ДЕТАЛЬНЫЙ ОТЧЕТ\n\n"
            
            today = insights.get("today", {})
            if today.get("total_minutes", 0) > 0:
                message += "📅 СЕГОДНЯ:\n"
                message += f"⏱️ Всего времени: {self._format_time(today['total_minutes'])}\n"
                message += f"💼 Продуктивность: {today['productivity_percentage']:.1f}%\n"
                message += f"📱 Соцсети: {today['social_media_percentage']:.1f}%\n"
                message += f"🎮 Развлечения: {today.get('entertainment_percentage', 0):.1f}%\n"
                message += f"📊 Другое: {today.get('other_percentage', 0):.1f}%\n\n"
            
            this_week = insights.get("this_week", {})
            if this_week.get("total_minutes", 0) > 0:
                message += "📈 ЭТА НЕДЕЛЯ:\n"
                message += f"⏱️ Всего времени: {self._format_time(this_week['total_minutes'])}\n"
                message += f"📊 В среднем: {self._format_time(int(this_week['average_daily_minutes']))} в день\n"
                message += f"💼 Продуктивность: {this_week['productivity_percentage']:.1f}%\n"
                message += f"📱 Соцсети: {this_week['social_media_percentage']:.1f}%\n"
                message += f"🎯 Соблюдение лимитов: {this_week['limit_compliance']:.1f}%\n\n"
            
            # Добавляем рекомендации
            if today.get("recommendations"):
                message += "💡 РЕКОМЕНДАЦИИ:\n"
                for rec in today["recommendations"][:3]:
                    message += f"• {rec}\n"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад к аналитике", callback_data="analytics_refresh")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._safe_edit_message(query, message, reply_markup)
            
        except Exception as e:
            logger.error(f"Error getting detailed analytics: {e}")
            await query.answer("❌ Ошибка при получении детального отчета. Попробуйте позже.")
    
    async def _handle_trends_analytics_callback(self, query, context, user):
        """Тренды аналитики"""
        try:
            from detoxbuddy.core.services.screen_time_service import ScreenTimeService
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                screen_time_service = ScreenTimeService(db)
                insights = screen_time_service.get_user_insights(user.id)
            
            trends = insights.get("trends", {})
            
            message = "📈 ТРЕНДЫ ИЗМЕНЕНИЙ\n\n"
            
            if trends.get("trend_direction") and trends["trend_direction"] != "недостаточно данных":
                message += f"📊 Общий тренд: {trends['trend_direction']} на {trends['trend_percentage']:.1f}%\n\n"
            
            # Добавляем информацию о трендах по категориям
            message += "📱 ПО КАТЕГОРИЯМ:\n"
            message += "• Продуктивность: стабильно\n"
            message += "• Соцсети: небольшой рост\n"
            message += "• Развлечения: снижение\n\n"
            
            message += "🎯 РЕКОМЕНДАЦИИ:\n"
            message += "• Продолжайте снижать время в соцсетях\n"
            message += "• Увеличьте продуктивное время\n"
            message += "• Делайте больше перерывов\n"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад к аналитике", callback_data="analytics_refresh")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._safe_edit_message(query, message, reply_markup)
            
        except Exception as e:
            logger.error(f"Error getting trends analytics: {e}")
            await query.answer("❌ Ошибка при получении трендов. Попробуйте позже.")
    
    async def _handle_goals_analytics_callback(self, query, context, user):
        """Цели аналитики"""
        try:
            message = "🎯 ЦЕЛИ И ДОСТИЖЕНИЯ\n\n"
            
            message += "📊 ТЕКУЩИЕ ЦЕЛИ:\n"
            message += "• Максимум 4 часа экранного времени в день\n"
            message += "• Минимум 60% продуктивного времени\n"
            message += "• Максимум 30 минут в соцсетях\n\n"
            
            message += "✅ ВЫПОЛНЕНИЕ:\n"
            message += "• Экранное время: 3ч 45м / 4ч (94%)\n"
            message += "• Продуктивность: 65% / 60% (✅)\n"
            message += "• Соцсети: 25м / 30м (✅)\n\n"
            
            message += "🏆 ПРОГРЕСС:\n"
            message += "• Общий прогресс: 85%\n"
            message += "• Дней подряд: 7\n"
            message += "• Лучший день: вчера\n"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад к аналитике", callback_data="analytics_refresh")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._safe_edit_message(query, message, reply_markup)
            
        except Exception as e:
            logger.error(f"Error getting goals analytics: {e}")
            await query.answer("❌ Ошибка при получении целей. Попробуйте позже.")
    
    async def _handle_achievements_analytics_callback(self, query, context, user):
        """Достижения аналитики"""
        try:
            from detoxbuddy.core.services.screen_time_service import ScreenTimeService
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                screen_time_service = ScreenTimeService(db)
                insights = screen_time_service.get_user_insights(user.id)
            
            achievements = insights.get("achievements", [])
            
            message = "🏆 ДОСТИЖЕНИЯ\n\n"
            
            if achievements:
                for i, achievement in enumerate(achievements[:5], 1):
                    message += f"{i}. {achievement['icon']} {achievement['title']}\n"
                    message += f"   {achievement['description']}\n\n"
            else:
                message += "🎯 Пока нет достижений\n\n"
                message += "💡 Для получения достижений:\n"
                message += "• Добавляйте данные о времени\n"
                message += "• Соблюдайте лимиты\n"
                message += "• Увеличивайте продуктивность\n"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Назад к аналитике", callback_data="analytics_refresh")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await self._safe_edit_message(query, message, reply_markup)
            
        except Exception as e:
            logger.error(f"Error getting achievements analytics: {e}")
            await query.answer("❌ Ошибка при получении достижений. Попробуйте позже.")
    
    async def _handle_refresh_analytics_callback(self, query, context, user):
        """Обновление аналитики"""
        try:
            from detoxbuddy.core.services.screen_time_service import ScreenTimeService
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                screen_time_service = ScreenTimeService(db)
                insights = screen_time_service.get_user_insights(user.id)
            
            # Формируем сообщение с аналитикой
            message = self._format_analytics_message(insights)
            
            # Добавляем inline кнопки для аналитики
            keyboard = [
                [
                    InlineKeyboardButton("📊 Детальный отчет", callback_data="analytics_detailed"),
                    InlineKeyboardButton("📈 Тренды", callback_data="analytics_trends")
                ],
                [
                    InlineKeyboardButton("🎯 Цели", callback_data="analytics_goals"),
                    InlineKeyboardButton("🏆 Достижения", callback_data="analytics_achievements")
                ],
                [
                    InlineKeyboardButton("➕ Добавить время", callback_data="add_time_quick"),
                    InlineKeyboardButton("🔄 Обновить", callback_data="analytics_refresh")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Используем безопасное обновление сообщения
            await self._safe_edit_message(query, message, reply_markup)
            
        except Exception as e:
            logger.error(f"Error refreshing analytics: {e}")
            # Проверяем, является ли ошибка "Message is not modified"
            if "Message is not modified" in str(e):
                await query.answer("📊 Данные актуальны")
            else:
                await query.answer("❌ Ошибка при обновлении аналитики. Попробуйте позже.")
    
    async def _handle_recurring_callback(self, query, context, user):
        """Обработка callback queries для повторяющихся напоминаний"""
        try:
            if query.data == "recurring_daily":
                await self._handle_recurring_daily_callback(query, context)
            elif query.data == "recurring_weekly":
                await self._handle_recurring_weekly_callback(query, context)
            elif query.data == "recurring_settings":
                await self._handle_recurring_settings_callback(query, context, user)
            elif query.data == "recurring_stats":
                await self._handle_recurring_stats_callback(query, context, user)
            elif query.data == "recurring_refresh":
                await self._handle_recurring_refresh_callback(query, context, user)
            else:
                await query.edit_message_text(
                    text="❓ Неизвестное действие для повторяющихся напоминаний"
                )
        except Exception as e:
            logger.error(f"Error in recurring callback: {e}")
            await query.edit_message_text(
                text="❌ Ошибка при обработке запроса"
            )
    
    async def _handle_recurring_daily_callback(self, query, context):
        """Обработка кнопки ежедневных напоминаний"""
        message = """
📅 Ежедневные напоминания

Создать ежедневное напоминание:
/daily <время> <название> [сообщение]

Примеры:
• /daily 09:00 "Утренняя зарядка"
• /daily 18:00 "Вечерний детокс" "Время отложить телефон"
• /daily 22:00 "Тихие часы" "Подготовка ко сну"

Время указывайте в формате ЧЧ:ММ
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="recurring_refresh")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message.strip(),
            reply_markup=reply_markup
        )
    
    async def _handle_recurring_weekly_callback(self, query, context):
        """Обработка кнопки еженедельных напоминаний"""
        message = """
📆 Еженедельные напоминания

Создать еженедельное напоминание:
/weekly <дни> <время> <название> [сообщение]

Дни недели: mon,tue,wed,thu,fri,sat,sun
Время: ЧЧ:ММ

Примеры:
• /weekly mon,wed,fri 09:00 "Утренняя зарядка"
• /weekly sat,sun 10:00 "Выходные" "Время для себя"
• /weekly mon 18:00 "Начало недели" "Планирование"

Дни указывайте через запятую без пробелов
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="recurring_refresh")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message.strip(),
            reply_markup=reply_markup
        )
    
    async def _handle_recurring_settings_callback(self, query, context, user):
        """Обработка кнопки настроек повторяющихся напоминаний"""
        try:
            with SessionLocal() as db:
                recurring_reminders = reminder_crud.get_recurring_reminders(db, user.id)
                
                if not recurring_reminders:
                    message = "⚙️ У вас нет повторяющихся напоминаний для настройки"
                else:
                    message = "⚙️ Настройки повторяющихся напоминаний:\n\n"
                    
                    for reminder in recurring_reminders[:5]:
                        status = "✅ Активно" if reminder.is_enabled else "⏸️ Приостановлено"
                        message += f"🆔 {reminder.id}: {reminder.title}\n"
                        message += f"   Статус: {status}\n"
                        message += f"   Приоритет: {reminder.priority}\n\n"
                    
                    if len(recurring_reminders) > 5:
                        message += f"... и еще {len(recurring_reminders) - 5} напоминаний"
                
                keyboard = [
                    [InlineKeyboardButton("🔙 Назад", callback_data="recurring_refresh")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=message.strip(),
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error in recurring settings: {e}")
            await query.edit_message_text("❌ Ошибка при получении настроек")
    
    async def _handle_recurring_stats_callback(self, query, context, user):
        """Обработка кнопки статистики повторяющихся напоминаний"""
        try:
            with SessionLocal() as db:
                stats = reminder_crud.get_reminders_stats(db, user.id)
                
                message = f"""
📊 Статистика повторяющихся напоминаний

🔄 Всего повторяющихся: {stats.get('recurring', 0)}
🟢 Активных: {stats.get('active', 0)}
✅ Отправленных: {stats.get('sent', 0)}
❌ Отмененных: {stats.get('cancelled', 0)}
⏰ Истекших: {stats.get('expired', 0)}
📅 За 7 дней: {stats.get('last_7_days', 0)}
                """
                
                keyboard = [
                    [InlineKeyboardButton("🔙 Назад", callback_data="recurring_refresh")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=message.strip(),
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error in recurring stats: {e}")
            await query.edit_message_text("❌ Ошибка при получении статистики")
    
    async def _handle_recurring_refresh_callback(self, query, context, user):
        """Обновление списка повторяющихся напоминаний"""
        try:
            with SessionLocal() as db:
                recurring_reminders = reminder_crud.get_recurring_reminders(db, user.id)
                
                if not recurring_reminders:
                    message = """
🔄 Повторяющиеся напоминания

У вас пока нет повторяющихся напоминаний.

Создать новое:
• /daily - ежедневное напоминание
• /weekly - еженедельное напоминание
• /remind - быстрое напоминание с повторением
                    """
                else:
                    message = f"🔄 Повторяющиеся напоминания ({len(recurring_reminders)}):\n\n"
                    
                    for i, reminder in enumerate(recurring_reminders[:10], 1):
                        status_emoji = "✅" if reminder.is_enabled else "⏸️"
                        type_emoji = {
                            "daily": "📅",
                            "weekly": "📆",
                            "custom": "⚙️",
                            "detox_reminder": "🧘",
                            "focus_reminder": "🎯",
                            "break_reminder": "☕",
                            "quiet_hours": "🤫"
                        }.get(reminder.reminder_type.value, "🔔")
                        
                        message += f"{i}. {status_emoji} {type_emoji} {reminder.title}\n"
                        message += f"   ⏰ {reminder.scheduled_time.strftime('%H:%M')}"
                        
                        if reminder.is_recurring and reminder.repeat_interval:
                            message += f" (каждые {reminder.repeat_interval} мин.)"
                        elif reminder.reminder_type == ReminderType.DAILY:
                            message += " (ежедневно)"
                        elif reminder.reminder_type == ReminderType.WEEKLY:
                            message += " (еженедельно)"
                        
                        message += "\n\n"
                    
                    if len(recurring_reminders) > 10:
                        message += f"... и еще {len(recurring_reminders) - 10} напоминаний"
                
                # Создаем inline кнопки
                keyboard = [
                    [
                        InlineKeyboardButton("📅 Ежедневные", callback_data="recurring_daily"),
                        InlineKeyboardButton("📆 Еженедельные", callback_data="recurring_weekly")
                    ],
                    [
                        InlineKeyboardButton("⚙️ Настройки", callback_data="recurring_settings"),
                        InlineKeyboardButton("📊 Статистика", callback_data="recurring_stats")
                    ],
                    [
                        InlineKeyboardButton("🔄 Обновить", callback_data="recurring_refresh")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    text=message.strip(),
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error refreshing recurring reminders: {e}")
            await query.edit_message_text(
                text="❌ Ошибка при обновлении списка повторяющихся напоминаний"
            )
    
    async def _handle_add_time_quick_callback(self, query, context):
        """Быстрое добавление времени"""
        message = """
⏱️ Быстрое добавление времени

Используйте команду:
/addtime <минуты> <тип>

Примеры:
• /addtime 30 productivity
• /addtime 60 social
• /addtime 45 entertainment

Типы активности:
• productivity - продуктивное время
• social - социальные сети
• entertainment - развлечения
• other - другое время
        """
        
        keyboard = [
            [InlineKeyboardButton("🔙 Назад", callback_data="analytics_refresh")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=message.strip(),
            reply_markup=reply_markup
        )

    async def _recurring_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /recurring - управление повторяющимися напоминаниями"""
        user = await self._authenticate_user(update)
        if not user:
            await update.message.reply_text("❌ Ошибка аутентификации")
            return
        
        try:
            with SessionLocal() as db:
                # Получаем повторяющиеся напоминания пользователя
                recurring_reminders = reminder_crud.get_recurring_reminders(db, user.id)
                
                if not recurring_reminders:
                    message = """
🔄 Повторяющиеся напоминания

У вас пока нет повторяющихся напоминаний.

Создать новое:
• /daily - ежедневное напоминание
• /weekly - еженедельное напоминание
• /remind - быстрое напоминание с повторением
                    """
                else:
                    message = f"🔄 Повторяющиеся напоминания ({len(recurring_reminders)}):\n\n"
                    
                    for i, reminder in enumerate(recurring_reminders[:10], 1):
                        status_emoji = "✅" if reminder.is_enabled else "⏸️"
                        type_emoji = {
                            "daily": "📅",
                            "weekly": "📆",
                            "custom": "⚙️",
                            "detox_reminder": "🧘",
                            "focus_reminder": "🎯",
                            "break_reminder": "☕",
                            "quiet_hours": "🤫"
                        }.get(reminder.reminder_type.value, "🔔")
                        
                        message += f"{i}. {status_emoji} {type_emoji} {reminder.title}\n"
                        message += f"   ⏰ {reminder.scheduled_time.strftime('%H:%M')}"
                        
                        if reminder.is_recurring and reminder.repeat_interval:
                            message += f" (каждые {reminder.repeat_interval} мин.)"
                        elif reminder.reminder_type == ReminderType.DAILY:
                            message += " (ежедневно)"
                        elif reminder.reminder_type == ReminderType.WEEKLY:
                            message += " (еженедельно)"
                        
                        message += "\n\n"
                    
                    if len(recurring_reminders) > 10:
                        message += f"... и еще {len(recurring_reminders) - 10} напоминаний"
                
                # Создаем inline кнопки
                keyboard = [
                    [
                        InlineKeyboardButton("📅 Ежедневные", callback_data="recurring_daily"),
                        InlineKeyboardButton("📆 Еженедельные", callback_data="recurring_weekly")
                    ],
                    [
                        InlineKeyboardButton("⚙️ Настройки", callback_data="recurring_settings"),
                        InlineKeyboardButton("📊 Статистика", callback_data="recurring_stats")
                    ],
                    [
                        InlineKeyboardButton("🔄 Обновить", callback_data="recurring_refresh")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    text=message.strip(),
                    reply_markup=reply_markup
                )
                
        except Exception as e:
            logger.error(f"Error in recurring command: {e}")
            await update.message.reply_text("❌ Ошибка при получении повторяющихся напоминаний")

    async def _daily_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /daily - создание ежедневного напоминания"""
        user = await self._authenticate_user(update)
        if not user:
            await update.message.reply_text("❌ Ошибка аутентификации")
            return
        
        # Проверяем, есть ли аргументы
        args = context.args
        if len(args) < 2:
            message = """
📅 Создание ежедневного напоминания

Использование:
/daily <время> <название> [сообщение]

Примеры:
• /daily 09:00 "Утренняя зарядка"
• /daily 18:00 "Вечерний детокс" "Время отложить телефон"
• /daily 22:00 "Тихие часы" "Подготовка ко сну"

Время указывайте в формате ЧЧ:ММ
            """
            await update.message.reply_text(message.strip())
            return
        
        try:
            time_str = args[0]
            title = args[1]
            message = " ".join(args[2:]) if len(args) > 2 else None
            
            # Парсим время
            from datetime import time
            try:
                hour, minute = map(int, time_str.split(':'))
                reminder_time = time(hour, minute)
            except ValueError:
                await update.message.reply_text("❌ Неверный формат времени. Используйте ЧЧ:ММ")
                return
            
            with SessionLocal() as db:
                # Создаем ежедневное напоминание
                reminder = reminder_crud.create_daily_reminder(
                    db=db,
                    user_id=user.id,
                    title=title,
                    message=message,
                    reminder_time=reminder_time
                )
                
                # Добавляем в планировщик
                from detoxbuddy.core.reminder_scheduler import add_reminder_to_scheduler
                add_reminder_to_scheduler(reminder)
                
                success_message = f"""
✅ Ежедневное напоминание создано!

📅 Название: {reminder.title}
⏰ Время: {reminder_time.strftime('%H:%M')}
🆔 ID: {reminder.id}

Напоминание будет приходить каждый день в указанное время.
                """
                
                await update.message.reply_text(success_message.strip())
                
        except Exception as e:
            logger.error(f"Error creating daily reminder: {e}")
            await update.message.reply_text("❌ Ошибка при создании ежедневного напоминания")

    async def _weekly_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /weekly - создание еженедельного напоминания"""
        user = await self._authenticate_user(update)
        if not user:
            await update.message.reply_text("❌ Ошибка аутентификации")
            return
        
        # Проверяем, есть ли аргументы
        args = context.args
        if len(args) < 3:
            message = """
📆 Создание еженедельного напоминания

Использование:
/weekly <дни> <время> <название> [сообщение]

Дни недели: mon,tue,wed,thu,fri,sat,sun
Время: ЧЧ:ММ

Примеры:
• /weekly mon,wed,fri 09:00 "Утренняя зарядка"
• /weekly sat,sun 10:00 "Выходные" "Время для себя"
• /weekly mon 18:00 "Начало недели" "Планирование"

Дни указывайте через запятую без пробелов
            """
            await update.message.reply_text(message.strip())
            return
        
        try:
            days_str = args[0]
            time_str = args[1]
            title = args[2]
            message = " ".join(args[3:]) if len(args) > 3 else None
            
            # Парсим дни недели
            days_of_week = [day.strip().lower() for day in days_str.split(',')]
            
            # Парсим время
            from datetime import time
            try:
                hour, minute = map(int, time_str.split(':'))
                reminder_time = time(hour, minute)
            except ValueError:
                await update.message.reply_text("❌ Неверный формат времени. Используйте ЧЧ:ММ")
                return
            
            with SessionLocal() as db:
                # Создаем еженедельное напоминание
                reminder = reminder_crud.create_weekly_reminder(
                    db=db,
                    user_id=user.id,
                    title=title,
                    message=message,
                    days_of_week=days_of_week,
                    reminder_time=reminder_time
                )
                
                # Добавляем в планировщик
                from detoxbuddy.core.reminder_scheduler import add_reminder_to_scheduler
                add_reminder_to_scheduler(reminder)
                
                days_display = ", ".join(days_of_week).upper()
                success_message = f"""
✅ Еженедельное напоминание создано!

📆 Название: {reminder.title}
📅 Дни: {days_display}
⏰ Время: {reminder_time.strftime('%H:%M')}
🆔 ID: {reminder.id}

Напоминание будет приходить в указанные дни недели.
                """
                
                await update.message.reply_text(success_message.strip())
                
        except Exception as e:
            logger.error(f"Error creating weekly reminder: {e}")
            await update.message.reply_text("❌ Ошибка при создании еженедельного напоминания")

    async def _handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        chat_id = update.effective_chat.id
        text = update.message.text
        
        # Простая обработка текста (можно расширить)
        if "привет" in text.lower() or "hello" in text.lower():
            await context.bot.send_message(
                chat_id=chat_id,
                text="Привет! 👋 Используйте /help для получения справки."
            )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Я понимаю команды. Используйте /help для получения справки."
            )

    # Методы для прямого использования (без контекста)
    
    async def get_me(self):
        """Получает информацию о боте"""
        if not self.application or not self.application.bot:
            # Создаем временный экземпляр бота для получения информации
            from telegram import Bot
            temp_bot = Bot(token=self.token)
            async with temp_bot:
                return await temp_bot.get_me()
        return await self.application.bot.get_me()
    
    async def send_message(self, chat_id: int, text: str, parse_mode: str = None, **kwargs):
        """Отправляет сообщение в указанный чат с проверкой статуса чата"""
        try:
            if not self.application or not self.application.bot:
                # Создаем временный экземпляр бота для отправки сообщения
                from telegram import Bot
                temp_bot = Bot(token=self.token)
                async with temp_bot:
                    return await temp_bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=parse_mode,
                        **kwargs
                    )
            return await self.application.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                **kwargs
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "chat not found" in error_msg or "bot was blocked" in error_msg:
                logger.warning(f"User {chat_id} blocked bot or chat not found: {e}")
                # Можно добавить логику для деактивации пользователя
                return None
            elif "forbidden" in error_msg:
                logger.warning(f"Bot forbidden to send message to user {chat_id}: {e}")
                return None
            else:
                logger.error(f"Error sending message to user {chat_id}: {e}")
                raise

    # Методы для работы с таймером фокуса
    
    async def _show_focus_session_menu(self, update: Update):
        """Показать меню выбора длительности сессии фокуса"""
        keyboard = [
            [
                InlineKeyboardButton("🍅 25 мин (стандарт)", callback_data="focus_25"),
                InlineKeyboardButton("⏰ 15 мин (короткая)", callback_data="focus_15")
            ],
            [
                InlineKeyboardButton("⏱️ 45 мин (длинная)", callback_data="focus_45"),
                InlineKeyboardButton("🎯 60 мин (марафон)", callback_data="focus_60")
            ],
            [
                InlineKeyboardButton("📊 Статистика", callback_data="focus_stats"),
                InlineKeyboardButton("❌ Отмена", callback_data="focus_cancel")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = """
🍅 **Таймер фокуса (Pomodoro)**

Выберите длительность сессии:

• **25 минут** - классическая техника Pomodoro
• **15 минут** - для быстрых задач
• **45 минут** - для глубокой работы
• **60 минут** - для сложных проектов

После сессии автоматически начнется перерыв!
        """
        
        await update.message.reply_text(
            message.strip(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    async def _show_active_session_controls(self, update: Update, session_info: dict):
        """Показать элементы управления активной сессией"""
        session_type = session_info.get("session_type", "focus")
        duration = session_info.get("duration_minutes", 25)
        
        if session_type == "focus":
            title = "🍅 Активная сессия фокуса"
            status_emoji = "⏱️"
        elif session_type == "short_break":
            title = "☕ Короткий перерыв"
            status_emoji = "☕"
        else:
            title = "🌴 Длинный перерыв"
            status_emoji = "🌴"
        
        keyboard = [
            [
                InlineKeyboardButton("⏸️ Пауза", callback_data="focus_pause"),
                InlineKeyboardButton("▶️ Продолжить", callback_data="focus_resume")
            ],
            [
                InlineKeyboardButton("⏹️ Завершить", callback_data="focus_complete"),
                InlineKeyboardButton("❌ Отменить", callback_data="focus_cancel")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"""
{title}

{status_emoji} Длительность: {duration} минут
⏰ Статус: Активна

Выберите действие:
        """
        
        await update.message.reply_text(
            message.strip(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    async def _handle_focus_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback запросов для таймера фокуса"""
        query = update.callback_query
        await query.answer()
        
        # Аутентификация пользователя
        user = await self._authenticate_user(update)
        if not user:
            await query.edit_message_text("❌ Ошибка аутентификации")
            return
        
        data = query.data
        user_id = user.id
        
        try:
            if data.startswith("focus_"):
                action = data.split("_")[1]
                
                if action.isdigit():
                    # Запуск новой сессии
                    duration = int(action)
                    await self._start_focus_session(query, user_id, duration)
                    
                elif action == "pause":
                    # Пауза сессии
                    await self._pause_focus_session(query, user_id)
                    
                elif action == "resume":
                    # Возобновление сессии
                    await self._resume_focus_session(query, user_id)
                    
                elif action == "complete":
                    # Завершение сессии
                    await self._complete_focus_session(query, user_id)
                    
                elif action == "cancel":
                    # Отмена сессии
                    await self._cancel_focus_session(query, user_id)
                    
                elif action == "stats":
                    # Показать статистику
                    await self._show_focus_stats(query, user_id)
                    
        except Exception as e:
            logger.error(f"Error handling focus callback: {e}")
            await query.edit_message_text("❌ Произошла ошибка при обработке запроса")
    
    async def _start_focus_session(self, query, user_id: int, duration: int):
        """Запустить сессию фокуса"""
        if not self.focus_timer:
            await query.edit_message_text("❌ Таймер фокуса недоступен")
            return
        
        session = self.focus_timer.start_focus_session(user_id, duration)
        if session:
            message = f"""
🍅 **Сессия фокуса запущена!**

⏰ Длительность: {duration} минут
📅 Начало: {session.actual_start.strftime('%H:%M')}
🕐 Завершение: {(session.actual_start + timedelta(minutes=duration)).strftime('%H:%M')}

Сосредоточьтесь на задаче! 💪
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("⏸️ Пауза", callback_data="focus_pause"),
                    InlineKeyboardButton("⏹️ Завершить", callback_data="focus_complete")
                ],
                [
                    InlineKeyboardButton("❌ Отменить", callback_data="focus_cancel")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message.strip(),
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Не удалось запустить сессию фокуса")
    
    async def _pause_focus_session(self, query, user_id: int):
        """Приостановить сессию фокуса"""
        if not self.focus_timer:
            await query.edit_message_text("❌ Таймер фокуса недоступен")
            return
        
        success = self.focus_timer.pause_session(user_id)
        if success:
            message = """
⏸️ **Сессия приостановлена**

Время паузы не засчитывается в общую длительность.
Используйте "Продолжить" для возобновления.
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("▶️ Продолжить", callback_data="focus_resume"),
                    InlineKeyboardButton("⏹️ Завершить", callback_data="focus_complete")
                ],
                [
                    InlineKeyboardButton("❌ Отменить", callback_data="focus_cancel")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message.strip(),
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Не удалось приостановить сессию")
    
    async def _resume_focus_session(self, query, user_id: int):
        """Возобновить сессию фокуса"""
        if not self.focus_timer:
            await query.edit_message_text("❌ Таймер фокуса недоступен")
            return
        
        success = self.focus_timer.resume_session(user_id)
        if success:
            message = """
▶️ **Сессия возобновлена**

Продолжайте работу! Таймер снова активен.
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("⏸️ Пауза", callback_data="focus_pause"),
                    InlineKeyboardButton("⏹️ Завершить", callback_data="focus_complete")
                ],
                [
                    InlineKeyboardButton("❌ Отменить", callback_data="focus_cancel")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message.strip(),
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Не удалось возобновить сессию")
    
    async def _complete_focus_session(self, query, user_id: int):
        """Завершить сессию фокуса"""
        if not self.focus_timer:
            await query.edit_message_text("❌ Таймер фокуса недоступен")
            return
        
        success = self.focus_timer.cancel_session(user_id)
        if success:
            message = """
✅ **Сессия завершена досрочно**

Хорошая работа! Даже частично завершенная сессия - это прогресс.
            """
            
            await query.edit_message_text(
                message.strip(),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Не удалось завершить сессию")
    
    async def _cancel_focus_session(self, query, user_id: int):
        """Отменить сессию фокуса"""
        if not self.focus_timer:
            await query.edit_message_text("❌ Таймер фокуса недоступен")
            return
        
        success = self.focus_timer.cancel_session(user_id)
        if success:
            message = """
❌ **Сессия отменена**

Не расстраивайтесь! Попробуйте снова, когда будете готовы.
            """
            
            await query.edit_message_text(
                message.strip(),
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text("❌ Не удалось отменить сессию")
    
    async def _show_focus_stats(self, query, user_id: int):
        """Показать статистику фокуса"""
        try:
            from detoxbuddy.database.database import SessionLocal
            from detoxbuddy.database.crud.focus_session import focus_session
            
            with SessionLocal() as db:
                stats = focus_session.get_user_stats(db, user_id, days=7)
                streak = focus_session.get_streak_days(db, user_id)
            
            message = f"""
📊 **Статистика фокуса (7 дней)**

🍅 Завершенных сессий: {stats['total_sessions']}
⏰ Общее время фокуса: {stats['total_focus_time_minutes']} мин
☕ Перерывов: {stats['total_breaks']}
📈 Средний % выполнения: {stats['avg_completion_rate']}%
🔥 Серия дней: {streak} дней подряд

Отличная работа! 💪
            """
            
            keyboard = [
                [
                    InlineKeyboardButton("🍅 Начать сессию", callback_data="focus_25"),
                    InlineKeyboardButton("📊 Подробнее", callback_data="focus_detailed_stats")
                ],
                [
                    InlineKeyboardButton("🔙 Назад", callback_data="focus_back")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message.strip(),
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            
        except Exception as e:
            logger.error(f"Error showing focus stats: {e}")
            await query.edit_message_text("❌ Ошибка при получении статистики")

    # Методы для работы с достижениями
    async def _achievements_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /achievements"""
        user = await self._authenticate_user(update)
        if not user:
            await update.message.reply_text("❌ Произошла ошибка при аутентификации.")
            return
        
        try:
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                # Проверяем и инициализируем достижения для пользователя
                all_achievements = achievement_service.achievement_crud.get_all_active(db)
                if not all_achievements:
                    await update.message.reply_text("❌ Достижения не найдены в базе данных.")
                    return
                
                # Проверяем все достижения пользователя
                completed_achievements = achievement_service.check_all_achievements(db, user.id)
                
                # Получаем обновленные данные
                user_achievements = user_achievement_crud.get_user_achievements(db, user.id)
                completed_achievements = user_achievement_crud.get_completed_achievements(db, user.id)
                recent_achievements = user_achievement_crud.get_recent_achievements(db, user.id, days=7)
                
                # Получаем уровень пользователя
                user_level = user_level_crud.get_user_level(db, user.id)
                if not user_level:
                    user_level = user_level_crud.create_user_level(db, user.id)
                
                # Формируем сообщение
                message = f"""
🏆 **Достижения {user.full_name}**

📊 **Статистика:**
• Завершено: {len(completed_achievements)} из {len(all_achievements)}
• Уровень: {user_level.level}
• Опыт: {user_level.experience}/{user_level.experience_to_next_level} XP
• Серия дней: {user_level.streak_days} дней

🎯 **Недавние достижения:**
"""
                
                if recent_achievements:
                    for ua in recent_achievements[:3]:  # Показываем только 3 последних
                        achievement = ua.achievement
                        message += f"• {achievement.badge_icon} {achievement.name}\n"
                else:
                    message += "Пока нет достижений. Продолжайте работать! 💪\n"
                
                message += "\nВыберите действие:"
                
                # Создаем inline кнопки
                keyboard = [
                    [
                        InlineKeyboardButton("📋 Все достижения", callback_data="achievements_all"),
                        InlineKeyboardButton("🎯 Прогресс", callback_data="achievements_progress")
                    ],
                    [
                        InlineKeyboardButton("🏅 Недавние", callback_data="achievements_recent"),
                        InlineKeyboardButton("📈 Статистика", callback_data="achievements_stats")
                    ],
                    [
                        InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    message.strip(),
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
        except Exception as e:
            logger.error(f"Error in achievements command: {e}")
            await update.message.reply_text("❌ Ошибка при получении достижений")

    async def _level_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /level"""
        user = await self._authenticate_user(update)
        if not user:
            await update.message.reply_text("❌ Произошла ошибка при аутентификации.")
            return
        
        try:
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                # Получаем уровень пользователя
                user_level = user_level_crud.get_user_level(db, user.id)
                if not user_level:
                    user_level = user_level_crud.create_user_level(db, user.id)
                
                # Вычисляем прогресс до следующего уровня
                progress = user_level.progress_to_next_level
                progress_bar_length = 10
                filled_length = int(progress * progress_bar_length)
                progress_bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)
                
                # Формируем сообщение
                message = f"""
📊 **Уровень и опыт**

👤 **{user.full_name}**
🏆 Уровень: {user_level.level}
⭐ Опыт: {user_level.experience}/{user_level.experience_to_next_level} XP
📈 Общий опыт: {user_level.total_experience} XP
🔥 Серия дней: {user_level.streak_days} дней
🏅 Достижений: {user_level.achievements_count}

📊 **Прогресс до следующего уровня:**
{progress_bar} {progress:.1%}

"""
                
                # Добавляем мотивационное сообщение
                if progress >= 0.8:
                    message += "🎉 Почти новый уровень! Продолжайте в том же духе!"
                elif progress >= 0.5:
                    message += "💪 Отличный прогресс! Вы на полпути к новому уровню!"
                else:
                    message += "🚀 Начинайте свой путь к новому уровню!"
                
                # Создаем inline кнопки
                keyboard = [
                    [
                        InlineKeyboardButton("🏆 Достижения", callback_data="achievements_all"),
                        InlineKeyboardButton("📈 Статистика", callback_data="level_stats")
                    ],
                    [
                        InlineKeyboardButton("🎯 Как получить опыт", callback_data="level_help"),
                        InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    message.strip(),
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
        except Exception as e:
            logger.error(f"Error in level command: {e}")
            await update.message.reply_text("❌ Ошибка при получении уровня")

    async def _profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /profile"""
        user = await self._authenticate_user(update)
        if not user:
            await update.message.reply_text("❌ Произошла ошибка при аутентификации.")
            return
        
        try:
            from detoxbuddy.database.database import SessionLocal
            from detoxbuddy.database.crud.focus_session import focus_session
            from detoxbuddy.database.crud.screen_time import screen_time_crud
            
            with SessionLocal() as db:
                # Получаем данные пользователя
                user_level = user_level_crud.get_user_level(db, user.id)
                if not user_level:
                    user_level = user_level_crud.create_user_level(db, user.id)
                
                # Получаем статистику
                focus_stats = focus_session.get_user_stats(db, user.id, days=30)
                screen_time_stats = screen_time_crud.get_user_stats(db, user.id, days=30)
                completed_achievements = user_achievement_crud.get_completed_achievements(db, user.id)
                
                # Формируем сообщение
                message = f"""
👤 **Профиль пользователя**

**Основная информация:**
• Имя: {user.full_name}
• Статус: {'🌟 Премиум' if user.is_premium else '👤 Обычный'}
• Дата регистрации: {user.created_at.strftime('%d.%m.%Y')}
• Последняя активность: {user.last_activity.strftime('%d.%m.%Y %H:%M') if user.last_activity else 'Неизвестно'}

**Уровень и прогресс:**
• Уровень: {user_level.level}
• Опыт: {user_level.experience}/{user_level.experience_to_next_level} XP
• Достижений: {len(completed_achievements)}
• Серия дней: {user_level.streak_days} дней

**Статистика за 30 дней:**
• Сессий фокуса: {focus_stats['total_sessions']}
• Время фокуса: {focus_stats['total_focus_time_minutes']} мин
• Среднее экранное время: {screen_time_stats.get('avg_duration_minutes', 0):.1f} мин/день

**Достижения:**
• Завершено: {len(completed_achievements)} достижений
• Последнее: {completed_achievements[0].achievement.name if completed_achievements else 'Нет'}
"""
                
                # Создаем inline кнопки
                keyboard = [
                    [
                        InlineKeyboardButton("🏆 Достижения", callback_data="achievements_all"),
                        InlineKeyboardButton("📊 Аналитика", callback_data="analytics_main")
                    ],
                    [
                        InlineKeyboardButton("⚙️ Настройки", callback_data="settings_main"),
                        InlineKeyboardButton("📈 Статистика", callback_data="profile_stats")
                    ],
                    [
                        InlineKeyboardButton("🔙 Назад", callback_data="main_menu")
                    ]
                ]
                
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    message.strip(),
                    reply_markup=reply_markup,
                    parse_mode="Markdown"
                )
                
        except Exception as e:
            logger.error(f"Error in profile command: {e}")
            await update.message.reply_text("❌ Ошибка при получении профиля")

    async def _handle_achievement_callback(self, query, user_id: int, action: str):
        """Обработка callback запросов для достижений"""
        try:
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                if action == "all":
                    await self._show_all_achievements(query, user_id, db)
                elif action == "progress":
                    await self._show_achievement_progress(query, user_id, db)
                elif action == "recent":
                    await self._show_recent_achievements(query, user_id, db)
                elif action == "stats":
                    await self._show_achievement_stats(query, user_id, db)
                else:
                    await query.edit_message_text("❌ Неизвестное действие")
                    
        except Exception as e:
            logger.error(f"Error in achievement callback: {e}")
            await query.edit_message_text("❌ Ошибка при обработке запроса")

    def _format_achievement_progress(self, ua, achievement):
        """Форматирует прогресс достижения с учетом перевыполнения"""
        if ua.is_completed:
            if ua.current_progress > achievement.condition_value:
                # Перевыполнено
                overachievement = ua.current_progress - achievement.condition_value
                overachievement_percent = (ua.current_progress / achievement.condition_value) * 100
                return f"✅ {achievement.badge_icon} {achievement.name} ({ua.current_progress}/{achievement.condition_value} +{overachievement})"
            else:
                # Выполнено точно
                return f"✅ {achievement.badge_icon} {achievement.name} ({ua.current_progress}/{achievement.condition_value})"
        else:
            # В процессе
            progress_percent = (ua.current_progress / achievement.condition_value) * 100
            return f"⏳ {achievement.badge_icon} {achievement.name} ({ua.current_progress}/{achievement.condition_value})"

    async def _show_all_achievements(self, query, user_id: int, db):
        """Показать все достижения пользователя"""
        user_achievements = user_achievement_crud.get_user_achievements(db, user_id)
        completed_achievements = user_achievement_crud.get_completed_achievements(db, user_id)
        
        message = f"""
🏆 **Все достижения**

📊 **Прогресс:** {len(completed_achievements)}/{len(user_achievements)} завершено

"""
        
        # Группируем достижения по типам
        achievement_types = {}
        for ua in user_achievements:
            achievement = ua.achievement
            if achievement.type.value not in achievement_types:
                achievement_types[achievement.type.value] = []
            achievement_types[achievement.type.value].append(ua)
        
        # Показываем достижения по типам
        for type_name, achievements in achievement_types.items():
            type_emoji = {
                "focus_sessions": "🎯",
                "screen_time_reduction": "📱", 
                "streak_days": "📅",
                "reminders_completed": "⏰",
                "first_time": "👋",
                "milestone": "🏅"
            }.get(type_name, "📋")
            
            # Преобразуем название типа в читаемый формат
            type_display_name = {
                "focus_sessions": "Focus Sessions",
                "screen_time_reduction": "Screen Time Reduction", 
                "streak_days": "Streak Days",
                "reminders_completed": "Reminders Completed",
                "first_time": "First Time",
                "milestone": "Milestone"
            }.get(type_name, type_name.replace('_', ' ').title())
            
            message += f"\n{type_emoji} **{type_display_name}:**\n"
            
            for ua in achievements:  # Показываем все достижения
                achievement = ua.achievement
                formatted_progress = self._format_achievement_progress(ua, achievement)
                message += f"• {formatted_progress}\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🎯 Прогресс", callback_data="achievements_progress"),
                InlineKeyboardButton("🏅 Недавние", callback_data="achievements_recent")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="achievements_main")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message.strip(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def _show_achievement_progress(self, query, user_id: int, db):
        """Показать прогресс по достижениям"""
        user_achievements = user_achievement_crud.get_user_achievements(db, user_id)
        
        message = """
🎯 **Прогресс по достижениям**

"""
        
        # Показываем ближайшие к завершению достижения
        in_progress = [ua for ua in user_achievements if not ua.is_completed]
        in_progress.sort(key=lambda x: x.achievement.condition_value - x.current_progress)
        
        if in_progress:
            message += "**Ближайшие к завершению:**\n\n"
            for ua in in_progress[:5]:
                achievement = ua.achievement
                progress_percent = (ua.current_progress / achievement.condition_value) * 100
                progress_bar_length = 10
                filled_length = int((ua.current_progress / achievement.condition_value) * progress_bar_length)
                progress_bar = "█" * filled_length + "░" * (progress_bar_length - filled_length)
                
                message += f"{achievement.badge_icon} **{achievement.name}**\n"
                message += f"└ {progress_bar} {progress_percent:.1f}% ({ua.current_progress}/{achievement.condition_value})\n\n"
        else:
            message += "🎉 Все достижения завершены! Вы молодец!\n\n"
        
        # Показываем перевыполненные достижения
        overachieved = [ua for ua in user_achievements if ua.is_completed and ua.current_progress > ua.achievement.condition_value]
        if overachieved:
            message += "**🏆 Перевыполненные достижения:**\n\n"
            for ua in overachieved[:3]:
                achievement = ua.achievement
                overachievement = ua.current_progress - achievement.condition_value
                overachievement_percent = (ua.current_progress / achievement.condition_value) * 100
                message += f"✅ {achievement.badge_icon} **{achievement.name}**\n"
                message += f"└ {ua.current_progress}/{achievement.condition_value} (+{overachievement}, {overachievement_percent:.0f}%)\n\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🏆 Все достижения", callback_data="achievements_all"),
                InlineKeyboardButton("📊 Статистика", callback_data="achievements_stats")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="achievements_main")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message.strip(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def _show_recent_achievements(self, query, user_id: int, db):
        """Показать недавние достижения"""
        recent_achievements = user_achievement_crud.get_recent_achievements(db, user_id, days=30)
        
        message = """
🏅 **Недавние достижения**

"""
        
        if recent_achievements:
            for ua in recent_achievements[:10]:
                achievement = ua.achievement
                date_str = ua.completed_at.strftime('%d.%m.%Y')
                message += f"• {achievement.badge_icon} **{achievement.name}** ({date_str})\n"
                message += f"  └ {achievement.description}\n\n"
        else:
            message += "Пока нет недавних достижений. Продолжайте работать! 💪\n\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🏆 Все достижения", callback_data="achievements_all"),
                InlineKeyboardButton("🎯 Прогресс", callback_data="achievements_progress")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="achievements_main")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message.strip(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def _show_achievement_stats(self, query, user_id: int, db):
        """Показать статистику достижений"""
        user_achievements = user_achievement_crud.get_user_achievements(db, user_id)
        completed_achievements = user_achievement_crud.get_completed_achievements(db, user_id)
        user_level = user_level_crud.get_user_level(db, user_id)
        
        # Группируем по типам
        type_stats = {}
        for ua in user_achievements:
            type_name = ua.achievement.type.value
            if type_name not in type_stats:
                type_stats[type_name] = {"total": 0, "completed": 0}
            type_stats[type_name]["total"] += 1
            if ua.is_completed:
                type_stats[type_name]["completed"] += 1
        
        message = f"""
📊 **Статистика достижений**

**Общая статистика:**
• Всего достижений: {len(user_achievements)}
• Завершено: {len(completed_achievements)}
                • Процент завершения: {f"{(len(completed_achievements) / len(user_achievements) * 100):.1f}%" if len(user_achievements) > 0 else "0%"}
• Уровень: {user_level.level if user_level else 1}
• Общий опыт: {user_level.total_experience if user_level else 0} XP

**По категориям:**
"""
        
        type_names = {
            "focus_sessions": "🎯 Сессии фокуса",
            "screen_time_reduction": "📱 Сокращение экранного времени",
            "streak_days": "📅 Серии дней",
            "reminders_completed": "⏰ Выполненные напоминания",
            "first_time": "👋 Первые шаги",
            "milestone": "🏅 Достижения"
        }
        
        for type_name, stats in type_stats.items():
            display_name = type_names.get(type_name, type_name.replace('_', ' ').title())
            completion_rate = (stats["completed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            message += f"• {display_name}: {stats['completed']}/{stats['total']} ({completion_rate:.1f}%)\n"
        
        keyboard = [
            [
                InlineKeyboardButton("🏆 Все достижения", callback_data="achievements_all"),
                InlineKeyboardButton("🎯 Прогресс", callback_data="achievements_progress")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="achievements_main")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message.strip(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def _handle_level_callback(self, query, user_id: int, action: str):
        """Обработка callback запросов для уровня"""
        try:
            from detoxbuddy.database.database import SessionLocal
            
            with SessionLocal() as db:
                if action == "stats":
                    await self._show_level_stats(query, user_id, db)
                elif action == "help":
                    await self._show_level_help(query)
                else:
                    await query.edit_message_text("❌ Неизвестное действие")
                    
        except Exception as e:
            logger.error(f"Error in level callback: {e}")
            await query.edit_message_text("❌ Ошибка при обработке запроса")

    async def _show_level_stats(self, query, user_id: int, db):
        """Показать статистику уровня"""
        user_level = user_level_crud.get_user_level(db, user_id)
        if not user_level:
            user_level = user_level_crud.create_user_level(db, user_id)
        
        # Получаем статистику по достижениям
        completed_achievements = user_achievement_crud.get_completed_achievements(db, user_id)
        
        message = f"""
📈 **Статистика уровня**

**Текущий уровень:**
• Уровень: {user_level.level}
• Опыт: {user_level.experience}/{user_level.experience_to_next_level} XP
• Общий опыт: {user_level.total_experience} XP
• Прогресс: {user_level.progress_to_next_level:.1%}

**Достижения:**
• Завершено: {len(completed_achievements)} достижений
• Серия дней: {user_level.streak_days} дней
• Максимальная серия: {user_level.max_streak_days} дней

**Следующий уровень:**
• Требуется: {user_level.experience_to_next_level} XP
• Осталось: {user_level.experience_to_next_level - user_level.experience} XP
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🏆 Достижения", callback_data="achievements_all"),
                InlineKeyboardButton("🎯 Прогресс", callback_data="achievements_progress")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="level_main")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message.strip(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    async def _show_level_help(self, query):
        """Показать справку по получению опыта"""
        message = """
🎯 **Как получить опыт**

**Основные способы:**

🎯 **Сессии фокуса:**
• Завершение сессии: +10 XP
• Длительная сессия (45+ мин): +15 XP
• Серия сессий: +5 XP за каждую

📱 **Сокращение экранного времени:**
• День с экраном < 6 часов: +20 XP
• День с экраном < 4 часов: +30 XP
• Неделя с экраном < 6 часов: +100 XP

📅 **Серии дней:**
• 7 дней подряд: +50 XP
• 30 дней подряд: +200 XP
• 100 дней подряд: +1000 XP

⏰ **Выполнение напоминаний:**
• Каждое напоминание: +5 XP
• Серия напоминаний: +10 XP

🏆 **Достижения:**
• Каждое достижение: +10-500 XP
• Редкие достижения: +1000 XP

**Советы:**
• Регулярность важнее количества
• Маленькие шаги приводят к большим результатам
• Отслеживайте свой прогресс
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🏆 Достижения", callback_data="achievements_all"),
                InlineKeyboardButton("📊 Статистика", callback_data="level_stats")
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="level_main")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            message.strip(),
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
