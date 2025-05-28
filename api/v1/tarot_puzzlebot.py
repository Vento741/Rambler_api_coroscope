"""
Эндпоинты для работы с картами Таро через PuzzleBot
Оптимизированная версия API для интеграции с PuzzleBot
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path, Response
from datetime import datetime
import json

from modules.tarot.models import PuzzleBotResponse
from modules.tarot.openrouter_service import TarotOpenRouterService
from modules.tarot.data import get_all_cards, get_card_by_id, get_all_spreads, get_spread_by_id
from core.cache import CacheManager
from core.openrouter_client import OpenRouterClient
import config

router = APIRouter(prefix="/api/v1/puzzlebot/tarot")

# Инициализация зависимостей
cache_manager = CacheManager(ttl_minutes=config.CACHE_TTL_MINUTES)

# Инициализация клиента OpenRouter
openrouter_client = OpenRouterClient(
    api_url=config.OPENROUTER_API_URL,
    api_keys=config.OPENROUTER_API_KEYS,
    models=config.OPENROUTER_MODELS,
    model_configs=config.OPENROUTER_MODEL_CONFIGS,
    model_api_keys=config.OPENROUTER_MODEL_API_KEYS,
    timeout=30
)

# Инициализация сервиса
tarot_service = TarotOpenRouterService(
    cache_manager=cache_manager,
    openrouter_client=openrouter_client,
    prompts_config=config.TAROT_PROMPTS
)

@router.get("/reading", response_model=Dict[str, Any])
async def get_puzzlebot_reading(
    spread_id: int = Query(..., description="ID выбранного расклада"),
    question: Optional[str] = Query(None, description="Вопрос для гадания"),
    user_type: str = Query("free", description="Тип пользователя (free/premium)")
):
    """
    Получение гадания на картах Таро для PuzzleBot
    
    Возвращает результат в формате, оптимизированном для PuzzleBot с одной переменной.
    
    - **spread_id**: ID выбранного расклада
    - **question**: Вопрос для гадания (опционально)
    - **user_type**: Тип пользователя (free/premium)
    """
    try:
        # Проверка типа пользователя
        if user_type not in ["free", "premium"]:
            return {"api_result_text": f"Ошибка: Неверный тип пользователя. Допустимые значения: free, premium"}
        
        # Проверка существования расклада
        spread = get_spread_by_id(spread_id)
        if not spread:
            return {"api_result_text": f"Ошибка: Расклад с ID {spread_id} не найден"}
        
        # Получение гадания
        response = await tarot_service.get_tarot_reading(
            spread_id=spread_id,
            question=question,
            user_type=user_type
        )
        
        # Если успешно получили результат
        if response.success:
            # Формируем данные в структуру, удобную для PuzzleBot
            reading_data = {
                "spread_id": spread_id,
                "spread_name": spread["name"],
                "question": question if question else "Общее гадание",
                "timestamp": datetime.now().isoformat(),
                "cards": response.data["cards"],
                "interpretation": response.data["interpretation"],
                "card_count": len(response.data["cards"])
            }
            
            # Добавляем строки с URLs картинок и позициями для удобства PuzzleBot
            cards_urls = [card["card_image_url"] for card in response.data["cards"]]
            positions = [card["position_name"] for card in response.data["cards"]]
            
            reading_data["card_urls"] = ",".join(cards_urls)
            reading_data["positions"] = ",".join(positions)
            
            # Создаем HTML-строку для визуализации карт в PuzzleBot
            html_cards = ""
            for card in response.data["cards"]:
                html_cards += f'<div class="tarot-card">'
                html_cards += f'<img src="{card["card_image_url"]}" alt="{card["card_name"]}" />'
                html_cards += f'<div class="position">{card["position_name"]}</div>'
                html_cards += f'<div class="card-name">{card["card_name"]} {"(перевернутая)" if card["is_reversed"] else ""}</div>'
                html_cards += f'</div>'
            
            reading_data["html_cards"] = html_cards
            
            # Создаем текстовое представление для чатбота
            text_result = f"🔮 {spread['name']} 🔮\n\n"
            text_result += f"Вопрос: {question if question else 'Общее гадание'}\n\n"
            text_result += "Выпавшие карты:\n"
            
            for card in response.data["cards"]:
                text_result += f"• {card['position_name']}: {card['card_name']} {'(перевернутая)' if card['is_reversed'] else ''}\n"
            
            text_result += "\n🌟 Интерпретация 🌟\n\n"
            text_result += response.data["interpretation"]
            
            reading_data["text_result"] = text_result
            
            # Возвращаем ТОЛЬКО текстовый результат для переменной в PuzzleBot
            return {"api_result_text": text_result}
        else:
            return {"api_result_text": f"Ошибка: {response.error}"}
    except Exception as e:
        return {"api_result_text": f"Ошибка: {str(e)}"}

@router.get("/card/{card_id}", response_model=Dict[str, Any])
async def get_puzzlebot_card(
    card_id: int = Path(..., description="ID карты Таро")
):
    """
    Получение информации о карте Таро для PuzzleBot
    
    - **card_id**: ID карты Таро
    """
    try:
        card = get_card_by_id(card_id)
        if not card:
            return {"api_result_text": f"Ошибка: Карта с ID {card_id} не найдена"}
        
        # Формируем текстовое представление карты
        text_result = f"🔮 {card['name']} 🔮\n\n"
        text_result += f"Аркан: {card['arcana']}"
        if card['suit']:
            text_result += f", Масть: {card['suit']}\n\n"
        else:
            text_result += "\n\n"
        
        text_result += f"{card['description']}\n\n"
        
        text_result += "🌞 В прямом положении 🌞\n"
        text_result += f"{card['meaning_upright']}\n"
        text_result += f"Ключевые слова: {', '.join(card['keywords_upright'])}\n\n"
        
        text_result += "🌚 В перевернутом положении 🌚\n"
        text_result += f"{card['meaning_reversed']}\n"
        text_result += f"Ключевые слова: {', '.join(card['keywords_reversed'])}"
        
        return {"api_result_text": text_result}
    except Exception as e:
        return {"api_result_text": f"Ошибка: {str(e)}"}

@router.get("/spread/{spread_id}", response_model=Dict[str, Any])
async def get_puzzlebot_spread(
    spread_id: int = Path(..., description="ID расклада Таро")
):
    """
    Получение информации о раскладе Таро для PuzzleBot
    
    - **spread_id**: ID расклада Таро
    """
    try:
        spread = get_spread_by_id(spread_id)
        if not spread:
            return {"api_result_text": f"Ошибка: Расклад с ID {spread_id} не найден"}
        
        # Формируем текстовое представление расклада
        text_result = f"🔮 {spread['name']} 🔮\n\n"
        text_result += f"{spread['description']}\n\n"
        text_result += f"Количество карт: {spread['card_count']}\n\n"
        
        text_result += "Позиции карт:\n"
        for position in spread['positions']:
            text_result += f"• {position['name']}: {position['description']}\n"
        
        return {"api_result_text": text_result}
    except Exception as e:
        return {"api_result_text": f"Ошибка: {str(e)}"}

@router.get("/daily_card", response_model=Dict[str, Any])
async def get_puzzlebot_daily_card(
    user_type: str = Query("free", description="Тип пользователя (free/premium)")
):
    """
    Получение карты дня для PuzzleBot
    
    - **user_type**: Тип пользователя (free/premium)
    """
    # Используем расклад на одну карту (ID = 1)
    return await get_puzzlebot_reading(
        spread_id=1,  # Предполагается, что расклад с ID=1 - это расклад "Карта дня"
        question="Карта дня",
        user_type=user_type
    )

@router.get("/spreads_list", response_model=Dict[str, Any])
async def get_puzzlebot_spreads_list():
    """
    Получение списка всех раскладов Таро для PuzzleBot
    """
    try:
        spreads = get_all_spreads()
        
        # Формируем текстовое представление списка раскладов
        text_result = "🔮 Доступные расклады Таро 🔮\n\n"
        
        for spread in spreads:
            text_result += f"ID: {spread['id']} - {spread['name']} ({spread['card_count']} карт)\n"
            text_result += f"{spread['description']}\n\n"
        
        return {"api_result_text": text_result}
    except Exception as e:
        return {"api_result_text": f"Ошибка: {str(e)}"}

@router.get("/cards_list", response_model=Dict[str, Any])
async def get_puzzlebot_cards_list(
    arcana: Optional[str] = Query(None, description="Фильтр по типу аркана (Старший/Младший)"),
    suit: Optional[str] = Query(None, description="Фильтр по масти (для Младших арканов)")
):
    """
    Получение списка карт Таро для PuzzleBot
    
    - **arcana**: Фильтр по типу аркана (Старший/Младший)
    - **suit**: Фильтр по масти (для Младших арканов)
    """
    try:
        cards = get_all_cards()
        
        # Применяем фильтры
        if arcana:
            cards = [card for card in cards if card["arcana"].lower() == arcana.lower()]
        
        if suit:
            cards = [card for card in cards if card.get("suit") and card["suit"].lower() == suit.lower()]
        
        # Формируем текстовое представление списка карт
        if arcana and suit:
            title = f"🔮 Карты Таро: {arcana} аркан, масть {suit} 🔮"
        elif arcana:
            title = f"🔮 Карты Таро: {arcana} аркан 🔮"
        elif suit:
            title = f"🔮 Карты Таро: масть {suit} 🔮"
        else:
            title = "🔮 Все карты Таро 🔮"
        
        text_result = f"{title}\n\n"
        
        for card in cards:
            text_result += f"ID: {card['id']} - {card['name']}"
            if card.get("suit"):
                text_result += f" ({card['suit']})"
            text_result += "\n"
        
        return {"api_result_text": text_result}
    except Exception as e:
        return {"api_result_text": f"Ошибка: {str(e)}"} 