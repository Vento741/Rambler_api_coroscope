"""
Фоновые задачи для лунного календаря
"""
import asyncio
import logging
from datetime import date, datetime, timedelta
import time

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
        :param openrouter_service: Сервис для генерации ответов через OpenRouter
        """
        self.cache_manager = cache_manager
        self.parser = parser
        self.openrouter_service = openrouter_service
        self._task = None
        self._lock_key = "moon_calendar_task_lock"
        self._lock_ttl = 60  # Время жизни блокировки в секундах
    
    async def _acquire_lock(self) -> bool:
        """
        Попытка получить блокировку для выполнения задачи
        
        :return: True если блокировка получена, False в противном случае
        """
        # Используем cache.add, который возвращает False если ключ уже существует
        lock_id = f"{datetime.now().timestamp()}"
        return await self.cache_manager.add(self._lock_key, lock_id, self._lock_ttl)
    
    async def _release_lock(self):
        """Освобождение блокировки"""
        await self.cache_manager.delete(self._lock_key)
    
    async def update_calendar_cache_and_generate_ai_responses(self):
        """
        Обновление кэша лунного календаря и генерация AI-ответов
        
        Обновляет данные для текущего и следующего дня
        """
        # Попытка получить блокировку
        lock_acquired = await self._acquire_lock()
        if not lock_acquired:
            logger.info("Другой экземпляр фоновой задачи уже выполняется. Пропускаем запуск.")
            return
        
        try:
            today = date.today()
            tomorrow = today + timedelta(days=1)
            dates = [today, tomorrow]
            
            logger.info(f"Запуск фоновой задачи обновления кэша и генерации AI-ответов для {today}, {tomorrow}")
            
            for calendar_date in dates:
                # Обновление спарсенных данных
                logger.info(f"Обновление спарсенных данных для {calendar_date}")
                try:
                    calendar_data = await self.parser.parse_calendar_day(calendar_date)
                    await self.cache_manager.set(str(calendar_date), calendar_data)
                    logger.info(f"Спарсенные данные для {calendar_date} сохранены в кэш.")
                    
                    # Генерация и кэширование AI-ответов
                    logger.info(f"Генерация и кэширование AI-ответов для {calendar_date}...")
                    await self.openrouter_service.background_generate_and_cache_ai_responses(calendar_date)
                    logger.info(f"AI-ответы для {calendar_date} сгенерированы и кэшированы.")
                except Exception as e:
                    logger.error(f"Ошибка при обновлении данных для {calendar_date}: {e}")
            
            logger.info(f"Фоновая задача обновления кэша и генерации AI-ответов завершена для {today}, {tomorrow}")
        finally:
            # Освобождаем блокировку в любом случае
            await self._release_lock()
    
    async def run_periodic_update(self, interval_minutes: int):
        """
        Запуск периодического обновления кэша лунного календаря
        
        :param interval_minutes: Интервал обновления в минутах
        """
        logger.info(f"Следующее периодическое обновление через {interval_minutes} минут.")
        while True:
            await asyncio.sleep(interval_minutes * 60)
            await self.update_calendar_cache_and_generate_ai_responses() 