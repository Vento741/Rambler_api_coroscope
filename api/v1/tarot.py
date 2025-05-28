"""
Эндпоинты для работы с картами Таро через OpenRouter
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query, Path, Depends, Response
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO
import asyncio
import aiohttp
import os
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

@router.get("/cards", response_model=List[TarotCard])
async def get_cards():
    """
    Получение списка всех карт Таро
    
    Возвращает полный список карт Таро с их описаниями и значениями
    """
    return get_all_cards()

@router.get("/cards/{card_id}", response_model=TarotCard)
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
    return card

@router.get("/spreads", response_model=List[TarotSpread])
async def get_spreads():
    """
    Получение списка всех доступных раскладов Таро
    
    Возвращает список раскладов с их описаниями и позициями карт
    """
    return get_all_spreads()

@router.get("/spreads/{spread_id}", response_model=TarotSpread)
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
    return spread

@router.post("/reading", response_model=ApiResponse)
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
    return await tarot_service.get_tarot_reading(
        spread_id=request.spread_id,
        question=request.question,
        user_type=request.user_type
    )

@router.get("/reading", response_model=ApiResponse)
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
    # Проверка типа пользователя
    if user_type not in ["free", "premium"]:
        raise HTTPException(
            status_code=400,
            detail="Неверный тип пользователя. Допустимые значения: free, premium"
        )
    
    # Проверка существования расклада
    spread = get_spread_by_id(spread_id)
    if not spread:
        raise HTTPException(
            status_code=404,
            detail=f"Расклад с ID {spread_id} не найден"
        )
    
    # Получение гадания
    return await tarot_service.get_tarot_reading(
        spread_id=spread_id,
        question=question,
        user_type=user_type
    )

async def download_image(session, url):
    """Загрузка изображения по URL"""
    async with session.get(url) as response:
        if response.status == 200:
            return await response.read()
        return None

@router.get("/collage", response_class=Response)
async def get_cards_collage(
    card_urls: List[str] = Query(..., description="Список URL изображений карт"),
    positions: List[str] = Query(..., description="Список названий позиций карт"),
    title: Optional[str] = Query(None, description="Заголовок коллажа"),
    spread_type: Optional[str] = Query(None, description="Тип расклада (для предустановленных шаблонов)")
):
    """
    Генерация коллажа из карт Таро
    
    - **card_urls**: Список URL изображений карт
    - **positions**: Список названий позиций карт (должен совпадать по длине с card_urls)
    - **title**: Заголовок коллажа (опционально)
    - **spread_type**: Тип расклада для предустановленных шаблонов (опционально)
    
    Возвращает изображение-коллаж с картами расклада.
    """
    if len(card_urls) != len(positions):
        raise HTTPException(
            status_code=400,
            detail="Количество URL карт должно совпадать с количеством позиций"
        )
    
    # Загружаем изображения карт асинхронно
    card_images = []
    async with aiohttp.ClientSession() as session:
        tasks = [download_image(session, url) for url in card_urls]
        results = await asyncio.gather(*tasks)
        
        for img_data in results:
            if img_data:
                try:
                    card_images.append(Image.open(BytesIO(img_data)))
                except Exception as e:
                    continue
    
    if not card_images:
        raise HTTPException(
            status_code=400,
            detail="Не удалось загрузить ни одного изображения карты"
        )
    
    # Определяем размер и расположение карт в зависимости от типа расклада
    if spread_type == "one_card":
        # Расклад на одну карту (карта дня)
        width, height = 600, 800
        card_width, card_height = 400, 600
        positions_xy = [(100, 100)]
        
    elif spread_type == "three_cards":
        # Расклад на три карты
        width, height = 1200, 600
        card_width, card_height = 300, 450
        positions_xy = [(100, 75), (450, 75), (800, 75)]
        
    elif spread_type == "celtic_cross":
        # Кельтский крест
        width, height = 1200, 1200
        card_width, card_height = 200, 300
        positions_xy = [
            (500, 450),  # Центр (позиция 1)
            (500, 450),  # Пересечение (позиция 2, с поворотом)
            (500, 800),  # Основа (позиция 3)
            (500, 100),  # Корона (позиция 4)
            (150, 450),  # Недавнее прошлое (позиция 5)
            (850, 450),  # Ближайшее будущее (позиция 6)
            (900, 800),  # Вы сами (позиция 7)
            (900, 600),  # Внешние влияния (позиция 8)
            (900, 400),  # Надежды/страхи (позиция 9)
            (900, 200),  # Итог (позиция 10)
        ]
        
    elif spread_type == "relationship":
        # Расклад на отношения
        width, height = 1200, 800
        card_width, card_height = 200, 300
        positions_xy = [
            (200, 250),   # Вы
            (800, 250),   # Партнер
            (500, 100),   # Связь
            (300, 500),   # Препятствия
            (700, 500),   # Потенциал
        ]
        
    else:
        # Общий случай - ряд карт
        card_width, card_height = 200, 300
        width = 150 + (card_width + 50) * len(card_images)
        height = 600
        positions_xy = [(150 + i * (card_width + 50), 150) for i in range(len(card_images))]
    
    # Создаем пустое изображение для коллажа
    collage = Image.new('RGB', (width, height), (30, 30, 50))
    draw = ImageDraw.Draw(collage)
    
    # Пытаемся загрузить шрифт, если не получается, используем стандартный
    try:
        font = ImageFont.truetype("arial.ttf", 24)
        small_font = ImageFont.truetype("arial.ttf", 18)
    except:
        font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Добавляем заголовок, если он есть
    if title:
        draw.text((width//2 - len(title)*7, 30), title, fill=(255, 255, 255), font=font)
    
    # Размещаем карты и их названия
    for i, (card, position, (x, y)) in enumerate(zip(card_images, positions, positions_xy[:len(card_images)])):
        # Масштабируем карту
        card = card.resize((card_width, card_height))
        
        # Если это Кельтский крест и позиция 2, поворачиваем карту на 90 градусов
        if spread_type == "celtic_cross" and i == 1:
            card = card.rotate(90, expand=True)
        
        # Вставляем карту в коллаж
        collage.paste(card, (x, y))
        
        # Добавляем название позиции
        text_width = len(position) * 7
        draw.text((x + card_width//2 - text_width//2, y + card_height + 10), 
                 position, fill=(255, 255, 255), font=small_font)
    
    # Добавляем дату и время создания
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    draw.text((10, height - 30), f"Создано: {timestamp}", fill=(180, 180, 180), font=small_font)
    
    # Сохраняем коллаж в BytesIO и возвращаем
    output = BytesIO()
    collage.save(output, format="JPEG", quality=95)
    output.seek(0)
    
    return Response(content=output.getvalue(), media_type="image/jpeg")

@router.get("/card-image/{card_id}")
async def get_card_image(
    card_id: int = Path(..., description="ID карты Таро"),
    is_reversed: bool = Query(False, description="Перевернутая карта (true/false)")
):
    """
    Получение изображения карты Таро, с возможностью отображения в перевернутом виде
    
    - **card_id**: ID карты Таро
    - **is_reversed**: Показать карту в перевернутом положении
    
    Возвращает изображение карты Таро.
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