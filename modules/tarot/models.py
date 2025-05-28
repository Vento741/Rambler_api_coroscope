"""
Модели данных для работы с картами Таро
"""
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class TarotCard(BaseModel):
    """Модель данных для карты Таро"""
    id: int
    name: str
    arcana: str  # Старший или Младший Аркан
    suit: Optional[str] = None  # Масть (для Младших Арканов)
    image_url: str
    keywords_upright: List[str]
    keywords_reversed: List[str]
    description: str
    meaning_upright: str
    meaning_reversed: str


class TarotCardPosition(BaseModel):
    """Модель данных для позиции карты в раскладе"""
    position: int
    name: str
    description: str


class TarotSpread(BaseModel):
    """Модель данных для расклада Таро"""
    id: int
    name: str
    description: str
    positions: List[TarotCardPosition]
    card_count: int


class TarotReadingRequest(BaseModel):
    """Модель запроса на получение гадания"""
    spread_id: int
    question: Optional[str] = None
    user_type: str = "free"  # "free" или "premium"


class TarotReading(BaseModel):
    """Модель данных для результата гадания"""
    spread: TarotSpread
    cards: List[Dict[str, Any]]
    interpretation: str
    created_at: datetime = Field(default_factory=datetime.now)
    question: Optional[str] = None


class ApiResponse(BaseModel):
    """Общая модель ответа API"""
    success: bool
    data: Optional[Union[str, Dict[str, Any], List[Dict[str, Any]]]] = None
    error: Optional[str] = None
    model: Optional[str] = None
    cached: bool = False


class PuzzleBotResponse(BaseModel):
    """Модель ответа, оптимизированная для PuzzleBot"""
    success: bool = True
    api_result_text: str  # Единственная переменная, которую будет использовать PuzzleBot
    html_cards: Optional[str] = None  # HTML-представление карт
    card_urls: Optional[str] = None  # URL изображений карт через запятую
    positions: Optional[str] = None  # Названия позиций через запятую
    timestamp: Optional[str] = None
    spread_name: Optional[str] = None
    error: Optional[str] = None

    @classmethod
    def from_reading(cls, reading_data: Dict[str, Any]) -> "PuzzleBotResponse":
        """Создает ответ для PuzzleBot из результата гадания"""
        # Формируем текстовое представление для чатбота
        text_result = f"🔮 {reading_data['spread']['name']} 🔮\n\n"
        text_result += f"Вопрос: {reading_data.get('question', 'Общее гадание')}\n\n"
        text_result += "Выпавшие карты:\n"
        
        for card in reading_data['cards']:
            text_result += f"• {card['position_name']}: {card['card_name']} {'(перевернутая)' if card['is_reversed'] else ''}\n"
        
        text_result += "\n🌟 Интерпретация 🌟\n\n"
        text_result += reading_data['interpretation']
        
        # Создаем HTML-строку для визуализации карт
        html_cards = ""
        for card in reading_data['cards']:
            html_cards += f'<div class="tarot-card">'
            html_cards += f'<img src="{card["card_image_url"]}" alt="{card["card_name"]}" />'
            html_cards += f'<div class="position">{card["position_name"]}</div>'
            html_cards += f'<div class="card-name">{card["card_name"]} {"(перевернутая)" if card["is_reversed"] else ""}</div>'
            html_cards += f'</div>'
        
        # Добавляем строки с URLs картинок и позициями
        cards_urls = [card["card_image_url"] for card in reading_data['cards']]
        positions = [card["position_name"] for card in reading_data['cards']]
        
        return cls(
            success=True,
            api_result_text=text_result,
            html_cards=html_cards,
            card_urls=",".join(cards_urls),
            positions=",".join(positions),
            timestamp=datetime.now().isoformat(),
            spread_name=reading_data['spread']['name']
        )
    
    @classmethod
    def error_response(cls, error_message: str) -> "PuzzleBotResponse":
        """Создает ответ с ошибкой для PuzzleBot"""
        return cls(
            success=False,
            api_result_text=f"Ошибка: {error_message}",
            error=error_message
        ) 