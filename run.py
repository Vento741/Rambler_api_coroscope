#!/usr/bin/env python3
"""
Скрипт запуска сервиса
"""
import sys
import uvicorn
import logging
from main import app
import config

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

def run_dev_server():
    """Запуск сервера разработки"""
    logger.info("Starting development server")
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level="debug"
    )

def run_prod_server():
    """Запуск продакшн сервера"""
    logger.info("Starting production server")
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        workers=config.WORKERS,
        log_level="info"
    )

if __name__ == "__main__":
    try:
        # Проверяем аргументы командной строки
        if len(sys.argv) > 1 and sys.argv[1] == "prod":
            run_prod_server()
        else:
            run_dev_server()
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)