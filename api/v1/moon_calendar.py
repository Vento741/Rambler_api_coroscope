"""
Эндпоинты лунного календаря
"""
from datetime import datetime, date
from fastapi import APIRouter, HTTPException

from modules.moon_calendar import MoonCalendarParser, ApiResponse, MoonCalendarService
from core.cache import CacheManager
from config import settings

router = APIRouter(prefix="/api/v1/moon-calendar")

# Инициализация зависимостей
cache_manager = CacheManager(ttl_minutes=settings.CACHE_TTL_MINUTES)
parser = MoonCalendarParser(timeout=settings.PARSER_TIMEOUT_SECONDS)
service = MoonCalendarService(cache_manager, parser)

@router.get("/current", response_model=ApiResponse)
async def get_current_moon_calendar():
    """Получение данных лунного календаря на сегодня"""
    return await service.get_calendar_for_date(date.today())

@router.get("/{calendar_date}", response_model=ApiResponse)
async def get_moon_calendar(calendar_date: str):
    """Получение данных лунного календаря на конкретную дату"""
    try:
        date_obj = datetime.strptime(calendar_date, "%Y-%m-%d").date()
        return await service.get_calendar_for_date(date_obj)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid date format. Use YYYY-MM-DD"
        ) 