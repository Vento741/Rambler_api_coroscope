"""
API эндпоинты для сервиса прогнозирования криптовалют
"""
import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse

from core.cache import CacheManager
from core.openrouter_client import OpenRouterClient
from modules.crypto_forecast.bybit_client import BybitClient
from modules.crypto_forecast.forecast_service import CryptoForecastService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/crypto",
    tags=["crypto_forecast"]
)

async def get_cache_manager(router_instance) -> CacheManager:
    """Получение экземпляра CacheManager из состояния приложения"""
    return router_instance.app.state.cache_manager

async def get_crypto_forecast_service(router_instance) -> CryptoForecastService:
    """Получение экземпляра CryptoForecastService из состояния приложения"""
    return router_instance.app.state.crypto_forecast_service

@router.get("/forecast/{symbol}")
async def get_crypto_forecast(
    symbol: str,
    period: str = Query("day", description="Период прогноза: hour, day, week"),
    user_type: str = Query("free", description="Тип пользователя: free, premium"),
    force_refresh: bool = Query(False, description="Принудительное обновление прогноза"),
    forecast_service: CryptoForecastService = Depends(get_crypto_forecast_service)
):
    """
    Получение прогноза для указанной криптовалюты
    
    - **symbol**: Символ криптовалюты (например, BTC, ETH, SOL)
    - **period**: Период прогноза (hour, day, week)
    - **user_type**: Тип пользователя (free, premium)
    - **force_refresh**: Принудительное обновление прогноза
    
    Возвращает прогноз для указанной криптовалюты на указанный период
    """
    try:
        # Проверяем корректность периода
        if period not in ["hour", "day", "week"]:
            raise HTTPException(status_code=400, detail="Некорректный период прогноза. Допустимые значения: hour, day, week")
        
        # Проверяем корректность типа пользователя
        if user_type not in ["free", "premium"]:
            user_type = "free"  # По умолчанию используем тип "free"
        
        # Генерируем прогноз
        forecast = await forecast_service.generate_forecast(
            symbol=symbol,
            period=period,
            user_type=user_type,
            force_refresh=force_refresh
        )
        
        return forecast
    
    except Exception as e:
        logger.error(f"Ошибка при получении прогноза для {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении прогноза: {str(e)}")

@router.get("/cryptos")
async def get_available_cryptos(
    forecast_service: CryptoForecastService = Depends(get_crypto_forecast_service)
):
    """
    Получение списка доступных криптовалют
    
    Возвращает список популярных и всех доступных криптовалют
    """
    try:
        cryptos = await forecast_service.get_available_cryptos()
        return cryptos
    
    except Exception as e:
        logger.error(f"Ошибка при получении списка криптовалют: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ошибка при получении списка криптовалют: {str(e)}")

@router.post("/puzzlebot/forecast")
async def puzzlebot_forecast(
    request: Dict[str, Any],
    forecast_service: CryptoForecastService = Depends(get_crypto_forecast_service)
):
    """
    Эндпоинт для интеграции с Telegram-ботом через puzzlebot.top
    
    Принимает запрос от puzzlebot.top и возвращает прогноз для указанной криптовалюты
    
    Ожидаемый формат запроса:
    {
        "crypto_symbol": "BTC",
        "forecast_period": "day",
        "user_type": "free"
    }
    """
    try:
        # Получаем параметры из запроса
        symbol = request.get("crypto_symbol", "BTC")
        period = request.get("forecast_period", "day")
        user_type = request.get("user_type", "free")
        
        # Преобразуем период из текстового формата в код
        period_mapping = {
            "Ближайший час": "hour",
            "На завтра": "day",
            "На неделю": "week"
        }
        
        # Если период указан в текстовом формате, преобразуем его
        if period in period_mapping:
            period = period_mapping[period]
        
        # Проверяем корректность периода
        if period not in ["hour", "day", "week"]:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Некорректный период прогноза. Допустимые значения: hour, day, week"
                }
            )
        
        # Генерируем прогноз
        forecast = await forecast_service.generate_forecast(
            symbol=symbol,
            period=period,
            user_type=user_type,
            force_refresh=False
        )
        
        # Формируем ответ для puzzlebot.top
        response = {
            "status": "success",
            "forecast": forecast["forecast"],
            "symbol": forecast["symbol"],
            "current_price": forecast["current_price"],
            "generated_at": forecast["generated_at"]
        }
        
        return response
    
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса от puzzlebot: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Ошибка при генерации прогноза: {str(e)}"
            }
        )

