"""
Модели данных для модуля Книги Перемен (И-Цзин)
"""
from typing import Dict, Optional
from pydantic import BaseModel


class HexagramSection(BaseModel):
    """Секции гексаграммы"""
    Название: str
    Образный_ряд: str
    Внешний_и_внутренний_миры: str
    Определение: str
    Символ: str
    Линии_гексаграммы: str
    Вначале_девятка: Optional[str] = None
    Девятка_вторая: Optional[str] = None
    Девятка_третья: Optional[str] = None
    Девятка_четвертая: Optional[str] = None
    Девятка_пятая: Optional[str] = None
    Наверху_девятка: Optional[str] = None
    Все_девятки: Optional[str] = None


class HexagramData(BaseModel):
    """Модель данных гексаграммы"""
    number: int
    title: str
    description: str
    sections: Dict[str, str]


class RandomHexagramResponse(BaseModel):
    """Модель ответа с рандомной гексаграммой"""
    number: int
    title: str
    description: str
    image_url: str
    pdf_url: str
    sections: Dict[str, str]
    formatted_text: str


class ApiResponse(BaseModel):
    """Общая модель ответа API"""
    success: bool
    data: Optional[RandomHexagramResponse] = None
    error: Optional[str] = None 