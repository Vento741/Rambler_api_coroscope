"""
Модели данных для таро
"""
from typing import Dict, List, Optional
from pydantic import BaseModel

class TarotCard(BaseModel):
    """Модель данных для карты таро"""
    name: str
    position: str
    description: str
    image_url: Optional[str] = None

class TarotReading(BaseModel):
    """Модель данных для расклада таро"""
    date: str  # ISO format string
    spread_type: str
    cards: List[TarotCard]
    general_interpretation: str

class ApiResponse(BaseModel):
    """Общая модель ответа API"""
    success: bool
    data: Optional[TarotReading] = None
    error: Optional[str] = None
    cached: bool = False 