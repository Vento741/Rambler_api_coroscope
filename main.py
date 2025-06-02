"""
Moon Calendar API Service - Main Application
"""
import asyncio
import logging
from contextlib import asynccontextmanager
import time
import os
from pathlib import Path
import sys

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
from core.cache import CacheManager
from api.v1 import health, moon_calendar, tarot, astro_bot, book_czin
from api.middleware import log_request_middleware
from modules.moon_calendar import MoonCalendarParser, MoonCalendarOpenRouterService, MoonCalendarTasks
from modules.moon_calendar.tasks import MoonCalendarTasks
from api.v1.tarot_puzzlebot import router as tarot_puzzlebot_router
from core.openrouter_client import OpenRouterClient
from modules.book_czin import BookCzinService

# Создаем директорию для логов, если она не существует
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"{config.LOG_DIR}/app.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ================= BACKGROUND TASKS =================

async def update_moon_calendar_cache_task(tasks: MoonCalendarTasks):
    """Фоновая задача обновления кэша лунного календаря и генерации AI-ответов"""
    try:
        # Сначала обновляем кэш и генерируем ответы сразу при запуске
        logger.info("Запуск начального обновления кэша и генерации AI-ответов...")
        try:
            await tasks.update_calendar_cache_and_generate_ai_responses()
            logger.info("Начальное обновление кэша и генерация AI-ответов выполнены успешно.")
        except Exception as e:
            logger.error(f"Ошибка при начальном обновлении кэша: {e}", exc_info=True)
            logger.info("Несмотря на ошибку, продолжаем запуск периодического обновления.")
        
        # Проверяем настройки интервала обновления и TTL кэша
        update_interval = config.BACKGROUND_TASKS["update_cache_interval_minutes"]
        cache_ttl = config.CACHE_TTL_MINUTES
        
        if cache_ttl <= update_interval:
            logger.warning(f"ВНИМАНИЕ: TTL кэша ({cache_ttl} мин) меньше или равен интервалу обновления ({update_interval} мин)! "
                          f"Это может привести к истечению срока действия кэша до следующего обновления. "
                          f"Рекомендуется установить TTL кэша как минимум в 2-3 раза больше интервала обновления.")
        else:
            logger.info(f"Настройки кэша: TTL = {cache_ttl} мин, интервал обновления = {update_interval} мин. "
                       f"TTL кэша в {cache_ttl/update_interval:.1f} раз больше интервала обновления, что хорошо.")
        
        # Затем запускаем периодическое обновление
        logger.info(f"Запуск периодического обновления кэша каждые {update_interval} минут...")
        await tasks.run_periodic_update(update_interval)
    except Exception as e:
        logger.critical(f"Критическая ошибка в фоновой задаче обновления кэша: {e}", exc_info=True)
        # Даже при критической ошибке не завершаем процесс, чтобы API продолжало работать

