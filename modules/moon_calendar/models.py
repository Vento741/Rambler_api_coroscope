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
    success: bool
    data: Optional[Union[CalendarDayResponse, str]] = None
    error: Optional[str] = None
    cached: bool = False
