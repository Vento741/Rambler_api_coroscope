"""
Эндпоинты для работы с астрологическими данными через OpenRouter
"""
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from modules.moon_calendar import MoonCalendarParser, ApiResponse
from modules.moon_calendar.openrouter_service import MoonCalendarOpenRouterService
from core.cache import CacheManager
from core.openrouter_client import OpenRouterClient
import config

router = APIRouter(prefix="/api/v1/astro_bot")

# Инициализация зависимостей
cache_manager = CacheManager(ttl_minutes=config.CACHE_TTL_MINUTES)
parser = MoonCalendarParser(timeout=config.PARSER_TIMEOUT)

# Инициализация клиента OpenRouter
openrouter_client = OpenRouterClient(
    api_url=config.OPENROUTER_API_URL,
    api_keys=config.OPENROUTER_API_KEYS,
    models=config.OPENROUTER_MODELS,
    model_configs=config.OPENROUTER_MODEL_CONFIGS,
    model_api_keys=config.OPENROUTER_MODEL_API_KEYS,
    timeout=30  # Увеличенный таймаут для всех запросов до 30 секунд
)

# Инициализация сервиса
openrouter_service = MoonCalendarOpenRouterService(
    cache_manager=cache_manager,
    parser=parser,
    openrouter_client=openrouter_client,
    prompts_config=config.OPENROUTER_PROMPTS
)

@router.get("/moon_day", response_model=ApiResponse)
async def get_moon_day(
    user_type: str = Query("free", description="Тип пользователя: free или premium"),
    calendar_date: Optional[str] = Query(None, description="Дата в формате YYYY-MM-DD")
):
    """
    Получение данных лунного календаря с обработкой через OpenRouter
    
    - **user_type**: Тип пользователя (free/premium)
    - **calendar_date**: Дата в формате YYYY-MM-DD (если не указана, используется текущая дата)
    """
    # Проверка типа пользователя
    if user_type not in ["free", "premium"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный тип пользователя. Допустимые значения: free, premium"
        )
    
    # Определение даты
    try:
        if calendar_date:
            date_obj = datetime.strptime(calendar_date, "%Y-%m-%d").date()
        else:
            date_obj = date.today()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Неверный формат даты. Используйте YYYY-MM-DD"
        )
    
    # Получение ответа
    return await openrouter_service.get_moon_calendar_response(date_obj, user_type) 