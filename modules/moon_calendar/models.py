"""
Модели данных для лунного календаря
"""
from typing import Dict, List, Optional, Union
from pydantic import BaseModel

class MoonDayResponse(BaseModel):
    """Модель данных для лунного дня"""
    name: str
    start: str  # ISO format string
    end: str    # ISO format string
    info: str

class CalendarDayResponse(BaseModel):
    """Модель данных для дня календаря"""
    date: str  # ISO format string
    moon_phase: str
    moon_days: List[MoonDayResponse]
    recommendations: Dict[str, str]

class ApiResponse(BaseModel):
    """Общая модель ответа API"""
    date: str  # ISO формат даты
    response: Optional[str] = None  # Текст ответа AI
    error: Optional[str] = None  # Сообщение об ошибке, если есть
