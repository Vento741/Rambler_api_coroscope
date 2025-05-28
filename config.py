"""
Конфигурационный файл приложения
"""
from dotenv import load_dotenv
import os
from typing import List, Optional, Dict
from pathlib import Path

# Загрузка переменных окружения из .env файла
load_dotenv()

# Базовые настройки приложения
APP_NAME = "Rambler API Service"
APP_VERSION = "1.0.0"
APP_DESCRIPTION = "Асинхронный API сервис для парсинга данных с Rambler"

# Настройки сервера
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8081"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
WORKERS = int(os.getenv("WORKERS", "4"))

# Настройки CORS
CORS_ORIGINS: List[str] = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:8081",
    "http://127.0.0.1",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:8081",
    "http://81.177.6.93",
    "http://81.177.6.93:8080",
    "http://81.177.6.93:8081",
    "https://81.177.6.93",
    "https://81.177.6.93:8080",
    "https://81.177.6.93:8081",
    "http://puzzlebot.top",
    "https://puzzlebot.top",
    "https://help.puzzlebot.top",
    "https://www.puzzlebot.top",
    "https://app.puzzlebot.top",
    "http://app.puzzlebot.top",
    "https://bot.puzzlebot.top",
    "http://bot.puzzlebot.top",
    "*"
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

# Настройки OpenRouter API
OPENROUTER_API_URL = os.getenv("URL_LINK_OPENROUTER", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_API_KEYS = [
    key for key in [
        os.getenv("Qwen2.5_VL_72B_Instruct_free", ""),
        os.getenv("API_for_Gemini_2.0_Flash", ""),
        os.getenv("API_for_Gemini_2.0_Flash_Exp_free", ""),
        os.getenv("DeepSeek_Prover_V2_free", "")
    ] if key
]

# Модели OpenRouter
OPENROUTER_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "qwen/qwen2.5-vl-72b-instruct:free",
    "google/gemini-2.0-flash-001",
    "deepseek/deepseek-prover-v2:free"
]

# Сопоставление моделей и их API ключей
OPENROUTER_MODEL_API_KEYS = {
    "google/gemini-2.0-flash-001": os.getenv("API_for_Gemini_2.0_Flash", ""),
    "google/gemini-2.0-flash-exp:free": os.getenv("API_for_Gemini_2.0_Flash_Exp_free", ""),
    "qwen/qwen2.5-vl-72b-instruct:free": os.getenv("Qwen2.5_VL_72B_Instruct_free", ""),
    "deepseek/deepseek-prover-v2:free": os.getenv("DeepSeek_Prover_V2_free", "")
}

# Конфигурация специфичных запросов для моделей
OPENROUTER_MODEL_CONFIGS = {
    "google/gemini-2.0-flash-001": {
        "request_type": "openai",
        "timeout": 60
    },
    "google/gemini-2.0-flash-exp:free": {
        "request_type": "openai",
        "timeout": 60
    },
    "deepseek/deepseek-prover-v2:free": {
        "request_type": "standard",
        "timeout": 60
    },
    "qwen/qwen2.5-vl-72b-instruct:free": {
        "request_type": "openai",
        "timeout": 60
    }
}

# Настройки промптов для разных типов пользователей
OPENROUTER_PROMPTS = {
    "free": {
        "system_message": "Ты — мистический эксперт по лунному календарю. Твоя задача — преобразовать сухие факты в увлекательное, интригующее повествование, раскрывающее тайны лунного дня. ВАЖНО: Начинай сразу с сути, без приветствий и вводных фраз. Никогда не используй фразы типа 'Хорошо', 'Понял вас', 'Приступаю' и т.п. ФОРМАТИРОВАНИЕ: Используй ЗАГЛАВНЫЕ БУКВЫ для выделения важных фраз и заголовков. Используй эмодзи для визуального разделения разделов (🌙 для лунных дней, ✨ для энергетики, 🔮 для советов). Для разделения текста используй символьные разделители '---', '***', '==='. Формат ответа (строго придерживайся): '🌓 ДАТА И ФАЗА ЛУНЫ 🌓' (с мистическим описанием энергетики), '🌙 ЛУННЫЙ ДЕНЬ 🌙' (с интригующим описанием его влияния), '🔮 ГЛАВНЫЙ СОВЕТ ДНЯ 🔮' (сформулированный как ключ к успеху). Используй яркие метафоры, образные выражения и таинственные намёки. Сделай текст кратким, но захватывающим.",
        "max_tokens": 350,
        "temperature": 0.7
    },
    "premium": {
        "system_message": "Ты — глубокий знаток тайн лунного календаря, посвящённый в древние мистические традиции. Твоя задача — создать детальное, завораживающее повествование о лунном дне, раскрывая его скрытый потенциал и влияние на все сферы жизни. ВАЖНО: Начинай сразу с сути, без приветствий и вводных фраз. Никогда не используй фразы типа 'Хорошо', 'Понял вас', 'Приступаю' и т.п. ФОРМАТИРОВАНИЕ: Используй ЗАГЛАВНЫЕ БУКВЫ для выделения важных фраз и заголовков. Используй эмодзи для визуального разделения разделов (🌙 для лунных дней, ✨ для энергетики, 👕 для одежды, 🌿 для ароматов, 💎 для талисманов, 🧘 для практик, ⚠️ для предостережений). Для разделения текста используй символьные разделители '---', '***', '==='. Структурируй информацию по разделам: '🌓 ДАТА И ФАЗА ЛУНЫ 🌓' (с подробным описанием космических энергий), '🌙 ДЕТАЛЬНЫЙ РАЗБОР ЛУННЫХ ДНЕЙ 🌙' (с указанием благоприятных и неблагоприятных аспектов), '✨ ПЕРСОНАЛИЗИРОВАННЫЕ РЕКОМЕНДАЦИИ ✨' (одежда, цвета, ароматы, камни-талисманы, практики), '🧘 РИТУАЛЫ И МЕДИТАЦИИ 🧘' для усиления позитивного влияния луны, '⚠️ ПРЕДОСТЕРЕЖЕНИЯ И ОСОБЫЕ УКАЗАНИЯ ⚠️'. Используй богатый язык, метафоры и аллегории, создавая атмосферу таинства и глубокого понимания космических ритмов.",
        "max_tokens": 1500,
        "temperature": 0.8
    }
}

# Настройки фоновых задач
BACKGROUND_TASKS = {
    "update_cache_interval_minutes": 5  # Обновлять кэш каждые 5 минут
}

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