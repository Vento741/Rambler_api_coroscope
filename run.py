#!/usr/bin/env python3
"""
Скрипт запуска сервиса
"""
import sys
import argparse
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

def run_dev_server(host=None, port=None):
    """Запуск сервера разработки"""
    host = host or config.HOST
    port = port or 8080  # Используем 8080 по умолчанию вместо config.PORT
    
    logger.info(f"Starting development server на {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        log_level="debug"
    )

def run_prod_server(host=None, port=None):
    """Запуск продакшн сервера"""
    host = host or config.HOST
    port = port or 8080  # Используем 8080 по умолчанию вместо config.PORT
    
    logger.info(f"Starting production server на {host}:{port}")
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        workers=config.WORKERS,
        log_level="info"
    )

if __name__ == "__main__":
    try:
        # Парсинг аргументов командной строки
        parser = argparse.ArgumentParser(description="Запуск сервера Moon Calendar API")
        parser.add_argument("--prod", action="store_true", help="Запустить в production режиме")
        parser.add_argument("--host", type=str, help="Хост для запуска сервера")
        parser.add_argument("--port", type=int, help="Порт для запуска сервера")
        args = parser.parse_args()
        
        # Запуск сервера
        if args.prod:
            run_prod_server(args.host, args.port)
        else:
            run_dev_server(args.host, args.port)
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        sys.exit(1)