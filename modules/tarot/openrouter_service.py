"""
Сервис для обработки запросов к картам Таро через OpenRouter
"""
import json
import logging
import random
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple

from fastapi import HTTPException

from core.exceptions import NetworkException
from core.openrouter_client import OpenRouterClient
from core.cache import CacheManager
from .models import ApiResponse, TarotReading, TarotCardPosition
from .data import get_all_cards, get_card_by_id, get_all_spreads, get_spread_by_id
from .prompts import get_spread_prompt

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
    
    async def get_tarot_reading(self, spread_id: int, question: Optional[str], user_type: str) -> ApiResponse:
        """
        Получение гадания на Таро
        
        :param spread_id: ID расклада
        :param question: Вопрос для гадания (опционально)
        :param user_type: Тип пользователя (free/premium)
        :return: Ответ API
        """
        try:
            # Проверяем существование расклада
            spread = get_spread_by_id(spread_id)
            if not spread:
                return ApiResponse(
                    success=False,
                    error=f"Расклад с ID {spread_id} не найден"
                )
            
            # Вытягиваем карты (всегда новые, так как результаты не кешируются)
            drawn_cards = self._draw_cards(spread_id)
            
            # Получаем конфигурацию промпта
            prompt_config = self._get_prompt_config(user_type)
            
            # Подготавливаем сообщение пользователя
            user_message = self._prepare_user_message(spread_id, drawn_cards, question, user_type)
            
            # Получаем список моделей для типа пользователя
            models = self._get_models_for_user_type(user_type)
            
            # Логируем информацию о запросе
            logger.info(f"Подготовлен запрос к OpenRouter для расклада {spread['name']}")
            logger.info(f"Доступные модели: {models}")
            
            # Формируем данные о картах для включения в ответ
            cards_data = []
            for i, (card, is_reversed) in enumerate(drawn_cards):
                position = spread["positions"][i]
                cards_data.append({
                    "position": position["position"],
                    "position_name": position["name"],
                    "position_description": position["description"],
                    "card_id": card["id"],
                    "card_name": card["name"],
                    "is_reversed": is_reversed,
                    "card_image_url": card["image_url"]
                })
            
            # Пробуем каждую модель по порядку
            last_error = None
            for model in models:
                try:
                    logger.info(f"Пробуем модель: {model}")
                    
                    # Генерируем ответ через OpenRouter с указанной моделью
                    response = await self.openrouter_client.generate_text(
                        system_message=prompt_config["system_message"],
                        user_message=user_message,
                        max_tokens=prompt_config["max_tokens"],
                        temperature=prompt_config["temperature"],
                        model=model
                    )
                    
                    # Проверка на пустой ответ
                    if not response or not response.strip():
                        logger.warning(f"Получен пустой ответ от модели {model}, пробуем следующую")
                        continue
                    
                    # Ответ успешно получен
                    logger.info(f"Успешно получен ответ от модели {model}")
                    
                    # Формируем полный ответ с данными о раскладе и интерпретацией
                    complete_response = {
                        "spread": spread,
                        "cards": cards_data,
                        "interpretation": response,
                        "created_at": datetime.now().isoformat(),
                        "question": question if question else "Общее гадание"
                    }
                    
                    # Возвращаем ответ
                    return ApiResponse(
                        success=True,
                        data=complete_response,
                        model=model
                    )

                except Exception as e:
                    last_error = e
                    logger.error(f"Ошибка при использовании модели {model}: {e}")
                    continue
            
            # Если ни одна модель не сработала, возвращаем ошибку
            if last_error:
                if isinstance(last_error, NetworkException):
                    error_message = f"Не удалось получить ответ ни от одной модели. Последняя ошибка: {str(last_error)}"
                else:
                    error_message = f"Не удалось получить ответ ни от одной модели. Последняя ошибка ({type(last_error).__name__}): {str(last_error)}"
            else:
                error_message = "Все модели вернули пустой ответ."
            
            logger.error(f"Финальная ошибка после перебора всех моделей: {error_message}")
            
            return ApiResponse(
                success=False,
                error=error_message
            )
            
        except HTTPException as e:
            logger.error(f"Ошибка HTTP: {e.detail}")
            return ApiResponse(
                success=False,
                error=f"Ошибка сервера: {e.detail}"
            )
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обработке запроса: {e}", exc_info=True)
            return ApiResponse(
                success=False,
                error=f"Внутренняя ошибка сервера: {str(e)}"
            ) 