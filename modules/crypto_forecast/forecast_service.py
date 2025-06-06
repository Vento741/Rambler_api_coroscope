"""
Сервис для генерации прогнозов криптовалют с использованием данных Bybit и моделей ИИ
"""
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from core.cache import CacheManager
from core.openrouter_client import OpenRouterClient
from modules.crypto_forecast.bybit_client import BybitClient, SymbolNotFoundError
import config

logger = logging.getLogger(__name__)

class CryptoForecastService:
    """
    Сервис для генерации прогнозов криптовалют
    """
    
    def __init__(
        self,
        cache_manager: CacheManager,
        bybit_client: BybitClient,
        openrouter_client: OpenRouterClient,
        prompts_config: Dict[str, Dict[str, Any]]
    ):
        """
        Инициализация сервиса прогнозирования криптовалют
        
        :param cache_manager: Менеджер кэша
        :param bybit_client: Клиент для работы с Bybit API
        :param openrouter_client: Клиент для работы с OpenRouter API
        :param prompts_config: Конфигурация промптов
        """
        self.cache_manager = cache_manager
        self.bybit_client = bybit_client
        self.openrouter_client = openrouter_client
        self.prompts_config = prompts_config
        
        logger.info("CryptoForecastService инициализирован")
    
    def _generate_cache_key(self, symbol: str, period: str) -> str:
        """
        Генерация ключа для кэша
        
        :param symbol: Символ криптовалюты
        :param period: Период прогноза
        :return: Ключ для кэша
        """
        return f"crypto_forecast_{symbol.lower()}_{period}"
    
    async def _prepare_forecast_prompt(
        self,
        market_data: Dict[str, Any],
        period: str
    ) -> str:
        """
        Подготовка промпта для генерации прогноза
        
        :param market_data: Рыночные данные
        :param period: Период прогноза (hour, day, week)
        :return: Промпт для модели
        """
        symbol = market_data["symbol"]
        ticker = market_data["ticker"]
        historical_data = market_data["historical_data"]
        
        # Получаем текущую цену
        current_price = "Неизвестно"
        if "list" in ticker and ticker["list"] and len(ticker["list"]) > 0:
            current_price = ticker["list"][0].get("lastPrice", "Неизвестно")
        
        # Формируем текст с историческими данными
        historical_text = ""
        
        # Добавляем данные по часам (последние 200 свечей)
        if "1h" in historical_data and historical_data["1h"]:
            historical_text += "\nДанные по часам (200 свечей, ~8 дней):\n"
            for kline in historical_data["1h"]:
                if len(kline) >= 6:
                    timestamp = datetime.fromtimestamp(int(kline[0]) / 1000).strftime("%Y-%m-%d %H:%M")
                    open_price, high_price, low_price, close_price, volume = kline[1:6]
                    historical_text += f"- {timestamp}: O:{open_price}, H:{high_price}, L:{low_price}, C:{close_price}, V:{volume}\n"
        
        # Добавляем данные по 4 часам (последние 200 свечей)
        if "4h" in historical_data and historical_data["4h"]:
            historical_text += "\nДанные по 4 часам (200 свечей, ~33 дня):\n"
            for kline in historical_data["4h"]:
                if len(kline) >= 6:
                    timestamp = datetime.fromtimestamp(int(kline[0]) / 1000).strftime("%Y-%m-%d %H:%M")
                    open_price, high_price, low_price, close_price, volume = kline[1:6]
                    historical_text += f"- {timestamp}: O:{open_price}, H:{high_price}, L:{low_price}, C:{close_price}, V:{volume}\n"
        
        # Добавляем данные по дням (последние 200 свечей)
        if "1d" in historical_data and historical_data["1d"]:
            historical_text += "\nДанные по дням (200 свечей, 200 дней):\n"
            for kline in historical_data["1d"]:
                if len(kline) >= 6:
                    timestamp = datetime.fromtimestamp(int(kline[0]) / 1000).strftime("%Y-%m-%d")
                    open_price, high_price, low_price, close_price, volume = kline[1:6]
                    historical_text += f"- {timestamp}: O:{open_price}, H:{high_price}, L:{low_price}, C:{close_price}, V:{volume}\n"
        
        # Формируем текст с периодом прогноза
        period_text = ""
        if period == "hour":
            period_text = "на ближайший час"
        elif period == "day":
            period_text = "на завтра"
        elif period == "week":
            period_text = "на ближайшую неделю"
        
        # Формируем промпт
        prompt = f"""
Проанализируй данные о криптовалюте {symbol} и сделай профессиональный прогноз {period_text}.

Текущая цена: {current_price}

{historical_text}

Сделай детальный технический анализ и прогноз цены {symbol} {period_text}. Обязательно включи в анализ:

1. ТЕКУЩАЯ СИТУАЦИЯ - краткое описание текущего положения цены, рыночного контекста и настроений

2. ОБЪЕМЫ ТОРГОВ - детальный анализ объемов:
   - Сравни объемы за последние периоды (рост/падение)
   - Оцени аномалии объемов и их влияние на цену
   - Укажи дивергенции между ценой и объемом
   - Определи, подтверждают ли объемы текущий тренд

3. ТЕХНИЧЕСКИЙ АНАЛИЗ:
   - Определи текущий тренд (восходящий, нисходящий, боковой)
   - Выяви ключевые паттерны (двойное дно, голова и плечи, флаги и т.д.)
   - Проанализируй моментум и силу тренда
   - Укажи важные индикаторы (RSI, MACD, MA и т.д.)

4. КЛЮЧЕВЫЕ УРОВНИ:
   - Точные цифровые значения уровней поддержки (не менее 2-3)
   - Точные цифровые значения уровней сопротивления (не менее 2-3)
   - Зоны накопления и распределения
   - Психологически важные уровни цены

5. ПРОГНОЗ:
   - Конкретный ценовой диапазон для {period_text} с вероятностями
   - Несколько сценариев развития (бычий, медвежий, нейтральный) с процентными вероятностями
   - Потенциальные триггеры для каждого сценария
   - Ожидаемая волатильность

6. ТОРГОВЫЕ РЕКОМЕНДАЦИИ:
   - Конкретные точки входа с указанием цены
   - Рекомендуемые стоп-лоссы (точные значения)
   - Целевые уровни для тейк-профита (точные значения)
   - Оптимальное соотношение риск/доходность для сделок

Предоставь структурированный, точный и обоснованный прогноз, опираясь исключительно на технический анализ и представленные данные.
"""
        
        return prompt
    
    async def generate_forecast(
        self,
        symbol: str,
        period: str,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Генерация прогноза для криптовалюты
        
        :param symbol: Символ криптовалюты (например, "BTC", "ETH")
        :param period: Период прогноза ("hour", "day", "week")
        :param force_refresh: Принудительное обновление прогноза
        :return: Прогноз криптовалюты
        """
        try:
            # Нормализуем символ (добавляем USDT, если не указан)
            if not symbol.endswith("USDT"):
                symbol = f"{symbol}USDT"
            
            # Проверяем кэш (проверка символа произойдет на уровне bybit_client)
            cache_key = self._generate_cache_key(symbol, period)
            
            if not force_refresh and self.cache_manager.redis:
                cached_data = await self.cache_manager.redis.get(cache_key)
                if cached_data:
                    try:
                        forecast_data = json.loads(cached_data)
                        logger.info(f"Получен прогноз из кэша для {symbol}, период {period}")
                        return forecast_data
                    except json.JSONDecodeError:
                        logger.warning(f"Ошибка декодирования данных из кэша для {symbol}, период {period}")
            
            # Получаем рыночные данные
            market_data = await self.bybit_client.get_market_data(symbol)
            
            # Подготавливаем промпт для модели
            prompt = await self._prepare_forecast_prompt(market_data, period)
            
            # Получаем конфигурацию промпта
            prompt_config = self.prompts_config.get("default", {})
            
            # Генерируем прогноз с использованием модели
            forecast_text = await self.openrouter_client.generate_text(
                system_message=prompt_config.get("system_message", "Ты — эксперт по криптовалютам и техническому анализу."),
                user_message=prompt,
                max_tokens=prompt_config.get("max_tokens", 1500),
                temperature=prompt_config.get("temperature", 0.7)
            )
            
            # Формируем результат
            forecast_data = {
                "symbol": symbol,
                "period": period,
                "current_price": market_data["ticker"]["list"][0].get("lastPrice", "Неизвестно") if "list" in market_data["ticker"] and market_data["ticker"]["list"] else "Неизвестно",
                "forecast": forecast_text,
                "generated_at": datetime.now().isoformat(),
            }
            
            # Сохраняем в кэш с соответствующим TTL
            if self.cache_manager.redis:
                ttl = config.CRYPTO_FORECAST_CACHE_TTL.get(period, 3600)
                await self.cache_manager.redis.set(
                    cache_key,
                    json.dumps(forecast_data),
                    ex=ttl
                )
                logger.info(f"Прогноз для {symbol}, период {period} сохранен в кэш с TTL {ttl} сек.")
            
            return forecast_data
        
        except SymbolNotFoundError:
            # Просто пробрасываем ошибку выше, чтобы ее обработал API-слой
            raise
        except Exception as e:
            logger.error(f"Ошибка при генерации прогноза для {symbol}, период {period}: {e}", exc_info=True)
            raise
    
    async def get_available_cryptos(self) -> Dict[str, List[str]]:
        """
        Получение списка доступных криптовалют
        
        :return: Словарь со списками криптовалют
        """
        try:
            popular_cryptos = await self.bybit_client.get_popular_cryptos()
            all_symbols = await self.bybit_client.get_available_symbols()
            
            return {
                "popular": [symbol.replace("USDT", "") for symbol in popular_cryptos],
                "all": [symbol.replace("USDT", "") for symbol in all_symbols if symbol.endswith("USDT")]
            }
        
        except Exception as e:
            logger.error(f"Ошибка при получении списка доступных криптовалют: {e}", exc_info=True)
            raise 