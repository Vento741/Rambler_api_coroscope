"""
Модели данных для работы с Таро
"""
from typing import List, Optional, Any, Dict, Union
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class TarotCard(BaseModel):
    """
    Модель карты Таро
    """
    card_name: str = Field(..., description="Название карты")
    position_name: str = Field(..., description="Название позиции карты в раскладе")
    position_description: Optional[str] = Field(None, description="Описание значения позиции")
    card_image_url: HttpUrl = Field(..., description="URL изображения карты")
    is_reversed: bool = Field(False, description="Признак перевернутой карты")


class TarotReading(BaseModel):
    """
    Модель гадания на Таро
    """
    spread_name: str = Field(..., description="Название расклада")
    question: str = Field(..., description="Вопрос для гадания")
    cards: List[TarotCard] = Field(..., description="Список карт в раскладе")
    interpretation: str = Field(..., description="Интерпретация расклада")
    timestamp: datetime = Field(default_factory=datetime.now, description="Время создания гадания")


class TarotPDFRequest(BaseModel):
    """
    Запрос на создание PDF с результатами гадания
    """
    reading: TarotReading = Field(..., description="Данные гадания")


class TarotPDFResponse(BaseModel):
    """
    Ответ на запрос создания PDF
    """
    success: bool = Field(..., description="Признак успешного создания PDF")
    error: Optional[str] = Field(None, description="Сообщение об ошибке")
    filename: Optional[str] = Field(None, description="Имя файла PDF")


class ApiResponse(BaseModel):
    """Общая модель ответа API для Таро"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cached: bool = False
    model: Optional[str] = None


class TarotReadingRequest(BaseModel):
    """
    Запрос на гадание на Таро
    """
    spread_id: int = Field(..., description="ID выбранного расклада")
    question: Optional[str] = Field(None, description="Вопрос для гадания")
    user_type: str = Field("free", description="Тип пользователя (free/premium)")


class TarotSpread(BaseModel):
    """
    Модель расклада Таро
    """
    id: int = Field(..., description="ID расклада")
    name: str = Field(..., description="Название расклада")
    description: str = Field(..., description="Описание расклада")
    positions: List[Dict[str, str]] = Field(..., description="Позиции карт в раскладе")
