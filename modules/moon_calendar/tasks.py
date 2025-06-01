"""
Фоновые задачи для лунного календаря
"""
import asyncio
import logging
from datetime import date, datetime, timedelta

from core.cache import CacheManager
from .parser import MoonCalendarParser
from .openrouter_service import MoonCalendarOpenRouterService

logger = logging.getLogger(__name__)

class MoonCalendarTasks:
    """Класс для фоновых задач лунного календаря"""
    
    def __init__(self, cache_manager: CacheManager, parser: MoonCalendarParser, openrouter_service: MoonCalendarOpenRouterService):
        """
        Инициализация
        
        :param cache_manager: Менеджер кэша
        :param parser: Парсер лунного календаря
        :param openrouter_service: Сервис для работы с OpenRouter
        """
        self.cache_manager = cache_manager
        self.parser = parser
        self.openrouter_service = openrouter_service
    
    async def update_calendar_cache_and_generate_ai_responses(self) -> None:
        """Обновление кэша лунного календаря (спарсенные данные) и генерация AI-ответов для текущего и следующего дня."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        dates_to_process = [today, tomorrow]

        logger.info(f"Запуск фоновой задачи обновления кэша и генерации AI-ответов для {', '.join(map(str, dates_to_process))}")
        
        for current_date in dates_to_process:
            try:
                logger.info(f"Обновление спарсенных данных для {current_date}")
                parsed_data = await self.parser.parse_calendar_day(current_date)
                
                # Сначала сохраняем только спарсенные данные. 
                # Это важно, т.к. _get_calendar_data в openrouter_service будет брать их из кэша.
                await self.cache_manager.set(current_date, parsed_data) 
                logger.info(f"Спарсенные данные для {current_date} сохранены в кэш.")

                # Теперь генерируем и кэшируем AI ответы для этой даты
                logger.info(f"Генерация и кэширование AI-ответов для {current_date}...")
                await self.openrouter_service.background_generate_and_cache_ai_responses(current_date)
                logger.info(f"AI-ответы для {current_date} сгенерированы и кэшированы.")

            except Exception as e:
                logger.error(f"Ошибка при обработке даты {current_date} в фоновой задаче: {e}", exc_info=True)
        
        logger.info(f"Фоновая задача обновления кэша и генерации AI-ответов завершена для {', '.join(map(str, dates_to_process))}")
    
    async def run_periodic_update(self, interval_minutes: int) -> None:
        """
        Запуск периодического обновления кэша и AI-ответов
        
        :param interval_minutes: Интервал обновления в минутах
        """
        while True:
            try:
                await self.update_calendar_cache_and_generate_ai_responses()
            except Exception as e:
                logger.error(f"Ошибка в периодическом обновлении кэша и AI-ответов: {e}", exc_info=True)
            
            logger.info(f"Следующее периодическое обновление через {interval_minutes} минут.")
            await asyncio.sleep(interval_minutes * 60) 