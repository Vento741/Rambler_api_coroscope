"""
Эндпоинты лунного календаря
"""
from datetime import datetime, date
from fastapi import APIRouter, HTTPException, Request

from modules.moon_calendar import MoonCalendarParser, ApiResponse, MoonCalendarService
from core.cache import CacheManager
import config 

router = APIRouter(prefix="/api/v1/moon-calendar")

# Удаляем старую глобальную инициализацию зависимостей
# cache_manager = CacheManager(ttl_minutes=config.CACHE_TTL_MINUTES)
# parser = MoonCalendarParser(timeout=config.PARSER_TIMEOUT)
# service = MoonCalendarService(cache_manager, parser)

@router.get("/current", response_model=ApiResponse)
async def get_current_moon_calendar(request: Request):
    """Получение данных лунного календаря на сегодня"""
    # Получаем сервис из state приложения
    service = request.app.state.moon_openrouter_service # Используем MoonCalendarOpenRouterService т.к. он теперь основной для API
    return await service.get_moon_calendar_response(date.today(), user_type="free") # Предполагаем, что это для "free" пользователя

@router.get("/{calendar_date}", response_model=ApiResponse)
async def get_moon_calendar(calendar_date: str, request: Request):
    """Получение данных лунного календаря на конкретную дату"""
    try:
        date_obj = datetime.strptime(calendar_date, "%Y-%m-%d").date()
        # Получаем сервис из state приложения
        service = request.app.state.moon_openrouter_service # Используем MoonCalendarOpenRouterService
        return await service.get_moon_calendar_response(date_obj, user_type="free") # Предполагаем, что это для "free" пользователя
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Неверный формат даты. Используйте YYYY-MM-DD" # Перевел на русский
        ) 