moon-calendar-api/
├── README.md                 # Документация проекта
├── requirements.txt          # Зависимости Python
├── config.py                # Конфигурация приложения
├── main.py                  # Основное FastAPI приложение
├── run.py                   # Скрипт запуска сервиса
├── test_client.py           # Тестовый клиент
│
├── modules/                 # Модули парсеров (для будущего развития)
│   ├── __init__.py
│   ├── moon_calendar/       # Текущий модуль лунного календаря
│   │   ├── __init__.py
│   │   ├── parser.py        # Логика парсинга
│   │   └── models.py        # Модели данных
│   ├── runes/              # Будущий модуль рун
│   ├── tarot/              # Будущий модуль таро
│   └── natal_chart/        # Будущий модуль натальных карт
│
├── core/                   # Ядро системы
│   ├── __init__.py
│   ├── cache.py           # Менеджер кэша
│   ├── exceptions.py      # Кастомные исключения
│   └── utils.py           # Утилиты
│
├── api/                   # API эндпоинты
│   ├── __init__.py
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── moon_calendar.py  # Эндпоинты лунного календаря
│   │   └── health.py         # Health check эндпоинты
│   └── middleware.py      # Middleware для API
│
├── tests/                 # Тесты
│   ├── __init__.py
│   ├── test_parser.py     # Тесты парсера
│   ├── test_cache.py      # Тесты кэша
│   └── test_api.py        # Тесты API
│
├── logs/                  # Логи (создается автоматически)
├── .env.example          # Пример переменных окружения
├── .gitignore            # Git ignore файл
└── docker/               # Docker конфигурация (опционально)
    ├── Dockerfile
    └── docker-compose.yml

ИНСТРУКЦИИ ПО РАЗВЕРТЫВАНИЮ:

1. ЛОКАЛЬНАЯ РАЗРАБОТКА:
   ```bash
   git clone <repository>
   cd moon-calendar-api
   pip install -r requirements.txt
   python run.py
   ```

2. ПРОДАКШН РАЗВЕРТЫВАНИЕ:
   ```bash
   # На VPS сервере
   git clone <repository>
   cd moon-calendar-api
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Настройка переменных окружения
   export HOST=0.0.0.0
   export PORT=8000
   export DEBUG=false
   
   # Запуск
   python run.py prod
   ```

3. ИНТЕГРАЦИЯ С PUZZLEBOT:
   
   a) Создайте HTTP запрос в PuzzleBot:
      URL: http://YOUR_SERVER_IP:8000/api/v1/moon-calendar/current
      Method: GET
      
   b) Сохраните ответ в переменную (например, moon_data)
   
   c) Используйте эту переменную в запросе к нейросети:
      {
        "model": "google/gemini-2.0-flash-001",
        "messages": [
          {
            "role": "system", 
            "content": "Обработай данные лунного календаря и создай краткую сводку в формате:
            1. 🌑 Фаза: {фаза луны}
            2. ⏱ Время: {время лунных дней}  
            3. 💫 Характеристики: {характеристики}
            4. ⚠ Советы: {рекомендации}"
          },
          {
            "role": "user",
            "content": "Данные: {{moon_data}}"
          }
        ]
      }

4. ТЕСТИРОВАНИЕ:
   ```bash
   python test_client.py
   ```

ПРЕИМУЩЕСТВА АРХИТЕКТУРЫ:

✅ Асинхронность - обработка множественных запросов
✅ Кэширование - быстрые повторные запросы  
✅ Масштабируемость - легко добавлять новые модули
✅ Мониторинг - логирование и метрики
✅ Производительность - оптимизированный парсинг
✅ Надежность - обработка ошибок и failover
✅ Простота интеграции - RESTful API
✅ Готовность к продакшну - конфигурация и развертывание

СЛЕДУЮЩИЕ ШАГИ:

1. Запустите сервис локально
2. Протестируйте через test_client.py
3. Интегрируйте с PuzzleBot
4. Разверните на VPS
5. Добавьте мониторинг
6. Масштабируйте при необходимости



Эта структура позволяет легко добавлять новые модули в будущем. Для добавления нового модуля (например, нумерологии) нужно:
Создать директорию modules/numerology/ с файлами:
__init__.py
models.py
parser.py
service.py
Создать API эндпоинты в api/v1/numerology.py
Подключить роутер в main.py
Такая модульная структура обеспечивает:
Четкое разделение ответственности
Легкость масштабирования
Переиспользование общих компонентов (кэш, утилиты и т.д.)
Простоту поддержки и расширения