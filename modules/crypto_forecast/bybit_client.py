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

class SymbolNotFoundError(ValueError):
    """Исключение для несуществующего или неторгуемого символа."""
    def __init__(self, message="Symbol not found", symbol=None):
        self.symbol = symbol
        super().__init__(message)

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
        
        # Кэш для списка символов
        self.available_symbols_cache: Optional[List[str]] = None
        self.symbols_cache_time: Optional[datetime] = None
        self.symbols_cache_ttl: timedelta = timedelta(hours=1)
        
        # Популярные криптовалюты
        self.popular_cryptos = [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
            "ADAUSDT", "DOGEUSDT", "DOTUSDT", "AVAXUSDT"
        ]
        
        # Словарь с полными названиями криптовалют
        self.crypto_names = {
            "BTC": "Bitcoin",
            "ETH": "Ethereum",
            "SOL": "Solana",
            "BNB": "Binance Coin",
            "XRP": "Ripple",
            "ADA": "Cardano",
            "DOGE": "Dogecoin",
            "DOT": "Polkadot",
            "AVAX": "Avalanche",
            "MATIC": "Polygon",
            "LINK": "Chainlink",
            "UNI": "Uniswap",
            "ATOM": "Cosmos",
            "LTC": "Litecoin",
            "ALGO": "Algorand",
            "NEAR": "NEAR Protocol",
            "FTM": "Fantom",
            "AAVE": "Aave",
            "GRT": "The Graph",
            "SNX": "Synthetix",
            "SHIB": "Shiba Inu",
            "FIL": "Filecoin",
            "ICP": "Internet Computer",
            "VET": "VeChain",
            "XLM": "Stellar",
            "EOS": "EOS",
            "SAND": "The Sandbox",
            "MANA": "Decentraland",
            "THETA": "Theta Network",
            "XTZ": "Tezos",
            "AXS": "Axie Infinity",
            "NEO": "NEO",
            "EGLD": "Elrond",
            "KSM": "Kusama",
            "XMR": "Monero",
            "HBAR": "Hedera",
            "ONE": "Harmony",
            "ENJ": "Enjin Coin",
            "GALA": "Gala",
            "ROSE": "Oasis Network",
            "CHZ": "Chiliz",
            "ZEC": "Zcash",
            "DASH": "Dash",
            "BAT": "Basic Attention Token",
            "CAKE": "PancakeSwap",
            "RUNE": "THORChain",
            "COMP": "Compound",
            "YFI": "yearn.finance",
            "SUSHI": "SushiSwap"
        }
        
        logger.info(f"BybitClient инициализирован. Testnet: {self.testnet}")
    
    async def _validate_symbol(self, symbol: str):
        """Проверяет валидность символа, используя кэшированный список."""
        # Получаем полный список символов (с кэшированием)
        available_symbols = await self.get_available_symbols()
        if symbol not in available_symbols:
            clean_symbol = symbol.replace('USDT', '')
            logger.warning(f"Попытка запроса для невалидного символа: {symbol}")
            raise SymbolNotFoundError(
                message=f"Символ '{clean_symbol}' не найден или не торгуется.",
                symbol=clean_symbol
            )

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Получение текущих данных тикера для указанного символа
        
        :param symbol: Символ криптовалюты (например, "BTCUSDT")
        :return: Данные тикера
        """
        await self._validate_symbol(symbol)
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
        :param interval: Интервал свечей
        :param limit: Максимальное количество записей (до 1000)
        :param start_time: Время начала в миллисекундах (опционально)
        :param end_time: Время окончания в миллисекундах (опционально)
        :return: Список K-линий
        """
        await self._validate_symbol(symbol)
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
            
            # Получаем исторические данные за разные периоды. Увеличиваем лимиты для более глубокого анализа.
            klines_1h_task = asyncio.create_task(self.get_klines(symbol, interval="60", limit=200))  # ~8 дней
            klines_4h_task = asyncio.create_task(self.get_klines(symbol, interval="240", limit=200)) # ~33 дня
            klines_1d_task = asyncio.create_task(self.get_klines(symbol, interval="D", limit=200))   # 200 дней
            
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
    
    async def get_available_symbols(self, force_refresh: bool = False) -> List[str]:
        """
        Получение списка доступных символов криптовалют с кэшированием.
        
        :param force_refresh: Принудительное обновление списка символов
        :return: Список символов
        """
        now = datetime.now()
        if not force_refresh and self.available_symbols_cache and self.symbols_cache_time and (now - self.symbols_cache_time < self.symbols_cache_ttl):
            logger.debug("Возвращаем список символов из кэша BybitClient.")
            return self.available_symbols_cache

        try:
            logger.info("Обновление кэша списка символов Bybit...")
            result = self.client.get_instruments_info(
                category="spot"
            )
            
            if result.get("retCode") == 0 and "result" in result and "list" in result["result"]:
                symbols = [item["symbol"] for item in result["result"]["list"] if item["status"] == "Trading"]
                logger.info(f"Успешно получен новый список доступных символов. Количество: {len(symbols)}")
                
                # Обновляем кэш
                self.available_symbols_cache = symbols
                self.symbols_cache_time = now
                
                return symbols
            else:
                logger.error(f"Ошибка при получении списка символов: {result}")
                # В случае ошибки возвращаем старые данные из кэша, если они есть
                if self.available_symbols_cache:
                    logger.warning("Возвращаем устаревшие данные из кэша символов из-за ошибки обновления.")
                    return self.available_symbols_cache
                raise Exception(f"Ошибка API Bybit: {result.get('retMsg', 'Неизвестная ошибка')}")
        
        except Exception as e:
            logger.error(f"Исключение при получении списка символов: {e}", exc_info=True)
            if self.available_symbols_cache:
                logger.warning("Возвращаем устаревшие данные из кэша символов из-за исключения при обновлении.")
                return self.available_symbols_cache
            raise
    
    async def get_popular_cryptos(self) -> List[str]:
        """
        Получение списка популярных криптовалют
        
        :return: Список символов популярных криптовалют
        """
        return self.popular_cryptos

    def get_crypto_full_name(self, symbol: str) -> str:
        """
        Получить полное название криптовалюты по символу
        
        :param symbol: Символ криптовалюты (например, BTC)
        :return: Полное название криптовалюты
        """
        # Нормализуем символ (убираем USDT, если есть)
        clean_symbol = symbol.replace("USDT", "")
        
        # Возвращаем полное название или сам символ, если название не найдено
        return self.crypto_names.get(clean_symbol, clean_symbol) 