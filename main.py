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
from api.v1 import health, moon_calendar, tarot, numerology, astro_bot
from api.middleware import log_request_middleware
from modules.moon_calendar import MoonCalendarParser, MoonCalendarOpenRouterService
from modules.moon_calendar.tasks import MoonCalendarTasks
from api.v1.tarot_puzzlebot import router as tarot_puzzlebot_router
from core.openrouter_client import OpenRouterClient

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

# Глобальные объекты
cache_manager = CacheManager(ttl_minutes=config.CACHE_TTL_MINUTES)
parser = MoonCalendarParser(timeout=config.PARSER_TIMEOUT)

# Инициализация OpenRouter клиента для лунного календаря
# (Эта конфигурация аналогична той, что используется в astro_bot.py)
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
    cache_manager=cache_manager,
    parser=parser,
    openrouter_client=openrouter_client_for_moon_tasks,
    prompts_config=config.OPENROUTER_PROMPTS
)

moon_calendar_tasks = MoonCalendarTasks(cache_manager, parser, moon_openrouter_service)

# ================= BACKGROUND TASKS =================

async def cleanup_cache_task(cache_manager: CacheManager):
    """Фоновая задача очистки кэша"""
    while True:
        await cache_manager.clear_expired()
        await asyncio.sleep(config.CACHE_CLEANUP_INTERVAL)

async def update_moon_calendar_cache_task(tasks: MoonCalendarTasks):
    """Фоновая задача обновления кэша лунного календаря и генерации AI-ответов"""
    # Сначала обновляем кэш и генерируем ответы сразу при запуске
    await tasks.update_calendar_cache_and_generate_ai_responses()
    
    # Затем запускаем периодическое обновление
    await tasks.run_periodic_update(config.BACKGROUND_TASKS["update_cache_interval_minutes"])

# ================= APPLICATION =================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Старт Moon Calendar API Service...")
    
    # Запускаем фоновую задачу очистки кэша
    cleanup_task = asyncio.create_task(cleanup_cache_task(cache_manager))
    
    # Запускаем фоновую задачу обновления кэша лунного календаря
    update_calendar_task = asyncio.create_task(update_moon_calendar_cache_task(moon_calendar_tasks))
    
    yield
    
    # Shutdown
    logger.info("Выключение Moon Calendar API Service...")
    cleanup_task.cancel()
    update_calendar_task.cancel()
    
    try:
        await cleanup_task
        await update_calendar_task
    except asyncio.CancelledError:
        pass

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
app.include_router(numerology.router)
app.include_router(astro_bot.router, tags=["astro_bot"])
app.include_router(tarot_puzzlebot_router)

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
