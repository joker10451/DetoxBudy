# DetoxBuddy - Цифровой Детокс-ассистент

Telegram бот для осознанного управления цифровым потреблением и улучшения цифровой гигиены.

## 🎯 Описание

DetoxBuddy помогает пользователям осознанно подходить к потреблению информации и использованию гаджетов. Бот не блокирует доступ, а выступает в роли тренера по цифровой гигиене.

## ✨ Основные функции

- **Персональный план детокса** - настройка целей и отслеживание прогресса
- **Таймер фокуса** - интеграция с техникой Pomodoro
- **"Тихие часы"** - настраиваемые напоминания о времени сна
- **Полезный контент** - ежедневные отобранные статьи
- **Аналитика экранного времени** - анализ паттернов использования

## 🏗️ Архитектура

- **Frontend**: Telegram Bot (python-telegram-bot)
- **Backend**: FastAPI
- **База данных**: PostgreSQL
- **Кэш**: Redis
- **Очереди**: Celery
- **Контейнеризация**: Docker

## 🚀 Быстрый старт

### Предварительные требования

- Python 3.11+
- Telegram Bot Token (получить у @BotFather)
- Redis (опционально, для лучшей производительности)

### Установка и запуск

1. **Клонируйте репозиторий**
   ```bash
   git clone <repository-url>
   cd detoxbuddy
   ```

2. **Создайте виртуальное окружение**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # или
   venv\Scripts\activate  # Windows
   ```

3. **Установите зависимости**
   ```bash
   pip install -r requirements.txt
   ```

4. **Настройте переменные окружения**
   ```bash
   cp configs/env.example .env
   # Отредактируйте .env и добавьте ваш TELEGRAM_BOT_TOKEN
   ```

5. **Запустите систему напоминаний**
   ```bash
   # Автоматический запуск всех сервисов
   python scripts/start_services.py
   
   # Или ручной запуск:
   # python scripts/run_celery_beat.py  # В отдельном терминале
   # python scripts/run_celery.py       # В отдельном терминале
   # python main.py                     # В отдельном терминале
   ```

### Диагностика проблем

Если напоминания не работают:

```bash
python scripts/diagnose_reminders.py
```

Подробная документация по системе напоминаний: [README_REMINDERS.md](README_REMINDERS.md)

## 📁 Структура проекта

```
detoxbuddy/
├── app/
│   ├── __init__.py
│   ├── main.py              # Точка входа FastAPI
│   ├── bot/                 # Telegram бот
│   ├── api/                 # API endpoints
│   ├── models/              # Модели данных
│   ├── services/            # Бизнес-логика
│   ├── utils/               # Утилиты
│   └── config.py            # Конфигурация
├── docs/                    # Документация
├── tests/                   # Тесты
├── alembic/                 # Миграции БД
├── requirements.txt         # Зависимости Python
├── Dockerfile              # Docker образ
├── docker-compose.yml      # Docker Compose
└── README.md               # Документация
```

## 🔧 Конфигурация

Основные переменные окружения:

- `TELEGRAM_BOT_TOKEN` - токен Telegram бота
- `DATABASE_URL` - URL базы данных PostgreSQL
- `REDIS_URL` - URL Redis сервера
- `ENVIRONMENT` - окружение (development/production)

## 🧪 Тестирование

```bash
# Запуск всех тестов
pytest

# Запуск тестов с покрытием
pytest --cov=app

# Запуск тестов в Docker
docker-compose exec app pytest
```

## 📊 Мониторинг

- **API документация**: http://localhost:8000/docs
- **Health check**: http://localhost:8000/health
- **Метрики**: http://localhost:8000/metrics

## 🤝 Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции
3. Внесите изменения
4. Добавьте тесты
5. Создайте Pull Request

## 📄 Лицензия

MIT License

## 📞 Поддержка

- Создайте Issue в GitHub
- Напишите в Telegram: @detoxbuddy_support

---

**Версия**: 1.0.0  
**Дата**: 2024-08-24
