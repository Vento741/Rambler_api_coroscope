"""
Сервис таро
"""
from datetime import date
import logging

from fastapi import HTTPException

from core.cache import CacheManager
from .models import ApiResponse, TarotReading
from .parser import TarotParser

logger = logging.getLogger(__name__)

class TarotService:
    """Сервис для работы с таро"""
    
    def __init__(self, cache_manager: CacheManager, parser: TarotParser):
        self.cache_manager = cache_manager
        self.parser = parser
    
    async def get_reading_for_date(self, reading_date: date) -> ApiResponse:
        """Получение расклада таро на конкретную дату"""
        try:
            # Проверяем кэш
            cached_data = await self.cache_manager.get(reading_date)
            
            if cached_data:
                return ApiResponse(
                    success=True,
                    data=TarotReading(**cached_data),
                    cached=True
                )
            
            # Парсим новые данные
            logger.info(f"Парсинг таро для {reading_date}")
            raw_data = await self.parser.parse_tarot_reading(reading_date)
            
            # Сохраняем в кэш
            await self.cache_manager.set(reading_date, raw_data)
            
            return ApiResponse(
                success=True,
                data=TarotReading(**raw_data),
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