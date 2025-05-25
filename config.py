"""
Конфигурация приложения
"""
import os
from typing import List, Optional
from pathlib import Path

# Базовые настройки приложения
APP_NAME = "Rambler API Service"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Асинхронный API сервис для парсинга данных с Rambler"

# Настройки сервера
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
WORKERS = int(os.getenv("WORKERS", "4"))

# Настройки CORS
CORS_ORIGINS: List[str] = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000",
    "http://81.177.6.93",
    "https://81.177.6.93",
    "http://puzzlebot.top",
    "https://puzzlebot.top",
    "https://help.puzzlebot.top",
    "https://www.puzzlebot.top",
    "*",
    ""
]

# Добавление дополнительных CORS origins из переменной окружения
if os.getenv("ADDITIONAL_CORS_ORIGINS"):
    CORS_ORIGINS.extend(os.getenv("ADDITIONAL_CORS_ORIGINS").split(","))

# Настройки кэша
CACHE_TTL_MINUTES = int(os.getenv("CACHE_TTL_MINUTES", "30"))
CACHE_CLEANUP_INTERVAL = int(os.getenv("CACHE_CLEANUP_INTERVAL", "300"))

# Настройки парсера
PARSER_TIMEOUT = int(os.getenv("PARSER_TIMEOUT", "10"))
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "100"))

# Настройки логирования
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_DIR = Path("logs")

# Создаем директорию для логов, если она не существует
LOG_DIR.mkdir(exist_ok=True)

# Настройки для продакшн
PROD_MODE = os.getenv("PROD_MODE", "false").lower() == "true"

# SSL настройки
SSL_CERT_PATH: Optional[str] = os.getenv("SSL_CERT_PATH")
SSL_KEY_PATH: Optional[str] = os.getenv("SSL_KEY_PATH")

# Настройки прокси
PROXY_PREFIX = os.getenv("PROXY_PREFIX", "")

# Функция для получения полного URL API
def get_api_url(path: str = "") -> str:
    """Получение полного URL API с учетом настроек"""
    protocol = "https" if SSL_CERT_PATH and SSL_KEY_PATH else "http"
    base_url = f"{protocol}://{HOST}:{PORT}"
    if PROXY_PREFIX:
        base_url = f"{base_url}/{PROXY_PREFIX.strip('/')}"
    if path:
        return f"{base_url}/{path.lstrip('/')}"
    return base_url