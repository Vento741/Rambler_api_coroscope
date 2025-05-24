"""
Эндпоинты таро
"""
from datetime import datetime, date
from fastapi import APIRouter, HTTPException

from modules.tarot import TarotParser, ApiResponse
from modules.tarot.service import TarotService
from core.cache import CacheManager
import config 

router = APIRouter(prefix="/api/v1/tarot")

# Инициализация зависимостей
cache_manager = CacheManager(ttl_minutes=config.CACHE_TTL_MINUTES)
parser = TarotParser(timeout=config.PARSER_TIMEOUT)
service = TarotService(cache_manager, parser)

@router.get("/current", response_model=ApiResponse)
async def get_current_tarot_reading():
    """Получение расклада таро на сегодня"""
    return await service.get_reading_for_date(date.today())

@router.get("/{reading_date}", response_model=ApiResponse)
async def get_tarot_reading(reading_date: str):
    """Получение расклада таро на конкретную дату"""
    try:
        date_obj = datetime.strptime(reading_date, "%Y-%m-%d").date()
        return await service.get_reading_for_date(date_obj)
    except ValueError:
        raise HTTPException(
            status_code=400, 
            detail="Invalid date format. Use YYYY-MM-DD"
        ) 