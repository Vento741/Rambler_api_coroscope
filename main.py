"""
Moon Calendar API Service - Main Application
"""
import asyncio
import logging
from contextlib import asynccontextmanager
import time
import os
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
from core.cache import CacheManager
from api.v1 import health, moon_calendar, tarot, numerology
from api.middleware import log_request_middleware

# Создаем директорию для логов, если она не существует
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/app.log")
    ]
)
logger = logging.getLogger(__name__)

# Глобальные объекты
cache_manager = CacheManager(ttl_minutes=config.CACHE_TTL_MINUTES)

# ================= BACKGROUND TASKS =================

async def cleanup_cache_task(cache_manager: CacheManager):
    """Фоновая задача очистки кэша"""
    while True:
        await cache_manager.clear_expired()
        await asyncio.sleep(config.CACHE_CLEANUP_INTERVAL)

# ================= APPLICATION =================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Старт Moon Calendar API Service...")
    
    # Запускаем фоновую задачу очистки кэша
    cleanup_task = asyncio.create_task(cleanup_cache_task(cache_manager))
    
    yield
    
    # Shutdown
    logger.info("Выключение Moon Calendar API Service...")
    cleanup_task.cancel()
    try:
        await cleanup_task
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
    allow_methods=["*"],
    allow_headers=["*"],
)

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
            content={"detail": "Internal server error"}
        )

# ================= ROUTES =================

# Регистрируем роутеры
app.include_router(health.router)
app.include_router(moon_calendar.router)
app.include_router(tarot.router)
app.include_router(numerology.router)

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
