"""
Эндпоинты для работы с картами Таро через OpenRouter
"""
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, HTTPException, Query, Path, Depends, Response
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import asyncio
import aiohttp
import os
import json
from datetime import datetime

from modules.tarot.models import ApiResponse, TarotReadingRequest, TarotCard, TarotSpread
from modules.tarot.openrouter_service import TarotOpenRouterService
from modules.tarot.data import get_all_cards, get_card_by_id, get_all_spreads, get_spread_by_id
from core.cache import CacheManager
from core.openrouter_client import OpenRouterClient
import config

router = APIRouter(prefix="/api/v1/tarot")

# Инициализация зависимостей
cache_manager = CacheManager(ttl_minutes=config.CACHE_TTL_MINUTES)

# Инициализация клиента OpenRouter
openrouter_client = OpenRouterClient(
    api_url=config.OPENROUTER_API_URL,
    api_keys=config.OPENROUTER_API_KEYS,
    models=config.OPENROUTER_MODELS,
    model_configs=config.OPENROUTER_MODEL_CONFIGS,
    model_api_keys=config.OPENROUTER_MODEL_API_KEYS,
    timeout=30  # Увеличенный таймаут для всех запросов
)

# Инициализация сервиса
tarot_service = TarotOpenRouterService(
    cache_manager=cache_manager,
    openrouter_client=openrouter_client,
    prompts_config=config.TAROT_PROMPTS
)

@router.get("/cards", response_model=Dict[str, Any])
async def get_cards():
    """
    Получение списка всех карт Таро
    
    Возвращает полный список карт Таро с их описаниями и значениями
    """
    cards = get_all_cards()
    
    # Возвращаем карты в формате, удобном для PuzzleBot
    result = {
        "success": True,
        "cards_count": len(cards),
        "cards": cards
    }
    
    return result

@router.get("/card/{card_id}", response_model=Dict[str, Any])
async def get_card(card_id: int = Path(..., description="ID карты Таро")):
    """
    Получение информации о конкретной карте Таро
    
    - **card_id**: ID карты Таро
    """
    card = get_card_by_id(card_id)
    if not card:
        raise HTTPException(
            status_code=404,
            detail=f"Карта с ID {card_id} не найдена"
        )
    
    # Возвращаем карту в формате, удобном для PuzzleBot
    result = {
        "success": True,
        "card": card
    }
    
    return result

@router.get("/spreads", response_model=Dict[str, Any])
async def get_spreads():
    """
    Получение списка всех доступных раскладов Таро
    
    Возвращает список раскладов с их описаниями и позициями карт
    """
    spreads = get_all_spreads()
    
    # Возвращаем расклады в формате, удобном для PuzzleBot
    result = {
        "success": True,
        "spreads_count": len(spreads),
        "spreads": spreads
    }
    
    return result

@router.get("/spread/{spread_id}", response_model=Dict[str, Any])
async def get_spread(spread_id: int = Path(..., description="ID расклада Таро")):
    """
    Получение информации о конкретном раскладе Таро
    
    - **spread_id**: ID расклада Таро
    """
    spread = get_spread_by_id(spread_id)
    if not spread:
        raise HTTPException(
            status_code=404,
            detail=f"Расклад с ID {spread_id} не найден"
        )
    
    # Возвращаем расклад в формате, удобном для PuzzleBot
    result = {
        "success": True,
        "spread": spread
    }
    
    return result

