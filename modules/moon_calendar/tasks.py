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
        self._is_updating = False # Флаг для предотвращения одновременного запуска
    
    async def update_calendar_cache_and_generate_ai_responses(self) -> None:
        """Обновление кэша лунного календаря (спарсенные данные) и генерация AI-ответов для текущего и следующего дня."""
        if self._is_updating:
            logger.info("Обновление уже выполняется, пропуск этого запуска.")
            return

        self._is_updating = True
        try:
            today = date.today()
            tomorrow = today + timedelta(days=1)
            dates_to_process = [today, tomorrow]

            logger.info(f"Запуск фоновой задачи обновления кэша и генерации AI-ответов для {', '.join(map(str, dates_to_process))}")
            
            for current_date in dates_to_process:
                try:
                    # Проверяем, что current_date действительно является объектом date
                    if not isinstance(current_date, date):
                        logger.error(f"Некорректный тип даты: {type(current_date)}. Ожидается datetime.date. Пропускаю дату.")
                        continue
                        
                    logger.info(f"Обновление спарсенных данных для {current_date.isoformat()}")
                    parsed_data = await self.parser.parse_calendar_day(current_date)
                    
                    # Сначала сохраняем только спарсенные данные. 
                    # Это важно, т.к. _get_calendar_data в openrouter_service будет брать их из кэша.
                    await self.cache_manager.set(current_date, parsed_data) 
                    logger.info(f"Спарсенные данные для {current_date.isoformat()} сохранены в кэш.")

                    # Теперь генерируем и кэшируем AI ответы для этой даты
                    logger.info(f"Генерация и кэширование AI-ответов для {current_date.isoformat()}...")
                    await self.openrouter_service.background_generate_and_cache_ai_responses(current_date)
                    logger.info(f"AI-ответы для {current_date.isoformat()} сгенерированы и кэшированы.")

                except Exception as e:
                    logger.error(f"Ошибка при обработке даты {current_date} в фоновой задаче: {e}", exc_info=True)
            
            logger.info(f"Фоновая задача обновления кэша и генерации AI-ответов завершена для {', '.join(map(str, dates_to_process))}")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в фоновой задаче обновления кэша: {e}", exc_info=True)
        finally: # Гарантируем сброс флага
            self._is_updating = False
    
    async def run_periodic_update(self, interval_minutes: int) -> None:
        """
        Запуск периодического обновления кэша и AI-ответов.
        Первое фактическое обновление в рамках этой функции произойдет ПОСЛЕ первого интервала сна.
        Для немедленного запуска задачи при старте приложения (до первого интервала),
        необходимо вызвать self.update_calendar_cache_and_generate_ai_responses() отдельно 
        перед запуском этой периодической задачи.
        
        :param interval_minutes: Интервал обновления в минутах
        """
        logger.info(f"Периодическое обновление кэша и AI-ответов настроено. Следующий запуск через {interval_minutes} минут.")
        
        # Бесконечный цикл обновления с защитой от исключений
        while True:
            try:
                # Сначала ждем указанный интервал
                await asyncio.sleep(interval_minutes * 60)
                
                # Затем выполняем обновление
                logger.info(f"Начало планового периодического обновления кэша ({interval_minutes} мин).")
                await self.update_calendar_cache_and_generate_ai_responses()
                logger.info(f"Плановое периодическое обновление завершено. Следующий запуск через {interval_minutes} минут.")
            except asyncio.CancelledError:
                # Позволяем задаче корректно завершиться при отмене
                logger.info("Периодическое обновление отменено.")
                break
            except Exception as e:
                # Логируем ошибку, но продолжаем цикл
                logger.error(f"Критическая ошибка в периодическом обновлении кэша и AI-ответов: {e}", exc_info=True)
                logger.info(f"Периодическое обновление продолжит работу. Следующая попытка через {interval_minutes} минут.") 