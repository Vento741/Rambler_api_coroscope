"""
Клиент для работы с API биржи Bybit
"""
import logging
from typing import Dict, List, Any, Optional, Union
import asyncio
from datetime import datetime, timedelta

import aiohttp
from pybit.unified_trading import HTTP as PybitHTTP

logger = logging.getLogger(__name__)

class BybitClient:
    """
    Асинхронный клиент для работы с API биржи Bybit
    """
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        testnet: bool = False,
        timeout: int = 10
    ):
        """
        Инициализация клиента для работы с Bybit API
        
        :param api_key: API ключ для доступа к Bybit API
        :param api_secret: API секрет для доступа к Bybit API
        :param testnet: Использовать тестовую сеть (True) или основную (False)
        :param timeout: Таймаут запросов в секундах
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.timeout = timeout
        
        # Инициализация клиента pybit
        self.client = PybitHTTP(
            testnet=self.testnet,
            api_key=self.api_key,
            api_secret=self.api_secret
        )
        
        logger.info(f"BybitClient инициализирован. Testnet: {self.testnet}")
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Получение текущих данных тикера для указанного символа
        
        :param symbol: Символ криптовалюты (например, "BTCUSDT")
        :return: Данные тикера
        """
        try:
            # Используем синхронный клиент pybit, т.к. он не имеет асинхронной версии
            result = self.client.get_tickers(
                category="spot",
                symbol=symbol
            )
            
            if result.get("retCode") == 0 and "result" in result:
                ticker_data = result["result"]
                logger.info(f"Успешно получены данные тикера для {symbol}")
                return ticker_data
            else:
                logger.error(f"Ошибка при получении данных тикера для {symbol}: {result}")
                raise Exception(f"Ошибка API Bybit: {result.get('retMsg', 'Неизвестная ошибка')}")
        
        except Exception as e:
            logger.error(f"Исключение при получении данных тикера для {symbol}: {e}", exc_info=True)
            raise
    
    async def get_klines(
        self, 
        symbol: str, 
        interval: str = "60",
        limit: int = 200,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Получение исторических данных K-линий (свечей)
        
        :param symbol: Символ криптовалюты (например, "BTCUSDT")
        :param interval: Интервал свечей:
            - Минуты: "1", "3", "5", "15", "30"
            - Часы: "60" (1ч), "120" (2ч), "240" (4ч), "360" (6ч), "720" (12ч)
            - Дни: "D" (1 день)
            - Недели: "W" (1 неделя)
            - Месяцы: "M" (1 месяц)
        :param limit: Максимальное количество записей (до 1000)
        :param start_time: Время начала в миллисекундах (опционально)
        :param end_time: Время окончания в миллисекундах (опционально)
        :return: Список K-линий
        """
        try:
            params = {
                "category": "spot",
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            if start_time:
                params["start"] = start_time
            
            if end_time:
                params["end"] = end_time
            
            result = self.client.get_kline(
                **params
            )
            
            if result.get("retCode") == 0 and "result" in result and "list" in result["result"]:
                klines_data = result["result"]["list"]
                logger.info(f"Успешно получены K-линии для {symbol}, интервал {interval}, количество: {len(klines_data)}")
                return klines_data
            else:
                logger.error(f"Ошибка при получении K-линий для {symbol}: {result}")
                raise Exception(f"Ошибка API Bybit: {result.get('retMsg', 'Неизвестная ошибка')}")
        
        except Exception as e:
            logger.error(f"Исключение при получении K-линий для {symbol}: {e}", exc_info=True)
            raise
    
    async def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Получение комплексных рыночных данных для символа
        
        :param symbol: Символ криптовалюты (например, "BTCUSDT")
        :return: Словарь с рыночными данными
        """
        try:
            # Получаем текущий тикер
            ticker_task = asyncio.create_task(self.get_ticker(symbol))
            
            # Получаем исторические данные за разные периоды
            klines_1h_task = asyncio.create_task(self.get_klines(symbol, interval="60", limit=24))  # 24 часа с интервалом 1 час
            klines_4h_task = asyncio.create_task(self.get_klines(symbol, interval="240", limit=42))  # 7 дней с интервалом 4 часа
            klines_1d_task = asyncio.create_task(self.get_klines(symbol, interval="D", limit=30))  # 30 дней с интервалом 1 день
            
            # Ожидаем завершения всех задач
            ticker_data = await ticker_task
            klines_1h = await klines_1h_task
            klines_4h = await klines_4h_task
            klines_1d = await klines_1d_task
            
            # Формируем комплексный набор данных
            market_data = {
                "symbol": symbol,
                "ticker": ticker_data,
                "historical_data": {
                    "1h": klines_1h,
                    "4h": klines_4h,
                    "1d": klines_1d
                },
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Успешно собраны комплексные рыночные данные для {symbol}")
            return market_data
        
        except Exception as e:
            logger.error(f"Ошибка при получении комплексных рыночных данных для {symbol}: {e}", exc_info=True)
            raise
    
    async def get_available_symbols(self) -> List[str]:
        """
        Получение списка доступных символов криптовалют
        
        :return: Список символов
        """
        try:
            result = self.client.get_instruments_info(
                category="spot"
            )
            
            if result.get("retCode") == 0 and "result" in result and "list" in result["result"]:
                symbols = [item["symbol"] for item in result["result"]["list"] if item["status"] == "Trading"]
                logger.info(f"Успешно получен список доступных символов. Количество: {len(symbols)}")
                return symbols
            else:
                logger.error(f"Ошибка при получении списка символов: {result}")
                raise Exception(f"Ошибка API Bybit: {result.get('retMsg', 'Неизвестная ошибка')}")
        
        except Exception as e:
            logger.error(f"Исключение при получении списка символов: {e}", exc_info=True)
            raise
    
    async def get_popular_cryptos(self) -> List[str]:
        """
        Получение списка популярных криптовалют
        
        :return: Список символов популярных криптовалют
        """
        # Список наиболее популярных криптовалют
        popular_cryptos = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
            "ADAUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT", "MATICUSDT"
        ]
        
        return popular_cryptos 