@router.post("/puzzlebot/welcome")
async def puzzlebot_welcome():
    """
    Эндпоинт для получения приветственного сообщения и инструкций
    
    Возвращает приветственное сообщение и инструкции для пользователя
    """
    try:
        welcome_message = {
            "status": "success",
            "welcome_message": "🚀 Добро пожаловать в Крипто-Прогноз!\n\nНаш сервис использует передовые технологии искусственного интеллекта для анализа рыночных данных и предоставления детальных прогнозов по криптовалютам.\n\n📊 Выберите криптовалюту для анализа:"
        }
        
        return welcome_message
    
    except Exception as e:
        logger.error(f"Ошибка при получении приветственного сообщения: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Ошибка при получении приветственного сообщения: {str(e)}"
            }
        )

@router.post("/puzzlebot/crypto_info")
async def puzzlebot_crypto_info(
    request: Dict[str, Any],
    forecast_service: CryptoForecastService = Depends(get_crypto_forecast_service)
):
    """
    Эндпоинт для получения информации о криптовалюте перед выбором периода прогноза
    
    Принимает запрос от puzzlebot.top и возвращает информацию о криптовалюте
    
    Ожидаемый формат запроса:
    {
        "crypto_symbol": "BTC"
    }
    """
    try:
        # Получаем параметры из запроса
        symbol = request.get("crypto_symbol", "BTC")
        
        # Нормализуем символ (добавляем USDT, если не указан)
        if not symbol.endswith("USDT"):
            symbol_with_usdt = f"{symbol}USDT"
        else:
            symbol_with_usdt = symbol
            symbol = symbol.replace("USDT", "")
        
        # Получаем данные о криптовалюте
        try:
            market_data = await forecast_service.bybit_client.get_market_data(symbol_with_usdt)
            
            # Получаем текущую цену и изменение за 24 часа
            current_price = "Неизвестно"
            price_change_24h = "Неизвестно"
            
            if "list" in market_data["ticker"] and market_data["ticker"]["list"] and len(market_data["ticker"]["list"]) > 0:
                ticker_data = market_data["ticker"]["list"][0]
                current_price = ticker_data.get("lastPrice", "Неизвестно")
                
                # Расчет изменения цены за 24 часа
                if "prevPrice24h" in ticker_data and ticker_data["prevPrice24h"] and "price24hPcnt" in ticker_data:
                    price_change_24h = ticker_data.get("price24hPcnt", "0")
                    # Преобразуем в проценты и добавляем знак
                    try:
                        price_change_pct = float(price_change_24h) * 100
                        price_change_24h = f"{'+' if price_change_pct >= 0 else ''}{price_change_pct:.2f}%"
                    except (ValueError, TypeError):
                        price_change_24h = "0.00%"
            
            # Определяем полное название криптовалюты
            crypto_names = {
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
                "SNX": "Synthetix"
            }
            
            full_name = crypto_names.get(symbol, symbol)
            
            # Формируем ответ
            response = {
                "status": "success",
                "symbol": symbol,
                "full_name": full_name,
                "current_price": current_price,
                "price_change_24h": price_change_24h,
                "message": f"💰 {symbol} - {full_name}\n\nТекущая цена: ${current_price}\n24ч изменение: {price_change_24h}\n\nВыберите период прогноза:"
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Ошибка при получении данных о криптовалюте {symbol}: {e}", exc_info=True)
            
            # В случае ошибки возвращаем базовую информацию
            crypto_names = {
                "BTC": "Bitcoin",
                "ETH": "Ethereum",
                "SOL": "Solana",
                "BNB": "Binance Coin",
                "XRP": "Ripple"
            }
            
            full_name = crypto_names.get(symbol, symbol)
            
            response = {
                "status": "success",
                "symbol": symbol,
                "full_name": full_name,
                "current_price": "Загрузка...",
                "price_change_24h": "Загрузка...",
                "message": f"💰 {symbol} - {full_name}\n\nЗагружаем актуальные данные...\n\nВыберите период прогноза:"
            }
            
            return response
    
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса информации о криптовалюте: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Ошибка при получении информации о криптовалюте: {str(e)}"
            }
        )

