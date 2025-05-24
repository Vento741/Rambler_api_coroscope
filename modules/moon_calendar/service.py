"""
Сервис лунного календаря
"""
from datetime import date
import logging

from fastapi import HTTPException

from core.cache import CacheManager
from .models import ApiResponse, CalendarDayResponse
from .parser import MoonCalendarParser

logger = logging.getLogger(__name__)

class MoonCalendarService:
    """Сервис для работы с лунным календарем"""
    
    def __init__(self, cache_manager: CacheManager, parser: MoonCalendarParser):
        self.cache_manager = cache_manager
        self.parser = parser
    
    async def get_calendar_for_date(self, calendar_date: date) -> ApiResponse:
        """Получение данных лунного календаря на конкретную дату"""
        try:
            # Проверяем кэш
            cached_data = await self.cache_manager.get(calendar_date)
            
            if cached_data:
                return ApiResponse(
                    success=True,
                    data=CalendarDayResponse(**cached_data),
                    cached=True
                )
            
            # Парсим новые данные
            logger.info(f"Парсинг лунного календаря для {calendar_date}")
            raw_data = await self.parser.parse_calendar_day(calendar_date)
            
            # Сохраняем в кэш
            await self.cache_manager.set(calendar_date, raw_data)
            
            return ApiResponse(
                success=True,
                data=CalendarDayResponse(**raw_data),
                cached=False
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            return ApiResponse(
                success=False,
                error=f"Внутренняя ошибка сервера: {str(e)}"
            ) 