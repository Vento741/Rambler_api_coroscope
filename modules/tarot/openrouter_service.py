"""
Сервис для обработки запросов к картам Таро через OpenRouter
"""
import json
import logging
import random
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import asyncio

from fastapi import HTTPException

from core.exceptions import NetworkException
from core.openrouter_client import OpenRouterClient
from core.cache import CacheManager
from .models import ApiResponse, TarotReading, TarotCardPosition, TarotSpread, TarotCard
from .data import get_all_cards, get_card_by_id, get_all_spreads, get_spread_by_id
from .prompts import get_spread_prompt, TAROT_SPREAD_PROMPTS

logger = logging.getLogger(__name__)

class TarotOpenRouterService:
    """Сервис для обработки запросов к картам Таро через OpenRouter"""
    
    def __init__(
        self, 
        cache_manager: CacheManager,
        openrouter_client: OpenRouterClient,
        prompts_config: Dict[str, Dict[str, Any]],
    ):
        """
        Инициализация сервиса
        
        :param cache_manager: Менеджер кэша
        :param openrouter_client: Клиент OpenRouter
        :param prompts_config: Конфигурация промптов для разных типов пользователей
        """
        self.cache_manager = cache_manager
        self.openrouter_client = openrouter_client
        self.prompts_config = prompts_config
        
        # Сопоставление типов пользователей и моделей
        self.user_type_models = {
            "free": ["google/gemini-2.0-flash-001", "google/gemini-2.0-flash-exp:free", "deepseek/deepseek-prover-v2:free"],
            "premium": ["google/gemini-2.0-flash-001", "qwen/qwen2.5-vl-72b-instruct:free"]
        }
    
    def _get_prompt_config(self, user_type: str) -> Dict[str, Any]:
        """
        Получение конфигурации промпта для типа пользователя
        
        :param user_type: Тип пользователя (free/premium)
        :return: Конфигурация промпта
        """
        return self.prompts_config.get(user_type, self.prompts_config["free"])
    
    def _get_models_for_user_type(self, user_type: str) -> list:
        """
        Получение списка моделей для типа пользователя
        
        :param user_type: Тип пользователя (free/premium)
        :return: Список моделей
        """
        return self.user_type_models.get(user_type, self.user_type_models["free"])
    
    def _draw_cards(self, spread_id: int) -> List[Tuple[Dict[str, Any], bool]]:
        """
        Вытягивание карт для расклада
        
        :param spread_id: ID расклада
        :return: Список кортежей (карта, перевернута ли)
        """
        spread = get_spread_by_id(spread_id)
        if not spread:
            raise ValueError(f"Расклад с ID {spread_id} не найден")
        
        all_cards = get_all_cards()
        card_count = spread["card_count"]
        
        # Случайно выбираем карты из колоды без повторений
        selected_cards = random.sample(all_cards, card_count)
        
        # Для каждой карты определяем, перевернута она или нет
        return [(card, random.choice([True, False])) for card in selected_cards]
    
    def _prepare_user_message(self, spread_id: int, drawn_cards: List[Tuple[Dict[str, Any], bool]], question: Optional[str], user_type: str) -> str:
        """
        Подготовка сообщения пользователя для OpenRouter
        
        :param spread_id: ID расклада
        :param drawn_cards: Список вытянутых карт с их положением
        :param question: Вопрос для гадания (опционально)
        :param user_type: Тип пользователя (free/premium)
        :return: Сообщение пользователя
        """
        spread = get_spread_by_id(spread_id)
        
        # Формируем информацию о раскладе
        spread_info = f"Расклад: {spread['name']}\nОписание расклада: {spread['description']}\n"
        
        # Добавляем вопрос, если он есть
        question_info = f"Вопрос: {question}\n" if question else "Вопрос не задан (общее гадание)\n"
        
        # Формируем информацию о картах
        cards_info = "Карты в раскладе:\n"
        for i, (card, is_reversed) in enumerate(drawn_cards):
            position = spread["positions"][i]
            position_name = position["name"]
            position_desc = position["description"]
            
            orientation = "перевернутая" if is_reversed else "прямая"
            
            cards_info += f"{i+1}. Позиция '{position_name}' ({position_desc}): {card['name']} ({orientation})\n"
            cards_info += f"   Описание карты: {card['description']}\n"
            
            if is_reversed:
                cards_info += f"   Значение в перевернутом положении: {card['meaning_reversed']}\n"
                cards_info += f"   Ключевые слова: {', '.join(card['keywords_reversed'])}\n"
            else:
                cards_info += f"   Значение в прямом положении: {card['meaning_upright']}\n"
                cards_info += f"   Ключевые слова: {', '.join(card['keywords_upright'])}\n"
        
        # Объединяем все части сообщения
        message = f"{spread_info}\n{question_info}\n{cards_info}\n"
        
        # Добавляем специфичные инструкции для данного расклада
        spread_specific_prompt = get_spread_prompt(spread_id, user_type)
        if spread_specific_prompt:
            message += f"\nСпециальные инструкции для этого расклада:\n{spread_specific_prompt}\n"
        
        # Добавляем общие инструкции в зависимости от типа пользователя
        if user_type == "free":
            message += (
                "Пожалуйста, предоставь краткую интерпретацию расклада и общий совет. "
                "Ограничься общим толкованием и основными выводами."
            )
        else:
            message += (
                "Пожалуйста, предоставь детальную интерпретацию расклада, включая: "
                "1. Общий анализ расклада и его энергетики, "
                "2. Подробное толкование каждой карты в контексте ее позиции, "
                "3. Взаимосвязи между картами и их влияние друг на друга, "
                "4. Конкретные советы и рекомендации на основе расклада, "
                "5. Возможные сценарии развития ситуации."
            )
        
        return message
    
    async def get_tarot_reading(
        self,
        spread_id: int,
        question: Optional[str] = None,
        user_type: str = "free",
        fixed_cards: Optional[List[Dict[str, Any]]] = None
    ) -> ApiResponse:
        """
        Получение гадания на Таро
        
        Args:
            spread_id: ID расклада
            question: Вопрос для гадания
            user_type: Тип пользователя (free/premium)
            fixed_cards: Список карт, которые должны быть в раскладе 
                         [{"card_id": id, "is_reversed": bool}, ...]
        
        Returns:
            ApiResponse: Ответ с данными гадания
        """
        try:
            # Проверяем существование расклада
            spread = get_spread_by_id(spread_id)
            if not spread:
                return ApiResponse(
                    success=False,
                    error=f"Расклад с ID {spread_id} не найден"
                )
            
            # Проверяем тип пользователя
            if user_type not in ["free", "premium"]:
                return ApiResponse(
                    success=False,
                    error=f"Неверный тип пользователя. Допустимые значения: free, premium"
                )
            
            # Формируем кэш-ключ
            cache_key = f"tarot_reading_{spread_id}_{user_type}"
            if question:
                cache_key += f"_{hash(question)}"
            if fixed_cards:
                # Если указаны фиксированные карты, включаем их в кэш-ключ
                fixed_cards_str = "_".join([f"{c['card_id']}_{c['is_reversed']}" for c in fixed_cards])
                cache_key += f"_{fixed_cards_str}"
            
            # Проверяем кэш
            cached_response = await self.cache_manager.get(cache_key)
            if cached_response:
                # Возвращаем кэшированный ответ
                cached_response["cached"] = True
                return ApiResponse(**cached_response)
            
            # Получаем все карты
            all_cards = get_all_cards()
            if not all_cards:
                return ApiResponse(
                    success=False,
                    error="Не удалось получить список карт Таро"
                )
            
            # Выбираем карты для расклада
            cards_for_reading = []
            
            # Если есть фиксированные карты, используем их
            if fixed_cards:
                for fixed_card_data in fixed_cards:
                    card_id = fixed_card_data["card_id"]
                    is_reversed = fixed_card_data["is_reversed"]
                    
                    card = get_card_by_id(card_id)
                    if not card:
                        return ApiResponse(
                            success=False,
                            error=f"Карта с ID {card_id} не найдена"
                        )
                    
                    cards_for_reading.append({
                        "card": card,
                        "is_reversed": is_reversed
                    })
            
            # Добираем оставшиеся карты случайным образом
            remaining_cards_count = spread["card_count"] - len(cards_for_reading)
            if remaining_cards_count > 0:
                # Создаем копию списка карт
                available_cards = all_cards.copy()
                
                # Исключаем карты, которые уже выбраны как фиксированные
                if fixed_cards:
                    fixed_card_ids = [card_data["card_id"] for card_data in fixed_cards]
                    available_cards = [card for card in available_cards if card["id"] not in fixed_card_ids]
                
                # Проверяем, достаточно ли осталось карт
                if len(available_cards) < remaining_cards_count:
                    return ApiResponse(
                        success=False,
                        error=f"Недостаточно карт для расклада. Требуется {remaining_cards_count}, доступно {len(available_cards)}"
                    )
                
                # Выбираем случайные карты
                selected_cards = random.sample(available_cards, remaining_cards_count)
                
                for card in selected_cards:
                    # Определяем случайно положение карты (прямое или перевернутое)
                    is_reversed = random.choice([True, False])
                    cards_for_reading.append({
                        "card": card,
                        "is_reversed": is_reversed
                    })
            
            # Формируем данные для отправки в промпт
            cards_with_positions = []
            
            for i, card_data in enumerate(cards_for_reading):
                if i < len(spread["positions"]):
                    position = spread["positions"][i]
                else:
                    # Если позиций меньше, чем карт (что странно), создаем дефолтную позицию
                    position = {
                        "name": f"Позиция {i+1}",
                        "description": f"Позиция {i+1} в раскладе"
                    }
                
                card = card_data["card"]
                is_reversed = card_data["is_reversed"]
                
                cards_with_positions.append({
                    "card_id": card["id"],
                    "card_name": card["name"],
                    "card_arcana": card["arcana"],
                    "card_suit": card.get("suit", ""),
                    "card_keywords": card["keywords_reversed"] if is_reversed else card["keywords_upright"],
                    "card_meaning": card["meaning_reversed"] if is_reversed else card["meaning_upright"],
                    "is_reversed": is_reversed,
                    "position": i + 1,
                    "position_name": position["name"],
                    "position_description": position["description"],
                    "card_image_url": card.get("image_url", "")  # URL изображения карты, если есть
                })
            
            # Получаем соответствующий промпт
            prompt_templates = TAROT_SPREAD_PROMPTS.get(spread_id)
            if not prompt_templates:
                return ApiResponse(
                    success=False,
                    error=f"Промпт для расклада с ID {spread_id} не найден"
                )
            
            # Выбираем промпт в зависимости от типа пользователя
            prompt_template = prompt_templates.get(user_type)
            if not prompt_template:
                return ApiResponse(
                    success=False,
                    error=f"Промпт для типа пользователя {user_type} не найден"
                )
            
            # Подготавливаем данные для промпта
            prompt_data = {
                "spread_name": spread["name"],
                "spread_description": spread["description"],
                "question": question if question else "Общее гадание",
                "cards": cards_with_positions
            }
            
            # Формируем промпт
            prompt = prompt_template.format(**prompt_data)
            
            # Отправляем запрос к OpenRouter
            result = await self.openrouter_client.chat_completion(
                messages=[
                    {"role": "system", "content": "Вы - опытный таролог, предоставляющий глубокие интерпретации раскладов Таро."},
                    {"role": "user", "content": prompt}
                ],
                model=self.prompts_config["TAROT_MODEL"]
            )
            
            # Формируем ответ
            if result.get("success", False):
                interpretation = result.get("response", "")
                
                # Формируем данные для ответа
                response_data = {
                    "spread": spread,
                    "cards": cards_with_positions,
                    "interpretation": interpretation,
                    "question": question if question else "Общее гадание",
                    "timestamp": datetime.now().isoformat()
                }
                
                # Сохраняем в кэш
                await self.cache_manager.set(
                    key=cache_key,
                    value={
                        "success": True,
                        "data": response_data,
                        "error": None,
                        "model": self.prompts_config["TAROT_MODEL"]
                    },
                    ttl_minutes=self.prompts_config.get("TAROT_CACHE_TTL", 60)
                )
                
                # Возвращаем ответ
                return ApiResponse(
                    success=True,
                    data=response_data,
                    model=self.prompts_config["TAROT_MODEL"],
                    cached=False
                )
            else:
                error_message = result.get("error", "Неизвестная ошибка при получении интерпретации")
                return ApiResponse(
                    success=False,
                    error=error_message
                )
        
        except Exception as e:
            logger.exception(f"Ошибка при получении гадания на Таро: {str(e)}")
            return ApiResponse(
                success=False,
                error=f"Ошибка при получении гадания на Таро: {str(e)}"
            ) 