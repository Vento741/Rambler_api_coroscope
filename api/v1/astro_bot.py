"""
Эндпоинты для работы с астрологическими данными через OpenRouter
"""
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Request

from modules.moon_calendar import MoonCalendarParser, ApiResponse
from modules.moon_calendar.openrouter_service import MoonCalendarOpenRouterService
from core.cache import CacheManager
from core.openrouter_client import OpenRouterClient
import config

router = APIRouter(prefix="/api/v1/astro_bot")

@router.get("/moon_day", response_model=ApiResponse)
async def get_moon_day(
    request: Request,
    user_type: str = Query("free", description="Тип пользователя: free или premium"),
    calendar_date: Optional[str] = Query(None, description="Дата в формате YYYY-MM-DD")
):
    """
    Получение данных лунного календаря с обработкой через OpenRouter
    
    - **user_type**: Тип пользователя (free/premium)
    - **calendar_date**: Дата в формате YYYY-MM-DD (если не указана, используется текущая дата)
    """
    openrouter_service: MoonCalendarOpenRouterService = request.app.state.moon_openrouter_service
    
    if user_type not in ["free", "premium"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный тип пользователя. Допустимые значения: free, premium"
        )
    
    try:
        if calendar_date:
            date_obj = datetime.strptime(calendar_date, "%Y-%m-%d").date()
        else:
            date_obj = date.today()
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Неверный формат даты. Используйте YYYY-MM-DD"
        )
    
    return await openrouter_service.get_moon_calendar_response(date_obj, user_type) 