# ================= APPLICATION =================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Старт Moon Calendar API Service...")
    
    # Инициализация зависимостей внутри lifespan
    cache_manager = CacheManager(ttl_minutes=config.CACHE_TTL_MINUTES)
    
    # Пробуем подключиться к Redis с несколькими попытками
    max_redis_connect_attempts = 3
    redis_connected = False
    
    for attempt in range(1, max_redis_connect_attempts + 1):
        logger.info(f"Попытка подключения к Redis {attempt}/{max_redis_connect_attempts}...")
        await cache_manager.connect()
        if cache_manager.redis:
            redis_connected = True
            logger.info(f"Успешное подключение к Redis с попытки {attempt}")
            break
        else:
            logger.warning(f"Не удалось подключиться к Redis с попытки {attempt}. {'Пробуем еще раз...' if attempt < max_redis_connect_attempts else 'Исчерпаны все попытки.'}")
            if attempt < max_redis_connect_attempts:
                await asyncio.sleep(1)  # Небольшая пауза перед следующей попыткой
    
    if not redis_connected:
        logger.critical(f"Не удалось подключиться к Redis после {max_redis_connect_attempts} попыток! Приложение может работать некорректно.")
    
    parser = MoonCalendarParser(timeout=config.PARSER_TIMEOUT)
    
    # Инициализация OpenRouter клиента для лунного календаря
    openrouter_client_for_moon_tasks = OpenRouterClient(
        api_url=config.OPENROUTER_API_URL,
        api_keys=config.OPENROUTER_API_KEYS,
        models=config.OPENROUTER_MODELS,
        model_configs=config.OPENROUTER_MODEL_CONFIGS,
        model_api_keys=config.OPENROUTER_MODEL_API_KEYS,
        timeout=60  # Таймаут для запросов от фоновой задачи
    )
    
    # Инициализация сервиса OpenRouter для лунного календаря
    moon_openrouter_service = MoonCalendarOpenRouterService(
        cache_manager=cache_manager, # Передаем экземпляр cache_manager
        parser=parser,
        openrouter_client=openrouter_client_for_moon_tasks,
        prompts_config=config.OPENROUTER_PROMPTS
    )
    
    moon_calendar_tasks = MoonCalendarTasks(
        cache_manager=cache_manager, # Передаем экземпляр cache_manager
        parser=parser,
        openrouter_service=moon_openrouter_service # Передаем экземпляр сервиса
    )
    
    # Инициализация сервиса для Книги Перемен
    book_czin_service = BookCzinService(
        base_url=config.BASE_URL
    )
    
    # Запускаем фоновую задачу обновления кэша лунного календаря
    update_calendar_task = asyncio.create_task(update_moon_calendar_cache_task(moon_calendar_tasks))
    
    # Добавляем cache_manager в state приложения для доступа из роутеров/зависимостей
    # Это более надежный способ, чем передавать его через конструкторы роутеров, которые создает FastAPI
    app.state.cache_manager = cache_manager
    # Добавляем другие зависимости в state, если они могут понадобиться в других частях приложения
    app.state.parser = parser
    app.state.openrouter_client_for_moon_tasks = openrouter_client_for_moon_tasks
    app.state.moon_openrouter_service = moon_openrouter_service
    app.state.moon_calendar_tasks = moon_calendar_tasks
    app.state.book_czin_service = book_czin_service
    
    yield
    
    # Shutdown
    logger.info("Выключение Moon Calendar API Service...")
    update_calendar_task.cancel()
    
    try:
        if not update_calendar_task.done():
             await update_calendar_task
    except asyncio.CancelledError:
        pass
    except Exception as e:
         logger.error(f"Ошибка при отмене задач: {e}", exc_info=True)

    # Закрываем соединение с Redis
    await cache_manager.close()
    logger.info("Redis connection closed.")

# Создание FastAPI приложения
app = FastAPI(
    title="Moon Calendar API",
    description="Асинхронное API для получения данных лунного календаря",
    version=config.APP_VERSION,
    docs_url="/docs" if config.DEBUG else None,
    redoc_url="/redoc" if config.DEBUG else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,  # 24 часа
)

# Обработчик OPTIONS запросов для CORS preflight
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return {"detail": "OK"}

# Middleware для логирования запросов
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware для логирования запросов и времени выполнения"""
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Логируем запрос
        logger.info(
            f"Request: {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s"
        )
        
        # Добавляем заголовок с временем обработки
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        logger.error(f"Request error: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Внутренняя ошибка сервера"}
        )

# ================= ROUTES =================

# Регистрируем роутеры
app.include_router(health.router)
app.include_router(moon_calendar.router, tags=["moon_calendar"])
app.include_router(tarot.router, tags=["tarot"])
app.include_router(astro_bot.router, tags=["astro_bot"])
app.include_router(tarot_puzzlebot_router)
app.include_router(book_czin.router)

# ================= ENTRY POINT =================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG,
        log_level=config.LOG_LEVEL.lower()
    )
