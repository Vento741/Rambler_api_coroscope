"""
Модели данных для модуля карт Таро
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class TarotCard(BaseModel):
    """Модель для карты Таро"""
    id: int = Field(..., description="Уникальный идентификатор карты")
    name: str = Field(..., description="Название карты")
    suit: Optional[str] = Field(None, description="Масть карты (для Младших Арканов)")
    arcana: str = Field(..., description="Тип аркана (Старший/Младший)")
    image_url: str = Field(..., description="URL изображения карты")
    keywords_upright: List[str] = Field(..., description="Ключевые слова для прямого положения")
    keywords_reversed: List[str] = Field(..., description="Ключевые слова для перевернутого положения")
    description: str = Field(..., description="Общее описание карты")
    meaning_upright: str = Field(..., description="Значение карты в прямом положении")
    meaning_reversed: str = Field(..., description="Значение карты в перевернутом положении")


class TarotSpread(BaseModel):
    """Модель для расклада карт Таро"""
    id: int = Field(..., description="Уникальный идентификатор расклада")
    name: str = Field(..., description="Название расклада")
    description: str = Field(..., description="Описание расклада")
    positions: List[Dict[str, str]] = Field(..., description="Позиции карт в раскладе и их значения")
    card_count: int = Field(..., description="Количество карт в раскладе")


class TarotCardPosition(BaseModel):
    """Модель для позиции карты в раскладе"""
    position: int = Field(..., description="Номер позиции")
    name: str = Field(..., description="Название позиции")
    description: str = Field(..., description="Описание значения позиции")
    card: TarotCard = Field(..., description="Карта в данной позиции")
    is_reversed: bool = Field(False, description="Флаг перевернутой карты")


class TarotReadingRequest(BaseModel):
    """Модель для запроса гадания на Таро"""
    spread_id: int = Field(..., description="ID выбранного расклада")
    question: Optional[str] = Field(None, description="Вопрос для гадания")
    user_type: str = Field("free", description="Тип пользователя (free/premium)")


class TarotReading(BaseModel):
    """Модель для результата гадания на Таро"""
    spread: TarotSpread = Field(..., description="Информация о раскладе")
    cards: List[TarotCardPosition] = Field(..., description="Карты в раскладе")
    general_interpretation: str = Field(..., description="Общая интерпретация расклада")
    detailed_interpretation: Optional[str] = Field(None, description="Детальная интерпретация (для premium)")
    advice: str = Field(..., description="Совет на основе расклада")
    created_at: str = Field(..., description="Дата и время создания расклада")


class ApiResponse(BaseModel):
    """Модель для API-ответа"""
    success: bool = Field(..., description="Успешность запроса")
    data: Optional[Any] = Field(None, description="Данные ответа")
    error: Optional[str] = Field(None, description="Сообщение об ошибке")
    cached: bool = Field(False, description="Флаг использования кэша")
    model: Optional[str] = Field(None, description="Использованная модель ИИ") 