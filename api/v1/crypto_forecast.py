"""
API эндпоинты для сервиса прогнозирования криптовалют
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, Request, Body
from fastapi.responses import JSONResponse

from core.cache import CacheManager
from core.openrouter_client import OpenRouterClient
from modules.crypto_forecast.bybit_client import BybitClient, SymbolNotFoundError
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
            force_refresh=force_refresh
        )
        
        return forecast
    
    except SymbolNotFoundError as e:
        logger.warning(f"Обработка SymbolNotFoundError для '{e.symbol}' в /forecast/{symbol}")
        available_cryptos = await forecast_service.get_available_cryptos()
        raise HTTPException(
            status_code=404,
            detail={"message": str(e), "available_symbols": available_cryptos}
        )
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
    data: Dict[str, Any] = Body(None),
    symbol: str = Query(None, description="Символ криптовалюты (например, BTC)"),
    period: str = Query(None, description="Период прогноза (hour, day, week)"),
    user_type: str = Query("free", description="Тип пользователя (free, premium)"),
    force_refresh: bool = Query(False, description="Принудительное обновление прогноза")
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
            error_message = "Некорректный период прогноза. Допустимые значения: Ближайший час, На завтра, На неделю."
            response = {
                "status": "error",
                "forecast": error_message,
                "symbol": symbol,
                "current_price": "N/A",
                "generated_at": datetime.now().isoformat()
            }
            return JSONResponse(
                status_code=200,
                content=response
            )
        
        # Генерируем прогноз
        forecast = await forecast_service.generate_forecast(
            symbol=symbol,
            period=period,
            force_refresh=force_refresh
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
    
    except SymbolNotFoundError as e:
        logger.warning(f"Обработка SymbolNotFoundError для '{e.symbol}' в puzzlebot/forecast")
        error_message = f"{str(e)} Пожалуйста, используйте одну из доступных криптовалют."
        response = {
            "status": "error",
            "forecast": error_message,
            "symbol": e.symbol,
            "current_price": "N/A",
            "generated_at": datetime.now().isoformat()
        }
        return JSONResponse(status_code=200, content=response)
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса от puzzlebot: {e}", exc_info=True)
        # Получаем параметры из запроса или из query параметров, чтобы вернуть символ в ответе
        if data:
            symbol = data.get("crypto_symbol", symbol or "BTC")
        else:
            symbol = symbol or "BTC"

        response = {
            "status": "error",
            "forecast": f"Внутренняя ошибка сервера при генерации прогноза. Попробуйте позже.",
            "symbol": symbol,
            "current_price": "N/A",
            "generated_at": datetime.now().isoformat()
        }
        return JSONResponse(
            status_code=200,
            content=response
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
    except SymbolNotFoundError as e:
        logger.warning(f"Обработка SymbolNotFoundError для '{e.symbol}' в puzzlebot/crypto_info")
        available_cryptos = await forecast_service.get_available_cryptos()
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": str(e), "available_symbols": available_cryptos}
        )
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
    except SymbolNotFoundError as e:
        logger.warning(f"Обработка SymbolNotFoundError для '{e.symbol}' в puzzlebot/market_data")
        available_cryptos = await forecast_service.get_available_cryptos()
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": str(e), "available_symbols": available_cryptos}
        )
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
    forecast_service = request.app.state.crypto_forecast_service
    action = data.get("action", "")
    symbol = data.get("symbol", "BTC").replace("USDT", "")
    period = data.get("period", "day")
    
    try:
        # Обрабатываем различные типы запросов
        if action == "get_forecast":
            force_refresh = data.get("force_refresh", False)
            
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
                return {
                    "status": "error",
                    "forecast": f"Неверный период: {period}. Допустимые значения: hour, day, week",
                    "symbol": symbol,
                    "period": period,
                    "current_price": "N/A",
                    "generated_at": datetime.now().isoformat()
                }
            
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
                "period": period,
                "current_price": forecast_data["current_price"],
                "generated_at": forecast_data["generated_at"]
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
    
    except SymbolNotFoundError as e:
        logger.warning(f"Обработка SymbolNotFoundError для '{e.symbol}' в bot_request (action: {action})")
        if action == "get_forecast":
            return {
                "status": "error",
                "forecast": f"{str(e)} Пожалуйста, выберите другую криптовалюту.",
                "symbol": e.symbol,
                "period": period,
                "current_price": "N/A",
                "generated_at": datetime.now().isoformat()
            }
        
        # Для других действий возвращаем стандартное сообщение об ошибке
        available_cryptos = await forecast_service.get_available_cryptos()
        return {
            "status": "error",
            "message": str(e),
            "available_symbols": available_cryptos
        }
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса от бота (action: {action}): {e}", exc_info=True)
        if action == "get_forecast":
            return {
                "status": "error",
                "forecast": f"Произошла внутренняя ошибка при генерации прогноза. Попробуйте позже.",
                "symbol": symbol,
                "period": period,
                "current_price": "N/A",
                "generated_at": datetime.now().isoformat()
            }
        return {
            "status": "error",
            "message": f"Произошла внутренняя ошибка: {str(e)}"
        } 