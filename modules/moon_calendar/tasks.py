"""
Фоновые задачи для лунного календаря
"""
import asyncio
import logging
from datetime import date, datetime, timedelta

from core.cache import CacheManager
from .parser import MoonCalendarParser

logger = logging.getLogger(__name__)

class MoonCalendarTasks:
    """Класс для фоновых задач лунного календаря"""
    
    def __init__(self, cache_manager: CacheManager, parser: MoonCalendarParser):
        """
        Инициализация
        
        :param cache_manager: Менеджер кэша
        :param parser: Парсер лунного календаря
        """
        self.cache_manager = cache_manager
        self.parser = parser
    
    async def update_calendar_cache(self) -> None:
        """Обновление кэша лунного календаря для текущего дня"""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        try:
            logger.info("Запуск фоновой задачи обновления кэша лунного календаря")
            
            # Обновляем кэш для сегодня
            logger.info(f"Обновление кэша для {today}")
            today_data = await self.parser.parse_calendar_day(today)
            await self.cache_manager.set(today, today_data)
            
            # Обновляем кэш для завтра
            logger.info(f"Обновление кэша для {tomorrow}")
            tomorrow_data = await self.parser.parse_calendar_day(tomorrow)
            await self.cache_manager.set(tomorrow, tomorrow_data)
            
            logger.info("Фоновая задача обновления кэша лунного календаря завершена")
        except Exception as e:
            logger.error(f"Ошибка при обновлении кэша лунного календаря: {e}")
    
    async def run_periodic_update(self, interval_minutes: int) -> None:
        """
        Запуск периодического обновления кэша
        
        :param interval_minutes: Интервал обновления в минутах
        """
        while True:
            try:
                await self.update_calendar_cache()
            except Exception as e:
                logger.error(f"Ошибка в периодическом обновлении кэша: {e}")
            
            # Ждем до следующего обновления
            await asyncio.sleep(interval_minutes * 60) 