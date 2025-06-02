"""
Эндпоинты для работы с картами Таро через PuzzleBot
Оптимизированная версия API для интеграции с PuzzleBot
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Path, Response
from datetime import datetime, date, time, timedelta
import json
import random

from modules.tarot.models import PuzzleBotResponse
from modules.tarot.openrouter_service import TarotOpenRouterService
from modules.tarot.data import get_all_cards, get_card_by_id, get_all_spreads, get_spread_by_id
from modules.tarot.pdf_generator import TarotPDFGenerator
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

# Инициализация генератора PDF
pdf_generator = TarotPDFGenerator()

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
            
            # Сохраняем данные в кэш для последующего использования при генерации PDF
            cache_key = f"tarot_reading_data_{spread_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            await cache_manager.set(cache_key, reading_data, ttl_minutes=60)  # Сохраняем на 1 час
            
            # Добавляем ссылку на PDF в текстовый результат
            pdf_link = f"/api/v1/puzzlebot/tarot/reading/pdf?cache_key={cache_key}"
            text_result += f"\n\n📄 [Скачать результат в PDF]({pdf_link})"
            
            # Возвращаем ТОЛЬКО текстовый результат для переменной в PuzzleBot
            return {"api_result_text": text_result}
        else:
            return {"api_result_text": f"Ошибка: {response.error}"}
    except Exception as e:
        return {"api_result_text": f"Ошибка: {str(e)}"}

@router.get("/reading/pdf", response_class=Response)
async def get_reading_pdf(
    cache_key: str = Query(..., description="Ключ кэша с данными гадания")
):
    """
    Получение PDF-файла с результатами гадания
    
    - **cache_key**: Ключ кэша с данными гадания
    """
    try:
        # Получаем данные гадания из кэша
        reading_data = await cache_manager.get(cache_key)
        if not reading_data:
            raise HTTPException(
                status_code=404,
                detail="Данные гадания не найдены или устарели. Пожалуйста, сделайте новое гадание."
            )
        
        # Генерируем PDF
        pdf_bytes = await pdf_generator.generate_reading_pdf(reading_data)
        
        # Формируем имя файла
        spread_name = reading_data.get("spread_name", "Таро").replace(" ", "_")
        filename = f"tarot_{spread_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        
        # Возвращаем PDF-файл
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при генерации PDF: {str(e)}"
        )

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
        if card.get('suit'):
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
    try:
        # Проверяем тип пользователя
        if user_type not in ["free", "premium"]:
            return {"api_result_text": f"Ошибка: Неверный тип пользователя. Допустимые значения: free, premium"}
        
        # Получаем текущую дату
        today = date.today()
        
        # Проверяем, есть ли карта дня в кэше
        cache_key = f"daily_card_{today.isoformat()}"
        daily_card_data = await cache_manager.get(cache_key)
        
        # Если карты дня нет в кэше или это первый запрос за день
        if not daily_card_data:
            # Генерируем новую карту дня
            all_cards = get_all_cards()
            if not all_cards:
                return {"api_result_text": "Ошибка: Не удалось получить список карт Таро"}
            
            # Выбираем случайную карту
            daily_card = random.choice(all_cards)
            # Определяем случайно положение карты (прямое или перевернутое)
            is_reversed = random.choice([True, False])
            
            # Создаем данные для карты дня
            daily_card_data = {
                "card": daily_card,
                "is_reversed": is_reversed,
                "date": today.isoformat(),
                "premium_reading": None,
                "free_reading": None
            }
            
            # Сохраняем в кэш до конца дня
            tomorrow = today + timedelta(days=1)
            midnight = datetime.combine(tomorrow, time.min)
            seconds_until_midnight = (midnight - datetime.now()).total_seconds()
            ttl_minutes = max(1, seconds_until_midnight // 60)
            
            await cache_manager.set(cache_key, daily_card_data, ttl_minutes=ttl_minutes)
        
        # Теперь у нас есть данные карты дня
        card = daily_card_data["card"]
        is_reversed = daily_card_data["is_reversed"]
        
        # Проверяем, есть ли уже интерпретация для данного типа пользователя
        interpretation_key = f"{'premium_reading' if user_type == 'premium' else 'free_reading'}"
        
        if daily_card_data.get(interpretation_key) is None:
            # Генерируем интерпретацию через OpenRouter
            question = f"Карта дня: {card['name']} {'(перевернутая)' if is_reversed else '(прямая)'}."
            
            response = await tarot_service.get_tarot_reading(
                spread_id=1,  # ID расклада "Карта дня"
                question=question,
                user_type=user_type,
                fixed_cards=[{"card_id": card["id"], "is_reversed": is_reversed}]
            )
            
            if response.success:
                # Сохраняем интерпретацию в кэш
                daily_card_data[interpretation_key] = response.data["interpretation"]
                await cache_manager.set(cache_key, daily_card_data, ttl_minutes=ttl_minutes)
            else:
                return {"api_result_text": f"Ошибка: {response.error}"}
        
        # Формируем текстовое представление карты дня
        text_result = f"🔮 Карта дня - {today.strftime('%d.%m.%Y')} 🔮\n\n"
        text_result += f"Карта: {card['name']} {'(перевернутая)' if is_reversed else '(прямая)'}\n\n"
        
        # Добавляем описание карты
        text_result += f"{card['description']}\n\n"
        
        # Добавляем значение карты в соответствующем положении
        if is_reversed:
            text_result += f"В перевернутом положении: {card['meaning_reversed']}\n"
            text_result += f"Ключевые слова: {', '.join(card['keywords_reversed'])}\n\n"
        else:
            text_result += f"В прямом положении: {card['meaning_upright']}\n"
            text_result += f"Ключевые слова: {', '.join(card['keywords_upright'])}\n\n"
        
        # Добавляем интерпретацию
        text_result += "🌟 Интерпретация 🌟\n\n"
        text_result += daily_card_data[interpretation_key]
        
        # Формируем данные для PDF
        reading_data = {
            "spread_id": 1,
            "spread_name": "Карта дня",
            "question": f"Карта дня на {today.strftime('%d.%m.%Y')}",
            "timestamp": datetime.now().isoformat(),
            "cards": [{
                "card_id": card["id"],
                "card_name": card["name"],
                "card_image_url": card["image_url"],
                "is_reversed": is_reversed,
                "position_name": "Карта дня",
                "position_description": "Энергия и влияние дня"
            }],
            "interpretation": daily_card_data[interpretation_key],
            "card_count": 1
        }
        
        # Сохраняем данные в кэш для последующего использования при генерации PDF
        pdf_cache_key = f"tarot_daily_card_{today.isoformat()}_{user_type}"
        await cache_manager.set(pdf_cache_key, reading_data, ttl_minutes=ttl_minutes)
        
        # Добавляем ссылку на PDF в текстовый результат
        pdf_link = f"/api/v1/puzzlebot/tarot/reading/pdf?cache_key={pdf_cache_key}"
        text_result += f"\n\n📄 [Скачать результат в PDF]({pdf_link})"
        
        return {"api_result_text": text_result}
    except Exception as e:
        return {"api_result_text": f"Ошибка: {str(e)}"}

@router.get("/daily_card/free", response_model=Dict[str, Any])
async def get_puzzlebot_daily_card_free():
    """Получение карты дня для бесплатных пользователей"""
    return await get_puzzlebot_daily_card(user_type="free")

@router.get("/daily_card/premium", response_model=Dict[str, Any])
async def get_puzzlebot_daily_card_premium():
    """Получение карты дня для премиум-пользователей"""
    return await get_puzzlebot_daily_card(user_type="premium")

@router.get("/spreads_list", response_model=Dict[str, Any])
async def get_puzzlebot_spreads_list():
    """
    Получение списка всех доступных раскладов Таро для PuzzleBot
    """
    try:
        spreads = get_all_spreads()
        
        # Формируем текстовое представление списка раскладов
        text_result = "🔮 Доступные расклады Таро 🔮\n\n"
        
        for spread in spreads:
            text_result += f"{spread['id']}. **{spread['name']}** ({spread['card_count']} карт)\n"
            text_result += f"   {spread['description']}\n\n"
        
        text_result += "Для получения подробной информации о раскладе используйте команду /spread с указанием ID расклада."
        
        return {"api_result_text": text_result}
    except Exception as e:
        return {"api_result_text": f"Ошибка: {str(e)}"}

@router.get("/cards_list", response_model=Dict[str, Any])
async def get_puzzlebot_cards_list(
    arcana: Optional[str] = Query(None, description="Фильтр по типу аркана (Старший/Младший)"),
    suit: Optional[str] = Query(None, description="Фильтр по масти (для Младших арканов)")
):
    """
    Получение списка карт Таро для PuzzleBot с возможностью фильтрации
    
    - **arcana**: Фильтр по типу аркана (Старший/Младший)
    - **suit**: Фильтр по масти (для Младших арканов)
    """
    try:
        all_cards = get_all_cards()
        
        # Применяем фильтры, если они указаны
        filtered_cards = all_cards
        
        if arcana:
            filtered_cards = [card for card in filtered_cards if card.get('arcana', '').lower() == arcana.lower()]
        
        if suit:
            filtered_cards = [card for card in filtered_cards if card.get('suit', '').lower() == suit.lower()]
        
        # Формируем текстовое представление списка карт
        text_result = "🔮 Карты Таро 🔮\n\n"
        
        # Добавляем информацию о фильтрах
        if arcana:
            text_result += f"Фильтр по аркану: {arcana}\n"
        if suit:
            text_result += f"Фильтр по масти: {suit}\n"
        
        text_result += f"Найдено карт: {len(filtered_cards)}\n\n"
        
        # Группируем карты по арканам и мастям для более удобного отображения
        if len(filtered_cards) > 0:
            # Группировка по арканам
            arcana_groups = {}
            for card in filtered_cards:
                arcana_type = card.get('arcana', 'Неизвестный аркан')
                suit_type = card.get('suit', 'Без масти')
                
                if arcana_type not in arcana_groups:
                    arcana_groups[arcana_type] = {}
                
                if suit_type not in arcana_groups[arcana_type]:
                    arcana_groups[arcana_type][suit_type] = []
                
                arcana_groups[arcana_type][suit_type].append(card)
            
            # Формируем текст с группировкой
            for arcana_type, suits in arcana_groups.items():
                text_result += f"## {arcana_type} аркан\n\n"
                
                for suit_type, cards in suits.items():
                    if suit_type != 'Без масти':
                        text_result += f"### {suit_type}\n\n"
                    
                    for card in cards:
                        text_result += f"{card['id']}. **{card['name']}**\n"
                    
                    text_result += "\n"
        else:
            text_result += "По заданным фильтрам карты не найдены."
        
        text_result += "Для получения подробной информации о карте используйте команду /card с указанием ID карты."
        
        return {"api_result_text": text_result}
    except Exception as e:
        return {"api_result_text": f"Ошибка: {str(e)}"}

@router.get("/three_cards", response_model=Dict[str, Any])
async def get_puzzlebot_three_cards(
    question: Optional[str] = Query(None, description="Вопрос для гадания"),
    user_type: str = Query("free", description="Тип пользователя (free/premium)")
):
    """
    Получение гадания "Три карты" для PuzzleBot
    
    - **question**: Вопрос для гадания (опционально)
    - **user_type**: Тип пользователя (free/premium)
    """
    # Используем расклад "Три карты" (ID = 2)
    return await get_puzzlebot_reading(spread_id=2, question=question, user_type=user_type)

@router.get("/seven_cards", response_model=Dict[str, Any])
async def get_puzzlebot_seven_cards(
    question: Optional[str] = Query(None, description="Вопрос для гадания"),
    user_type: str = Query("free", description="Тип пользователя (free/premium)")
):
    """
    Получение гадания "Семь карт" для PuzzleBot
    
    - **question**: Вопрос для гадания (опционально)
    - **user_type**: Тип пользователя (free/premium)
    """
    # Используем расклад "Семь карт" (ID = 6)
    return await get_puzzlebot_reading(spread_id=6, question=question, user_type=user_type)

@router.get("/celtic_cross", response_model=Dict[str, Any])
async def get_puzzlebot_celtic_cross(
    question: Optional[str] = Query(None, description="Вопрос для гадания"),
    user_type: str = Query("free", description="Тип пользователя (free/premium)")
):
    """
    Получение гадания "Кельтский крест" для PuzzleBot
    
    - **question**: Вопрос для гадания (опционально)
    - **user_type**: Тип пользователя (free/premium)
    """
    # Используем расклад "Кельтский крест" (ID = 3)
    return await get_puzzlebot_reading(spread_id=3, question=question, user_type=user_type)

@router.get("/relationship", response_model=Dict[str, Any])
async def get_puzzlebot_relationship(
    question: Optional[str] = Query(None, description="Вопрос для гадания"),
    user_type: str = Query("free", description="Тип пользователя (free/premium)")
):
    """
    Получение гадания "Расклад на отношения" для PuzzleBot
    
    - **question**: Вопрос для гадания (опционально)
    - **user_type**: Тип пользователя (free/premium)
    """
    # Используем расклад "Расклад на отношения" (ID = 4)
    return await get_puzzlebot_reading(spread_id=4, question=question, user_type=user_type)

@router.get("/wish_cards", response_model=Dict[str, Any])
async def get_puzzlebot_wish_cards(
    question: Optional[str] = Query(None, description="Желание для анализа"),
    user_type: str = Query("free", description="Тип пользователя (free/premium)")
):
    """
    Получение гадания "Карты желаний" для PuzzleBot
    
    - **question**: Желание для анализа (опционально)
    - **user_type**: Тип пользователя (free/premium)
    """
    # Используем расклад "Карты желаний" (ID = 5)
    return await get_puzzlebot_reading(spread_id=5, question=question, user_type=user_type)

@router.get("/horoscope", response_model=Dict[str, Any])
async def get_puzzlebot_horoscope(
    question: Optional[str] = Query(None, description="Вопрос для гадания"),
    user_type: str = Query("free", description="Тип пользователя (free/premium)")
):
    """
    Получение гадания "Гороскоп" для PuzzleBot
    
    - **question**: Вопрос для гадания (опционально)
    - **user_type**: Тип пользователя (free/premium)
    """
    # Используем расклад "Гороскоп" (ID = 7)
    return await get_puzzlebot_reading(spread_id=7, question=question, user_type=user_type)

@router.get("/tree_of_life", response_model=Dict[str, Any])
async def get_puzzlebot_tree_of_life(
    question: Optional[str] = Query(None, description="Вопрос для гадания"),
    user_type: str = Query("free", description="Тип пользователя (free/premium)")
):
    """
    Получение гадания "Древо жизни" для PuzzleBot
    
    - **question**: Вопрос для гадания (опционально)
    - **user_type**: Тип пользователя (free/premium)
    """
    # Используем расклад "Древо жизни" (ID = 8)
    return await get_puzzlebot_reading(spread_id=8, question=question, user_type=user_type) 