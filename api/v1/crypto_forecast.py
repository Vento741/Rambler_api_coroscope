"""
API эндпоинты для сервиса прогнозирования криптовалют
"""
import logging
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request, Body
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
@router.get("/puzzlebot/forecast")
async def puzzlebot_forecast(
    request: Request,
    data: Dict[str, Any] = None,
    symbol: str = Query(None, description="Символ криптовалюты (например, BTC)"),
    period: str = Query(None, description="Период прогноза (hour, day, week)"),
    user_type: str = Query("free", description="Тип пользователя (free, premium)")
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
        # Получаем сервис из состояния приложения
        forecast_service = request.app.state.crypto_forecast_service
        
        # Получаем параметры из запроса или из query параметров
        if data:
            symbol = data.get("crypto_symbol", symbol or "BTC")
            period = data.get("forecast_period", period or "day")
            user_type = data.get("user_type", user_type)
        else:
            symbol = symbol or "BTC"
            period = period or "day"
        
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
@router.get("/puzzlebot/welcome")
async def get_welcome_message(request: Request) -> Dict[str, Any]:
    """
    Получение приветственного сообщения
    """
    try:
        return {
            "status": "success",
            "message": "Добро пожаловать в API прогнозов криптовалют!"
        }
    except Exception as e:
        logger.error(f"Ошибка при получении приветственного сообщения: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/puzzlebot/forecast")
async def get_forecast(
    request: Request,
    symbol: str = Query(..., description="Символ криптовалюты (например, BTC)"),
    period: str = Query("day", description="Период прогноза (hour, day, week)"),
    force_refresh: bool = Query(False, description="Принудительное обновление прогноза")
) -> Dict[str, Any]:
    """
    Получение прогноза для криптовалюты
    """
    try:
        forecast_service = request.app.state.crypto_forecast_service
        
        # Проверяем период
        if period not in ["hour", "day", "week"]:
            raise HTTPException(status_code=400, detail=f"Неверный период: {period}. Допустимые значения: hour, day, week")
        
        # Нормализуем символ (убираем USDT, если есть)
        symbol = symbol.replace("USDT", "")
        
        # Генерируем прогноз
        forecast_data = await forecast_service.generate_forecast(
            symbol=f"{symbol}USDT",
            period=period,
            force_refresh=force_refresh
        )
        
        # Формируем результат
        result = {
            "status": "success",
            "forecast": forecast_data["forecast"]
        }
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении прогноза для {symbol}, период {period}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/puzzlebot/crypto_info")
async def get_crypto_info(
    request: Request,
    crypto_symbol: str = Query(..., description="Символ криптовалюты (например, BTC)")
) -> Dict[str, Any]:
    """
    Получение информации о криптовалюте
    """
    try:
        forecast_service = request.app.state.crypto_forecast_service
        
        # Нормализуем символ (убираем USDT, если есть)
        symbol = crypto_symbol.replace("USDT", "")
        
        # Получаем рыночные данные
        market_data = await forecast_service.bybit_client.get_market_data(f"{symbol}USDT")
        
        # Формируем результат
        result = {
            "status": "success",
            "symbol": symbol,
            "full_name": forecast_service.bybit_client.get_crypto_full_name(symbol),
            "current_price": market_data["ticker"]["list"][0].get("lastPrice", "Неизвестно") if "list" in market_data["ticker"] and market_data["ticker"]["list"] else "Неизвестно",
            "price_change_24h": market_data["ticker"]["list"][0].get("price24hPcnt", "Неизвестно") if "list" in market_data["ticker"] and market_data["ticker"]["list"] else "Неизвестно"
        }
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении информации о криптовалюте {crypto_symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/puzzlebot/disclaimer")
@router.get("/puzzlebot/disclaimer")
async def get_disclaimer(request: Request) -> Dict[str, Any]:
    """
    Получение отказа от ответственности
    """
    try:
        disclaimer = """⚠️ ОТКАЗ ОТ ОТВЕТСТВЕННОСТИ

Все прогнозы и аналитические данные предоставляются исключительно в информационных целях и не являются финансовым советом. Криптовалютный рынок крайне волатилен, и никакой анализ не может гарантировать точное предсказание будущих цен.

Принимая решения о покупке или продаже криптовалют, полагайтесь на собственный анализ и консультации с профессиональными финансовыми советниками. Автор и разработчики этого сервиса не несут ответственности за любые финансовые потери, связанные с использованием предоставленной информации.

Торговля криптовалютами сопряжена с высоким риском и может привести к потере значительной части или всех ваших инвестиций.
"""
        
        return {
            "status": "success",
            "disclaimer": disclaimer
        }
    except Exception as e:
        logger.error(f"Ошибка при получении отказа от ответственности: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/puzzlebot/market_data")
async def get_market_data(
    request: Request,
    crypto_symbol: str = Query(..., description="Символ криптовалюты (например, BTC)"),
    period: str = Query("day", description="Период для исторических данных (hour, day, week)")
) -> Dict[str, Any]:
    """
    Получение рыночных данных для криптовалюты
    """
    try:
        forecast_service = request.app.state.crypto_forecast_service
        
        # Нормализуем символ (убираем USDT, если есть)
        symbol = crypto_symbol.replace("USDT", "")
        
        # Получаем рыночные данные
        market_data = await forecast_service.bybit_client.get_market_data(f"{symbol}USDT")
        
        # Формируем результат
        result = {
            "status": "success",
            "market_data": market_data
        }
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении рыночных данных для {crypto_symbol}, период {period}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/puzzlebot/bot_request")
async def process_bot_request(
    request: Request,
    data: Dict[str, Any] = Body(...),
) -> Dict[str, Any]:
    """
    Обработка запроса от бота
    """
    try:
        forecast_service = request.app.state.crypto_forecast_service
        
        # Получаем параметры из запроса
        action = data.get("action", "")
        
        # Обрабатываем различные типы запросов
        if action == "get_forecast":
            symbol = data.get("symbol", "")
            period = data.get("period", "day")
            force_refresh = data.get("force_refresh", False)
            
            # Проверяем период
            if period not in ["hour", "day", "week"]:
                return {
                    "status": "error",
                    "message": f"Неверный период: {period}. Допустимые значения: hour, day, week"
                }
            
            # Нормализуем символ (убираем USDT, если есть)
            symbol = symbol.replace("USDT", "")
            
            # Генерируем прогноз
            forecast_data = await forecast_service.generate_forecast(
                symbol=f"{symbol}USDT",
                period=period,
                force_refresh=force_refresh
            )
            
            # Формируем результат
            return {
                "status": "success",
                "forecast": forecast_data["forecast"],
                "symbol": symbol,
                "period": period
            }
        
        elif action == "get_available_cryptos":
            # Получаем доступные криптовалюты
            cryptos = await forecast_service.get_available_cryptos()
            
            # Формируем результат
            return {
                "status": "success",
                "cryptos": cryptos
            }
        
        else:
            return {
                "status": "error",
                "message": f"Неизвестное действие: {action}"
            }
    
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса от бота: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        } 