@router.post("/reading", response_model=Dict[str, Any])
async def get_reading(request: TarotReadingRequest):
    """
    Получение гадания на картах Таро
    
    - **spread_id**: ID выбранного расклада
    - **question**: Вопрос для гадания (опционально)
    - **user_type**: Тип пользователя (free/premium)
    """
    # Проверка типа пользователя
    if request.user_type not in ["free", "premium"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный тип пользователя. Допустимые значения: free, premium"
        )
    
    # Проверка существования расклада
    spread = get_spread_by_id(request.spread_id)
    if not spread:
        raise HTTPException(
            status_code=404,
            detail=f"Расклад с ID {request.spread_id} не найден"
        )
    
    # Получение гадания
    response = await tarot_service.get_tarot_reading(
        spread_id=request.spread_id,
        question=request.question,
        user_type=request.user_type
    )
    
    # Для PuzzleBot возвращаем результат в удобном формате
    if response.success:
        # Форматируем данные в одну структуру
        result = {
            "success": True,
            "reading_data": {
                "spread_id": request.spread_id,
                "spread_name": spread["name"],
                "question": request.question if request.question else "Общее гадание",
                "timestamp": datetime.now().isoformat(),
                "cards": response.data["cards"],
                "interpretation": response.data["interpretation"],
                "card_count": len(response.data["cards"])
            }
        }
        
        # Добавляем строку с URLs картинок для удобства PuzzleBot
        cards_urls = [card["card_image_url"] for card in response.data["cards"]]
        positions = [card["position_name"] for card in response.data["cards"]]
        
        result["reading_data"]["card_urls"] = ",".join(cards_urls)
        result["reading_data"]["positions"] = ",".join(positions)
        
        # Создаем HTML-строку для визуализации карт в PuzzleBot
        html_cards = ""
        for card in response.data["cards"]:
            html_cards += f'<div class="tarot-card">'
            html_cards += f'<img src="{card["card_image_url"]}" alt="{card["card_name"]}" />'
            html_cards += f'<div class="position">{card["position_name"]}</div>'
            html_cards += f'<div class="card-name">{card["card_name"]} {"(перевернутая)" if card["is_reversed"] else ""}</div>'
            html_cards += f'</div>'
        
        result["reading_data"]["html_cards"] = html_cards
        
        # Создаем текстовое представление для чатбота
        text_result = f"🔮 {spread['name']} 🔮\n\n"
        text_result += f"Вопрос: {request.question if request.question else 'Общее гадание'}\n\n"
        text_result += "Выпавшие карты:\n"
        
        for card in response.data["cards"]:
            text_result += f"• {card['position_name']}: {card['card_name']} {'(перевернутая)' if card['is_reversed'] else ''}\n"
        
        text_result += "\n🌟 Интерпретация 🌟\n\n"
        text_result += response.data["interpretation"]
        
        result["reading_data"]["text_result"] = text_result
        
        return result
    else:
        return {
            "success": False,
            "error": response.error
        }

@router.get("/reading", response_model=Dict[str, Any])
async def get_reading_get(
    spread_id: int = Query(..., description="ID выбранного расклада"),
    question: Optional[str] = Query(None, description="Вопрос для гадания"),
    user_type: str = Query("free", description="Тип пользователя (free/premium)")
):
    """
    Получение гадания на картах Таро (GET метод)
    
    - **spread_id**: ID выбранного расклада
    - **question**: Вопрос для гадания (опционально)
    - **user_type**: Тип пользователя (free/premium)
    """
    # Перенаправляем на POST-метод через объект запроса
    request = TarotReadingRequest(
        spread_id=spread_id,
        question=question,
        user_type=user_type
    )
    return await get_reading(request)

@router.get("/daily_card", response_model=Dict[str, Any])
async def get_daily_card(
    user_type: str = Query("free", description="Тип пользователя (free/premium)")
):
    """
    Получение карты дня
    
    - **user_type**: Тип пользователя (free/premium)
    """
    # Используем расклад на одну карту (ID = 1)
    request = TarotReadingRequest(
        spread_id=1,  # Предполагается, что расклад с ID=1 - это расклад "Карта дня"
        question="Карта дня",
        user_type=user_type
    )
    
    return await get_reading(request)