@router.post("/puzzlebot/disclaimer")
async def puzzlebot_disclaimer():
    """
    Эндпоинт для получения отказа от ответственности
    
    Возвращает текст отказа от ответственности для отображения после прогноза
    """
    try:
        disclaimer = {
            "status": "success",
            "disclaimer": "⚠️ ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ\n\nВсе прогнозы и аналитические данные предоставляются исключительно в информационных целях и не являются финансовым советом. Инвестиции в криптовалюты связаны с высоким риском, и вы можете потерять свои средства.\n\nПринимая решения о покупке или продаже активов, полагайтесь на собственный анализ и консультации с профессиональными финансовыми советниками.\n\nКоманда Крипто-Прогноза не несёт ответственности за любые финансовые потери, связанные с использованием предоставленной информации."
        }
        
        return disclaimer
    
    except Exception as e:
        logger.error(f"Ошибка при получении отказа от ответственности: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Ошибка при получении отказа от ответственности: {str(e)}"
            }
        )

@router.post("/puzzlebot/market_data")
async def puzzlebot_market_data(
    request: Dict[str, Any],
    forecast_service: CryptoForecastService = Depends(get_crypto_forecast_service)
):
    """
    Эндпоинт для получения рыночных данных о криптовалюте в формате JSON
    
    Принимает запрос от puzzlebot.top и возвращает данные о криптовалюте
    для дальнейшей передачи в модель
    
    Ожидаемый формат запроса:
    {
        "crypto_symbol": "BTC",
        "period": "day"
    }
    """
    try:
        # Получаем параметры из запроса
        symbol = request.get("crypto_symbol", "BTC")
        period = request.get("period", "day")
        
        # Преобразуем период из текстового формата в код
        period_mapping = {
            "Ближайший час": "hour",
            "На завтра": "day",
            "На неделю": "week"
        }
        
        # Если период указан в текстовом формате, преобразуем его
        if period in period_mapping:
            period = period_mapping[period]
        
        # Проверяем корректность периода
        if period not in ["hour", "day", "week"]:
            period = "day"  # По умолчанию используем дневной период
        
        # Нормализуем символ (добавляем USDT, если не указан)
        if not symbol.endswith("USDT"):
            symbol_with_usdt = f"{symbol}USDT"
        else:
            symbol_with_usdt = symbol
            symbol = symbol.replace("USDT", "")
        
        # Получаем данные о криптовалюте
        market_data = await forecast_service.bybit_client.get_market_data(symbol_with_usdt)
        
        # Получаем текущую цену
        current_price = "Неизвестно"
        if "list" in market_data["ticker"] and market_data["ticker"]["list"] and len(market_data["ticker"]["list"]) > 0:
            current_price = market_data["ticker"]["list"][0].get("lastPrice", "Неизвестно")
        
        # Формируем упрощенные данные для передачи в модель
        simplified_data = {
            "symbol": symbol,
            "current_price": current_price,
            "ticker": market_data["ticker"],
            "period": period
        }
        
        # Добавляем исторические данные в зависимости от периода
        if period == "hour":
            # Для часового прогноза добавляем только часовые данные (последние 24 часа)
            simplified_data["historical_data"] = {
                "1h": market_data["historical_data"].get("1h", [])[:24]
            }
        elif period == "day":
            # Для дневного прогноза добавляем часовые и 4-часовые данные
            simplified_data["historical_data"] = {
                "1h": market_data["historical_data"].get("1h", [])[:24],
                "4h": market_data["historical_data"].get("4h", [])[:24]
            }
        else:  # week
            # Для недельного прогноза добавляем все данные
            simplified_data["historical_data"] = {
                "1h": market_data["historical_data"].get("1h", [])[:24],
                "4h": market_data["historical_data"].get("4h", [])[:42],
                "1d": market_data["historical_data"].get("1d", [])[:30]
            }
        
        # Формируем ответ
        response = {
            "status": "success",
            "market_data": simplified_data
        }
        
        return response
    
    except Exception as e:
        logger.error(f"Ошибка при получении рыночных данных для {symbol}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"Ошибка при получении рыночных данных: {str(e)}"
            }
        ) 