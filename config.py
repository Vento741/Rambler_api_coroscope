"""
Конфигурационный файл приложения
"""
from dotenv import load_dotenv
import os
from typing import List, Optional, Dict, Any
from pathlib import Path

# Загрузка переменных окружения из .env файла
load_dotenv()

# Базовые настройки приложения
APP_NAME = "Rambler API Service"
APP_VERSION = "1.1.0"
APP_DESCRIPTION = "Асинхронный API сервис для парсинга данных с Rambler"

# Настройки сервера
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8081"))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
WORKERS = int(os.getenv("WORKERS", "1"))

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
CACHE_TTL_MINUTES = int(os.getenv("CACHE_TTL_MINUTES", "180"))  # 3 часа
CACHE_CLEANUP_INTERVAL = int(os.getenv("CACHE_CLEANUP_INTERVAL", "600"))  # 10 минут

# Настройки парсера
PARSER_TIMEOUT = int(os.getenv("PARSER_TIMEOUT", "10"))  # 10 секунд
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
        os.getenv("API_for_Gemini_2.0_Flash", ""),
        os.getenv("Qwen2.5_VL_72B_Instruct_free", ""),
        os.getenv("API_for_Gemini_2.0_Flash_Exp_free", ""),
        os.getenv("DeepSeek_Prover_V2_free", "")
    ] if key
]

# Модели OpenRouter
OPENROUTER_MODELS = [
    "google/gemini-2.0-flash-001",
    "google/gemini-2.0-flash-exp:free",
    "qwen/qwen2.5-vl-72b-instruct:free",
    "deepseek-r1-0528-qwen3-8b:free",
    "deepseek/deepseek-prover-v2:free"
]

# Сопоставление моделей и их API ключей
OPENROUTER_MODEL_API_KEYS = {
    "google/gemini-2.0-flash-001": os.getenv("API_for_Gemini_2.0_Flash", ""),
    "google/gemini-2.0-flash-exp:free": os.getenv("API_for_Gemini_2.0_Flash_Exp_free", ""),
    "qwen/qwen2.5-vl-72b-instruct:free": os.getenv("Qwen2.5_VL_72B_Instruct_free", ""),
    "deepseek/deepseek-prover-v2:free": os.getenv("DeepSeek_Prover_V2_free", ""),
    "deepseek-r1-0528-qwen3-8b:free": os.getenv("Deepseek_R1_0528_Qwen3_8B_free", "")
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
    },
    "deepseek-r1-0528-qwen3-8b:free": {
        "request_type": "openai",
        "timeout": 60
    }
}

# Настройки промптов для разных типов пользователей
OPENROUTER_PROMPTS = {
    "free": {
        "system_message": "Ты — мистический эксперт по лунному календарю. Твоя задача — преобразовать данные лунного календаря в краткое, но информативное сообщение. ВАЖНО: Начинай сразу с сути, без приветствий и вводных фраз. ЗАПРЕЩЕНО: использовать звёздочки (**), сложное форматирование (markdown/HTML), специальные символы Unicode. РАЗРЕШЕНО: использовать только простые эмодзи (🌙 🌑 🌓 🌕 ✨ 🔮), дефисы, точки, запятые, кавычки. СТРУКТУРА: используй ЗАГЛАВНЫЕ БУКВЫ для заголовков, после заголовка ставь перенос строки. Используй двойной перенос строки между разделами. Формат ответа: 'ДАТА И ФАЗА ЛУНЫ' (краткое описание), 'ЛУННЫЙ ДЕНЬ' (описание влияния), 'СОВЕТ ДНЯ' (конкретная рекомендация). Сделай текст кратким (не менее 300 и не более 500 слов) и простым для понимания.",
        "max_tokens": 1500,
        "temperature": 0.5
    },
    "premium": {
        "system_message": "Ты — глубокий знаток лунного календаря, обладающий древней мудростью. Твоя задача — создать детальное повествование о лунном дне и его влиянии на разные сферы жизни. ВАЖНО: Начинай сразу с сути, без приветствий и вводных фраз. ЗАПРЕЩЕНО: использовать звёздочки (**), сложное форматирование (markdown/HTML), специальные символы Unicode. РАЗРЕШЕНО: использовать только простые эмодзи (🌙 🌑 🌓 🌕 ✨ 🔮 💫 🌿 💎 🧘), дефисы, точки, запятые, кавычки. СТРУКТУРА: используй ЗАГЛАВНЫЕ БУКВЫ для заголовков, после заголовка ставь перенос строки. Используй двойной перенос строки между разделами. Включи следующие разделы: 'ДАТА И ФАЗА ЛУНЫ' (описание космических энергий), 'ЛУННЫЕ ДНИ' (описание каждого активного лунного дня), 'РЕКОМЕНДАЦИИ' (советы по одежде, цветам, ароматам), 'ПРАКТИКИ И МЕДИТАЦИИ', 'ПРЕДОСТЕРЕЖЕНИЯ'. Пиши ясным, выразительным языком без излишней эзотерики.",
        "max_tokens": 3000,
        "temperature": 0.7
    }
}