@router.get("/combined_data", response_model=Dict[str, Any])
async def get_combined_data(
    card_id: Optional[int] = Query(None, description="ID конкретной карты для детальной информации"),
    spread_id: Optional[int] = Query(None, description="ID конкретного расклада для детальной информации")
):
    """
    Получение комбинированных данных о картах и раскладах Таро
    
    - **card_id**: ID конкретной карты (опционально)
    - **spread_id**: ID конкретного расклада (опционально)
    
    Если не указаны card_id и spread_id, возвращает списки всех карт и раскладов
    Если указан card_id, возвращает детальную информацию о конкретной карте
    Если указан spread_id, возвращает детальную информацию о конкретном раскладе
    """
    result = {
        "success": True,
        "data_type": "combined",
        "timestamp": datetime.now().isoformat()
    }
    
    if card_id is not None:
        # Получаем информацию о конкретной карте
        card = get_card_by_id(card_id)
        if not card:
            raise HTTPException(
                status_code=404,
                detail=f"Карта с ID {card_id} не найдена"
            )
        result["data_type"] = "card_details"
        result["card"] = card
    elif spread_id is not None:
        # Получаем информацию о конкретном раскладе
        spread = get_spread_by_id(spread_id)
        if not spread:
            raise HTTPException(
                status_code=404,
                detail=f"Расклад с ID {spread_id} не найден"
            )
        result["data_type"] = "spread_details"
        result["spread"] = spread
    else:
        # Получаем базовую информацию обо всех картах и раскладах
        cards = get_all_cards()
        spreads = get_all_spreads()
        
        # Упрощаем данные для лаконичности ответа
        simple_cards = [{"id": card["id"], "name": card["name"], "arcana": card["arcana"], "suit": card["suit"]} for card in cards]
        simple_spreads = [{"id": spread["id"], "name": spread["name"], "card_count": spread["card_count"]} for spread in spreads]
        
        result["data_type"] = "basic_lists"
        result["cards"] = simple_cards
        result["spreads"] = simple_spreads
        result["cards_count"] = len(cards)
        result["spreads_count"] = len(spreads)
    
    return result

@router.get("/generate_card_image", response_class=Response)
async def generate_card_image(
    card_id: int = Query(..., description="ID карты Таро"),
    is_reversed: bool = Query(False, description="Перевернутая карта (true/false)")
):
    """
    Генерация изображения карты Таро
    
    - **card_id**: ID карты Таро
    - **is_reversed**: Перевернутая карта (true/false)
    
    Возвращает изображение карты Таро в формате JPEG.
    """
    # Получаем информацию о карте
    card = get_card_by_id(card_id)
    if not card:
        raise HTTPException(
            status_code=404,
            detail=f"Карта с ID {card_id} не найдена"
        )
    
    # Загружаем изображение карты
    try:
        response = requests.get(card["image_url"])
        if response.status_code != 200:
            raise HTTPException(
                status_code=500,
                detail="Не удалось загрузить изображение карты"
            )
        
        image_data = BytesIO(response.content)
        image = Image.open(image_data)
        
        # Если требуется перевернутое изображение
        if is_reversed:
            image = image.rotate(180)
        
        # Добавляем подпись с названием карты
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype("arial.ttf", 20)
        except:
            font = ImageFont.load_default()
        
        # Создаем полупрозрачную полосу для текста
        width, height = image.size
        overlay = Image.new('RGBA', (width, 40), (0, 0, 0, 180))
        image.paste(overlay, (0, height - 40), overlay)
        
        # Добавляем название карты
        title = f"{card['name']} ({('Перевернутая' if is_reversed else 'Прямая')})"
        draw.text((10, height - 35), title, fill=(255, 255, 255), font=font)
        
        # Сохраняем изображение в BytesIO и возвращаем
        output = BytesIO()
        image.save(output, format="JPEG", quality=95)
        output.seek(0)
        
        return Response(content=output.getvalue(), media_type="image/jpeg")
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке изображения: {str(e)}"
        )

