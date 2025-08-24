# Система напоминаний DetoxBuddy

## 🔧 Диагностика проблем

Если напоминания не работают, запустите диагностику:

```bash
python scripts/diagnose_reminders.py
```

## 🚀 Быстрый запуск

### Вариант 1: Автоматический запуск всех сервисов

```bash
python scripts/start_services.py
```

### Вариант 2: Ручной запуск компонентов

1. **Запуск Celery beat (планировщик задач):**
   ```bash
   python scripts/run_celery_beat.py
   ```

2. **Запуск Celery worker (обработчик задач):**
   ```bash
   python scripts/run_celery.py
   ```

3. **Запуск Telegram бота:**
   ```bash
   python main.py
   ```

## 📋 Команды бота для работы с напоминаниями

### Создание напоминания
```
/remind <время> <текст>
```

**Примеры:**
- `/remind 15m Сделать перерыв`
- `/remind 1h Позвонить маме`
- `/remind 30m Выпить воды`

### Просмотр напоминаний
```
/reminders
```

### Другие команды
- `/start` - Начало работы с ботом
- `/help` - Справка по командам
- `/test` - Проверка работоспособности

## 🔧 Устранение проблем

### Проблема: "Redis не подключен"
**Решение:** Система автоматически переключается на SQLite. Для лучшей производительности установите Redis:

**Windows:**
1. Скачайте Redis с https://github.com/microsoftarchive/redis/releases
2. Установите и запустите `redis-server`

**macOS:**
```bash
brew install redis
redis-server
```

**Ubuntu:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

### Проблема: "База данных не подключена"
**Решение:** Система автоматически создает SQLite базу в папке `./data/`

### Проблема: "Celery задачи не выполняются"
**Решение:** Убедитесь, что запущены оба процесса:
1. Celery beat (планировщик)
2. Celery worker (обработчик)

## 📊 Мониторинг

### Логи Celery
- `celery.log` - логи worker'а
- `celery_beat.log` - логи планировщика

### Логи бота
- `detoxbuddy.log` - основные логи приложения

### База данных
- `./data/detoxbuddy.db` - основная база данных
- `./data/celery_broker.db` - база для очередей Celery
- `./data/celery_results.db` - база для результатов задач

## 🧪 Тестирование

1. Запустите все сервисы
2. Отправьте боту команду `/start`
3. Создайте тестовое напоминание: `/remind 2m Тестовое напоминание`
4. Подождите 2 минуты - должно прийти уведомление

## 📝 Структура системы напоминаний

```
src/detoxbuddy/
├── tasks/
│   └── reminder_tasks.py          # Задачи Celery для напоминаний
├── database/
│   ├── models/
│   │   └── reminder.py            # Модель напоминания
│   └── crud/
│       └── reminder.py            # CRUD операции
├── telegram/bot/
│   └── telegram_bot.py            # Команды бота
└── core/
    └── celery_app.py              # Конфигурация Celery
```

## 🔄 Жизненный цикл напоминания

1. **Создание** - пользователь отправляет `/remind`
2. **Планирование** - напоминание сохраняется в БД
3. **Проверка** - Celery beat каждую минуту проверяет активные напоминания
4. **Отправка** - Celery worker отправляет уведомление через Telegram
5. **Обновление** - статус напоминания обновляется

## ⚙️ Настройки

Основные настройки в `src/detoxbuddy/core/config.py`:

- `CELERY_BROKER_URL` - URL брокера (Redis/SQLite)
- `CELERY_TIMEZONE` - часовой пояс
- `TELEGRAM_BOT_TOKEN` - токен бота

## 🆘 Поддержка

При возникновении проблем:

1. Запустите диагностику: `python scripts/diagnose_reminders.py`
2. Проверьте логи в файлах `*.log`
3. Убедитесь, что все сервисы запущены
4. Проверьте подключение к базе данных
