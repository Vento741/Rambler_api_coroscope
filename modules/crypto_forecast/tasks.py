"""
Фоновые задачи для сервиса прогнозирования криптовалют
"""
import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta

from core.cache import CacheManager
from modules.crypto_forecast.bybit_client import BybitClient
from modules.crypto_forecast.forecast_service import CryptoForecastService

logger = logging.getLogger(__name__)

class CryptoForecastTasks:
    """
    Класс для выполнения фоновых задач сервиса прогнозирования криптовалют
    """
    
    def __init__(
        self,
        cache_manager: CacheManager,
        bybit_client: BybitClient,
        forecast_service: CryptoForecastService
    ):
        """
        Инициализация класса задач
        
        :param cache_manager: Менеджер кэша
        :param bybit_client: Клиент для работы с Bybit API
        :param forecast_service: Сервис прогнозирования криптовалют
        """
        self.cache_manager = cache_manager
        self.bybit_client = bybit_client
        self.forecast_service = forecast_service
        
        logger.info("CryptoForecastTasks инициализирован")
    
    async def update_popular_cryptos_forecasts(self):
        """
        Обновление прогнозов для популярных криптовалют
        """
        try:
            logger.info("Запуск обновления прогнозов для популярных криптовалют")
            
            # Получаем список популярных криптовалют
            popular_cryptos = await self.bybit_client.get_popular_cryptos()
            popular_symbols = [symbol.replace("USDT", "") for symbol in popular_cryptos]
            
            # Периоды прогнозов
            periods = ["hour", "day", "week"]
            
            # Счетчики для статистики
            total_forecasts = len(popular_symbols) * len(periods)
            successful_forecasts = 0
            failed_forecasts = 0
            
            logger.info(f"Начинаем обновление {total_forecasts} прогнозов для {len(popular_symbols)} популярных криптовалют")
            
            # Обновляем прогнозы для каждой криптовалюты и каждого периода
            for symbol in popular_symbols:
                for period in periods:
                    try:
                        logger.info(f"Обновление прогноза для {symbol}, период {period}")
                        
                        # Генерируем прогноз с принудительным обновлением
                        await self.forecast_service.generate_forecast(
                            symbol=symbol,
                            period=period,
                            user_type="free",  # Используем базовый тип пользователя для кэширования
                            force_refresh=True
                        )
                        
                        successful_forecasts += 1
                        logger.info(f"Успешно обновлен прогноз для {symbol}, период {period}")
                        
                        # Небольшая пауза между запросами для снижения нагрузки
                        await asyncio.sleep(1)
                    
                    except Exception as e:
                        failed_forecasts += 1
                        logger.error(f"Ошибка при обновлении прогноза для {symbol}, период {period}: {e}", exc_info=True)
                        
                        # Пауза перед следующей попыткой
                        await asyncio.sleep(5)
            
            logger.info(f"Обновление прогнозов завершено. Успешно: {successful_forecasts}, Ошибок: {failed_forecasts}")
            
        except Exception as e:
            logger.error(f"Критическая ошибка при обновлении прогнозов для популярных криптовалют: {e}", exc_info=True)
    
    async def run_periodic_update(self, interval_minutes: int = 60):
        """
        Запуск периодического обновления прогнозов
        
        :param interval_minutes: Интервал обновления в минутах
        """
        logger.info(f"Запуск периодического обновления прогнозов каждые {interval_minutes} минут")
        
        while True:
            try:
                # Запускаем обновление прогнозов
                await self.update_popular_cryptos_forecasts()
                
                # Ждем указанный интервал перед следующим обновлением
                logger.info(f"Ожидание {interval_minutes} минут перед следующим обновлением прогнозов")
                await asyncio.sleep(interval_minutes * 60)
            
            except asyncio.CancelledError:
                logger.info("Задача периодического обновления прогнозов отменена")
                break
            
            except Exception as e:
                logger.error(f"Ошибка в периодическом обновлении прогнозов: {e}", exc_info=True)
                
                # Ждем перед повторной попыткой (половина интервала)
                retry_interval = max(5 * 60, interval_minutes * 30)  # Минимум 5 минут, максимум половина интервала
                logger.info(f"Повторная попытка через {retry_interval // 60} минут")
                await asyncio.sleep(retry_interval) 