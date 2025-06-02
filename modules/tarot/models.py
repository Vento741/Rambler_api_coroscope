"""
Модели данных для работы с Таро
"""
from typing import List, Optional
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
