# Moon Calendar API Service

Асинхронное FastAPI сервис для парсинга лунного календаря с Rambler с кэшированием и поддержкой конкурентных запросов.

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Запуск сервиса

**Режим разработки:**
```bash
python run.py
```

**Продакшн режим:**
```bash
python run.py prod
```

**Прямой запуск:**
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Тестирование

```bash
python test_client.py
```

## 📋 API Endpoints

### Базовые эндпоинты

- **GET /** - Информация о сервисе
- **GET /health** - Проверка здоровья сервиса

### Основные эндпоинты

- **GET /api/v1/moon-calendar/current** - Лунный календарь на сегодня
- **GET /api/v1/moon-calendar/{date}** - Лунный календарь на конкретную дату (YYYY-MM-DD)

## 📖 Примеры использования

### Получение данных на сегодня

```bash
curl http://127.0.0.1:8000/api/v1/moon-calendar/2025-05-24
```

### Пример ответа

```json
{
  "success": true,
  "data": {
    "date": "2025-05-24",
    "moon_phase": "Растущая Луна",
    "moon_days": [
      {
        "name": "26 лунный день",
        "start": "2025-05-24T02:49:00+03:00",
        "end": "2025-05-24T16:16:00+03:00",
        "info": "День пассивности и созерцания. Рекомендуется избегать активных действий."
      }
    ],
    "recommendations": {
      "Общие советы": "Посвятите время отдыху и размышлениям",
      "Предостережения": "Будьте осторожны в общении и избегайте конфликтов"
    }
  },
  "cached": false
}
```

## 🏗️ Архитектура

### Компоненты системы

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PuzzleBot     │───▶│   FastAPI       │───▶│   Rambler       │
│   Platform      │    │   Service       │    │   Website       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │   Cache Layer    │
                       │   (In-Memory)    │
                       └──────────────────┘
```

### Основные модули

- **`main.py`** - FastAPI приложение и эндпоинты
- **`config.py`** - Конфигурация сервиса
- **`run.py`** - Скрипт запуска
- **`test_client.py`** - Тестовый клиент

### Ключевые возможности

- ⚡ **Асинхронная обработка** - поддержка множественных конкурентных запросов
- 🗄️ **Интеллектуальное кэширование** - TTL кэш с автоочисткой
- 🔄 **Автоматическая очистка** - фоновые задачи для управления памятью
- 📊 **Мониторинг** - логирование и метрики производительности
- 🛡️ **Обработка ошибок** - graceful handling сетевых и парсинг ошибок

## ⚙️ Конфигурация

### Переменные окружения

```bash
# Сервер
HOST=127.0.0.1
PORT=8000
DEBUG=false

# Кэш
CACHE_TTL_MINUTES=30
CACHE_CLEANUP_INTERVAL=300

# Парсер
PARSER_TIMEOUT=10
MAX_CONCURRENT_REQUESTS=100

# Логирование
LOG_LEVEL=INFO
```

### Настройка для продакшна

1. Установите переменные окружения
2. Настройте CORS origins в `config.py`
3. Используйте reverse proxy (nginx)
4. Настройте мониторинг и логирование

## 🔗 Интеграция с PuzzleBot

### Настройка HTTP запроса в PuzzleBot

```json
{
  "method": "GET",
  "url": "http://YOUR_SERVER:8000/api/v1/moon-calendar/current",
  "headers": {
    "Content-Type": "application/json"
  }
}
```

### Обработка ответа

После получения JSON от API, используйте следующую структуру для передачи в нейросеть:

```json
{
  "model": "google/gemini-2.0-flash-001",
  "messages": [
    {
      "role": "system",
      "content": "Ты — эксперт по лунному календарю. На основе предоставленных данных создай краткую сводку в формате:\n\n1. 🌑 Фаза: {moon_phase}\n2. ⏱ Время: {moon_days_summary}\n3. 💫 Характеристики: {characteristics}\n4. ⚠ Советы: {recommendations}\n\nИспользуй только предоставленные данные. Максимум 2 предложения на пункт."
    },
    {
      "role": "user",
      "content": "Обработай эти данные лунного календаря: {{JSON_FROM_API}}"
    }
  ],
  "max_tokens": 200,
  "temperature": 0.3
}
```

## 🧪 Тестирование

### Автоматические тесты

```bash
python test_client.py
```

Тесты проверяют:
- ✅ Health check
- ✅ Получение текущего календаря
- ✅ Получение календаря на дату
- ✅ Производительность кэша
- ✅ Конкурентные запросы

### Ручное тестирование

```bash
# Проверка здоровья
curl http://127.0.0.1:8000/health

# Получение данных
curl http://127.0.0.1:8000/api/v1/moon-calendar/current

# Тест с конкретной датой
curl http://127.0.0.1:8000/api/v1/moon-calendar/2025-05-24
```

## 🚀 Развертывание

### Локальное развертывание

```bash
# Клонируйте проект
git clone <repository>
cd moon-calendar-api

# Установите зависимости
pip install -r requirements.txt

# Запустите сервис
python run.py
```

### Развертывание на VPS (Джино)

1. **Подключение к серверу**

```bash
ssh username@your_jino_server_ip
```

2. **Установка необходимых пакетов**

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx supervisor git
```

3. **Клонирование репозитория**

```bash
mkdir -p /home/username/apps
cd /home/username/apps
git clone https://github.com/your-username/Rambler_api.git
cd Rambler_api
```

4. **Настройка виртуального окружения**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r req.txt
pip install gunicorn
```

5. **Создание файла конфигурации**

Создайте файл `.env` на основе `.env.example`:

```bash
cp .env.example .env
nano .env
```

6. **Настройка Supervisor**

```bash
sudo nano /etc/supervisor/conf.d/rambler_api.conf
```

Содержимое файла:

```ini
[program:rambler_api]
directory=/home/username/apps/Rambler_api
command=/home/username/apps/Rambler_api/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
user=username
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/rambler_api/err.log
stdout_logfile=/var/log/rambler_api/out.log
```

7. **Настройка Nginx**

```bash
sudo nano /etc/nginx/sites-available/rambler_api
```

Содержимое файла:

```nginx
server {
    listen 80;
    server_name your_domain.com www.your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

8. **Активация конфигурации Nginx**

```bash
sudo ln -s /etc/nginx/sites-available/rambler_api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

9. **Запуск сервиса**

```bash
sudo mkdir -p /var/log/rambler_api
sudo chown -R username:username /var/log/rambler_api
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start rambler_api
```

10. **Настройка SSL с Let's Encrypt (опционально)**

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com -d www.your_domain.com
```

### Использование с systemd

Создайте файл `/etc/systemd/system/moon-calendar.service`:

```ini
[Unit]
Description=Moon Calendar API Service
After=network.target

[Service]
Type=exec
User=your_user
WorkingDirectory=/path/to/moon-calendar-api
Environment=PATH=/path/to/moon-calendar-api/venv/bin
ExecStart=/path/to/moon-calendar-api/venv/bin/python run.py prod
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Активация сервиса
sudo systemctl daemon-reload
sudo systemctl enable moon-calendar
sudo systemctl start moon-calendar
```

## 📈 Масштабирование

### Для больших нагрузок

1. **Увеличьте количество воркеров**:
   ```python
   uvicorn.run("main:app", workers=8)
   ```

2. **Используйте Redis для кэша**:
   - Замените in-memory кэш на Redis
   - Добавьте поддержку кластера Redis

3. **Настройте балансировщик нагрузки**:
   - nginx upstream
   - HAProxy
   - Cloudflare Load Balancer

4. **Добавьте мониторинг**:
   - Prometheus + Grafana
   - DataDog
   - New Relic

### Будущие модули

Структура подготовлена для добавления новых парсеров:

```python
# Добавление нового модуля
@app.get("/api/v1/runes/{date}")
async def get_runes_reading(date: str):
    # Логика парсинга рун
    pass

@app.get("/api/v1/tarot/{date}")
async def get_tarot_reading(date: str):
    # Логика парсинга таро
    pass
```

## 🤝 Поддержка

Для вопросов и предложений создайте issue в репозитории или свяжитесь с разработчиком.

## 📝 Лицензия

MIT License - используйте свободно для личных и коммерческих проектов.

# Система кэширования в сервисе криптовалютных прогнозов

## Обзор системы кэширования

Сервис криптовалютных прогнозов использует Redis в качестве основного механизма кэширования для оптимизации производительности и снижения нагрузки на внешние API. Кэширование реализовано через класс `CacheManager` в `core/cache.py`.

## Основные компоненты системы кэширования

### 1. CacheManager (core/cache.py)

Класс `CacheManager` предоставляет асинхронный интерфейс для работы с Redis:

- **Инициализация**: Создает подключение к Redis с настраиваемым TTL (время жизни кэша)
- **Методы кэширования**: 
  - `get()` - получение данных из кэша
  - `set()` - сохранение данных в кэш с установленным TTL
  - `connect()` - установка соединения с Redis
  - `close()` - закрытие соединения

### 2. Кэширование прогнозов в CryptoForecastService

В классе `CryptoForecastService` (modules/crypto_forecast/forecast_service.py) реализована логика кэширования прогнозов:

- **Генерация ключей**: Метод `_generate_cache_key()` создает уникальные ключи для каждой комбинации криптовалюты и периода прогноза
- **TTL по периодам**: 
  - Часовой прогноз: 1 час (3600 секунд)
  - Дневной прогноз: 24 часа (86400 секунд)
  - Недельный прогноз: 3 дня (259200 секунд)

### 3. Фоновое обновление кэша

Класс `CryptoForecastTasks` (modules/crypto_forecast/tasks.py) отвечает за фоновое обновление кэша:

- **Периодическое обновление**: Метод `run_periodic_update()` запускает обновление прогнозов с заданным интервалом
- **Обновление популярных криптовалют**: Метод `update_popular_cryptos_forecasts()` обновляет прогнозы для популярных криптовалют

## Конфигурация кэширования

Настройки кэширования определены в файле `config.py`:

```python
# Настройки кэша
CACHE_TTL_MINUTES = int(os.getenv("CACHE_TTL_MINUTES", "180"))
CACHE_CLEANUP_INTERVAL = int(os.getenv("CACHE_CLEANUP_INTERVAL", "600"))

# Redis settings
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
```

Эти настройки можно изменить через переменные окружения в файле `.env`.

## API эндпоинты и кэширование

В файле `api/v1/crypto_forecast.py` реализованы эндпоинты, которые используют кэширование:

- **GET /api/v1/crypto/forecast/{symbol}**: Получение прогноза для указанной криптовалюты
  - Параметр `force_refresh=True` позволяет принудительно обновить кэш

## Структура кэшированных данных

Данные в кэше хранятся в формате JSON и содержат:

- **symbol**: Символ криптовалюты
- **period**: Период прогноза
- **current_price**: Текущая цена
- **forecast**: Текст прогноза
- **generated_at**: Время генерации прогноза
- **expires_at**: Время истечения прогноза

## Обработка ошибок кэширования

Система кэширования включает обработку различных ошибок:

- **Ошибки соединения**: Автоматические попытки переподключения к Redis
- **Ошибки десериализации**: Обработка и удаление поврежденных данных из кэша
- **Недоступность Redis**: Корректная обработка случаев, когда Redis недоступен

## Рекомендации по оптимизации кэширования

1. **Мониторинг использования памяти Redis**: Регулярно проверяйте использование памяти Redis
2. **Настройка TTL**: Оптимизируйте TTL в зависимости от частоты обновления данных
3. **Фоновые задачи**: Настройте интервал фоновых задач для предварительного заполнения кэша
4. **Масштабирование**: При необходимости рассмотрите возможность использования Redis Cluster

## Пример использования кэширования в коде

```python
# Получение прогноза с использованием кэша
async def get_forecast(symbol, period):
    cache_key = f"crypto_forecast_{symbol.lower()}_{period}"
    
    # Попытка получить данные из кэша
    cached_data = await cache_manager.redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    # Если данных в кэше нет, генерируем новый прогноз
    forecast_data = await generate_new_forecast(symbol, period)
    
    # Сохраняем в кэш с соответствующим TTL
    ttl = 3600  # 1 час по умолчанию
    if period == "day":
        ttl = 86400  # 24 часа
    elif period == "week":
        ttl = 259200  # 3 дня
    
    await cache_manager.redis.set(cache_key, json.dumps(forecast_data), ex=ttl)
    
    return forecast_data
```