@router.get("/generate_reading_image", response_class=Response)
async def generate_reading_image(
    spread_id: int = Query(..., description="ID расклада"),
    card_ids: str = Query(..., description="Список ID карт, разделенных запятыми"),
    reversed_flags: str = Query("", description="Список флагов 'перевернутости' карт (0/1), разделенных запятыми"),
    title: Optional[str] = Query(None, description="Заголовок для изображения")
):
    """
    Генерация изображения расклада Таро
    
    - **spread_id**: ID расклада
    - **card_ids**: Список ID карт, разделенных запятыми
    - **reversed_flags**: Список флагов 'перевернутости' карт (0/1), разделенных запятыми
    - **title**: Заголовок для изображения
    
    Возвращает изображение расклада Таро в формате JPEG.
    """
    # Получаем информацию о раскладе
    spread = get_spread_by_id(spread_id)
    if not spread:
        raise HTTPException(
            status_code=404,
            detail=f"Расклад с ID {spread_id} не найден"
        )
    
    # Парсим списки ID карт и флагов перевернутости
    card_id_list = [int(x) for x in card_ids.split(",")]
    
    if reversed_flags:
        reversed_list = [x == "1" for x in reversed_flags.split(",")]
    else:
        reversed_list = [False] * len(card_id_list)
    
    # Проверяем соответствие количества карт и флагов
    if len(card_id_list) != len(reversed_list):
        raise HTTPException(
            status_code=400,
            detail="Количество карт и флагов перевернутости должно совпадать"
        )
    
    # Проверяем соответствие количества карт и позиций в раскладе
    if len(card_id_list) != len(spread["positions"]):
        raise HTTPException(
            status_code=400,
            detail=f"Количество карт ({len(card_id_list)}) не соответствует количеству позиций в раскладе ({len(spread['positions'])})"
        )
    
    # Загружаем информацию о картах
    cards = []
    for card_id in card_id_list:
        card = get_card_by_id(card_id)
        if not card:
            raise HTTPException(
                status_code=404,
                detail=f"Карта с ID {card_id} не найдена"
            )
        cards.append(card)
    
    # Загружаем изображения карт
    card_images = []
    for card in cards:
        try:
            response = requests.get(card["image_url"])
            if response.status_code == 200:
                card_images.append(Image.open(BytesIO(response.content)))
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Не удалось загрузить изображение карты {card['name']}"
                )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при загрузке изображения: {str(e)}"
            )
    
    # Определяем размер и расположение карт в зависимости от типа расклада
    if spread_id == 1:  # Карта дня
        width, height = 600, 800
        card_width, card_height = 400, 600
        positions_xy = [(100, 100)]
    elif spread_id == 2:  # Расклад на три карты
        width, height = 1200, 600
        card_width, card_height = 300, 450
        positions_xy = [(100, 75), (450, 75), (800, 75)]
    elif spread_id == 3:  # Кельтский крест
        width, height = 1200, 1200
        card_width, card_height = 200, 300
        positions_xy = [
            (500, 450),  # Центр
            (500, 450),  # Пересечение (с поворотом)
            (500, 800),  # Основа
            (500, 100),  # Корона
            (150, 450),  # Прошлое
            (850, 450),  # Будущее
            (900, 800),  # Вы сами
            (900, 600),  # Внешние влияния
            (900, 400),  # Надежды/страхи
            (900, 200),  # Итог
        ]
    elif spread_id == 4:  # Расклад на отношения
        width, height = 1200, 800
        card_width, card_height = 200, 300
        positions_xy = [
            (200, 250),  # Вы
            (800, 250),  # Партнер
            (500, 100),  # Связь
            (300, 500),  # Препятствия
            (700, 500),  # Потенциал
        ]
    else:  # Общий случай
        card_width, card_height = 200, 300
        width = 150 + (card_width + 50) * len(card_images)
        height = 600
        positions_xy = [(150 + i * (card_width + 50), 150) for i in range(len(card_images))]
    
    # Создаем пустое изображение для коллажа
    collage = Image.new('RGB', (width, height), (30, 30, 50))
    draw = ImageDraw.Draw(collage)
    
    # Пытаемся загрузить шрифт
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        small_font = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Добавляем заголовок
    if title:
        draw.text((width//2 - len(title)*7, 30), title, fill=(255, 255, 255), font=font)
    else:
        draw.text((width//2 - len(spread["name"])*7, 30), spread["name"], fill=(255, 255, 255), font=font)
    
    # Размещаем карты
    for i, (card_img, is_reversed, position, (x, y)) in enumerate(zip(card_images, reversed_list, spread["positions"], positions_xy)):
        # Масштабируем карту
        card_img = card_img.resize((card_width, card_height))
        
        # Если карта перевернута или это вторая карта в Кельтском кресте
        if is_reversed:
            card_img = card_img.rotate(180)
        elif spread_id == 3 and i == 1:  # Кельтский крест, вторая карта (пересечение)
            card_img = card_img.rotate(90, expand=True)
        
        # Вставляем карту
        collage.paste(card_img, (x, y))
        
        # Добавляем название позиции
        position_name = position["name"]
        text_width = len(position_name) * 7
        draw.text((x + card_width//2 - text_width//2, y + card_height + 10), 
                 position_name, fill=(255, 255, 255), font=small_font)
    
    # Добавляем дату и время создания
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw.text((10, height - 30), f"Создано: {timestamp}", fill=(180, 180, 180), font=small_font)
    
    # Сохраняем коллаж в BytesIO и возвращаем
    output = BytesIO()
    collage.save(output, format="JPEG", quality=95)
    output.seek(0)
    
    return Response(content=output.getvalue(), media_type="image/jpeg") 