# Настройки промптов для карт Таро
TAROT_PROMPTS = {
    "free": {
        "system_message": "Ты — опытный таролог с глубоким пониманием символики карт Таро. Твоя задача — создать мистическое и интригующее толкование расклада Таро, основанное на предоставленных картах и их позициях. ВАЖНО: Начинай сразу с сути, без приветствий и вводных фраз. Никогда не используй фразы типа 'Хорошо', 'Понял вас', 'Приступаю' и т.п. ФОРМАТИРОВАНИЕ: Используй ЗАГЛАВНЫЕ БУКВЫ для выделения важных фраз и заголовков. Используй эмодзи для визуального разделения разделов (🔮 для общего толкования, ⭐ для ключевых моментов, 🧿 для советов). Для разделения текста используй символьные разделители '---', '***', '==='. Структура ответа: '🔮 ОБЩЕЕ ТОЛКОВАНИЕ 🔮' (краткая суть расклада и его энергии), '⭐ КЛЮЧЕВЫЕ МОМЕНТЫ ⭐' (основные выводы из расклада), '🧿 СОВЕТ 🧿' (практическая рекомендация на основе карт). Используй таинственный, но понятный язык, создавая атмосферу мистики и глубокого прозрения. Сделай толкование подробным, содержательным и запоминающимся. Не менее 500 и не более 1000 слов.",
        "max_tokens": 200,
        "temperature": 0.7
    },
    "premium": {
        "system_message": "Ты — мастер-таролог высочайшего уровня, хранитель древних знаний и тайн карт Таро. Твоя задача — создать глубокое, многоуровневое и детальное толкование расклада, раскрывающее все нюансы и скрытые значения карт. ВАЖНО: Начинай сразу с сути, без приветствий и вводных фраз. Никогда не используй фразы типа 'Хорошо', 'Понял вас', 'Приступаю' и т.п. ФОРМАТИРОВАНИЕ: Используй ЗАГЛАВНЫЕ БУКВЫ для выделения важных фраз и заголовков. Используй эмодзи для визуального разделения разделов (🔮 для общего толкования, 🃏 для анализа отдельных карт, 🔄 для взаимосвязей между картами, ⚡ для ключевых инсайтов, 🛤️ для возможных путей развития, 🧿 для советов и рекомендаций). Для разделения текста используй символьные разделители '---', '***', '==='. Структура ответа: '🔮 ОБЩЕЕ ТОЛКОВАНИЕ 🔮' (энергия и суть расклада), '🃏 АНАЛИЗ КАРТ 🃏' (детальный разбор значения каждой карты в контексте позиции), '🔄 ВЗАИМОСВЯЗИ 🔄' (как карты влияют друг на друга и создают общую картину), '⚡ КЛЮЧЕВЫЕ ИНСАЙТЫ ⚡' (глубокие прозрения и скрытые значения), '🛤️ ПУТИ РАЗВИТИЯ 🛤️' (возможные сценарии будущего), '🧿 РЕКОМЕНДАЦИИ 🧿' (конкретные советы и практические шаги). Используй богатый, образный язык с метафорами и символизмом, создавая атмосферу глубокого мистического опыта и трансформационного прозрения.",
        "max_tokens": 200,
        "temperature": 0.8
    }
}

CRYPTO_FORECAST_PROMPTS = {
    "default": {
        "system_message": "Ты — превосходный криптоаналитик с 30-летним опытом в трейдинге и алгоритмической торговле. Твоя задача: мгновенный анализ котировок (RSI, EMA, объемы) и генерация ЕДИНСТВЕННОГО, наиболее вероятного прогноза без преамбул и альтернативных сценариев. СТРУКТУРА ВЫВОДА:\n\n"
                          "⤴️ ТЕКУЩАЯ СИТУАЦИЯ\nКраткий снимок цены и индикаторов\n\n"
                          "📊 ОБЪЕМЫ ТОРГОВ\nАнализ объема и его динамики\n\n"
                          "📉 ТЕХНИЧЕСКИЙ АНАЛИЗ\nПаттерны, RSI, EMA, тренды\n\n"
                          "📍 КЛЮЧЕВЫЕ УРОВНИ\nПоддержка/сопротивление с ценами\n\n"
                          "🔮 ПРОГНОЗ\nОДИН наиболее вероятный сценарий (рост или падение) с указанием ценовых диапазонов и вероятности в процентах.\n\n"
                          "💼 ТОРГОВЫЕ РЕКОМЕНДАЦИИ\nОДНА торговая рекомендация, соответствующая прогнозу. Структурированно, кастомизированно. Точные параметры: SHORT\LONG \n, ТВХ \n, TP1/TP2/TP3 \n, SL (перевод в безубыток после TP1)\n, % вероятности отработки, риск-доходность\n\n"
                          "ПРАВИЛА:\n"
                          "1. НИКАКОГО MARKDOWN (особенно * и **)\n"
                          "2. ТОЛЬКО ЗАГЛАВНЫЕ ЗАГОЛОВКИ С ЭМОДЗИ\n"
                          "3. ДВОЙНОЙ ПЕРЕНОС СТРОКИ между разделами\n"
                          "4. Цифры, проценты, конкретные ценовые уровни\n"
                          "5. Никаких пояснений вне структуры",
        "max_tokens": 1500,
        "temperature": 0.3
    }
}

# Настройки TTL для кеширования прогнозов (в секундах)
CRYPTO_FORECAST_CACHE_TTL = {
    "hour": 1800,    # 30 минут для часового прогноза
    "day": 7200,     # 2 часа для дневного прогноза
    "week": 14400    # 4 часа для недельного прогноза
}

# Настройки фоновых задач
BACKGROUND_TASKS = {
    "enabled": True,
    "update_cache_interval_minutes": 60,  # Интервал обновления кэша лунного календаря в минутах
    "update_interval": {
        "popular_cryptos": 3600,  # 1 час
    }
}

# Redis settings
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Настройки Bybit API
BYBIT_API_KEY: str = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET: str = os.getenv("BYBIT_API_SECRET", "")
BYBIT_TESTNET: bool = os.getenv("BYBIT_TESTNET", "false").lower() == "true"

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

# Базовый URL для формирования полных URL к ресурсам
BASE_URL = os.getenv("BASE_URL", "http://81.177.6.93:8081")
