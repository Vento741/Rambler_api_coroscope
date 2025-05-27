"""
Сервис для обработки данных лунного календаря через OpenRouter
"""
import json
import logging
from datetime import date
from typing import Dict, Any, Optional

from fastapi import HTTPException
import aiohttp

from core.openrouter_client import OpenRouterClient
from core.cache import CacheManager
from .models import ApiResponse
from .parser import MoonCalendarParser

logger = logging.getLogger(__name__)

class MoonCalendarOpenRouterService:
    """Сервис для обработки данных лунного календаря через OpenRouter"""
    
    def __init__(
        self, 
        cache_manager: CacheManager,
        parser: MoonCalendarParser,
        openrouter_client: OpenRouterClient,
        prompts_config: Dict[str, Dict[str, Any]]
    ):
        """
        Инициализация сервиса
        
        :param cache_manager: Менеджер кэша
        :param parser: Парсер лунного календаря
        :param openrouter_client: Клиент OpenRouter
        :param prompts_config: Конфигурация промптов для разных типов пользователей
        """
        self.cache_manager = cache_manager
        self.parser = parser
        self.openrouter_client = openrouter_client
        self.prompts_config = prompts_config
    
    async def _get_calendar_data(self, calendar_date: date) -> Dict[str, Any]:
        """
        Получение данных лунного календаря
        
        :param calendar_date: Дата календаря
        :return: Данные лунного календаря
        """
        # Генерируем ключ кэша для даты
        cache_key = f"moon_calendar_{calendar_date.isoformat()}"
        
        # Проверяем кэш
        cached_data = await self.cache_manager.get(calendar_date)
        
        if cached_data:
            logger.info(f"Использую кэшированные данные для {calendar_date}")
            return cached_data
        
        # Если данных нет в кэше, парсим их
        logger.info(f"Парсинг данных лунного календаря для {calendar_date}")
        try:
            calendar_data = await self.parser.parse_calendar_day(calendar_date)
            
            # Сохраняем в кэш
            await self.cache_manager.set(calendar_date, calendar_data)
            
            return calendar_data
        except Exception as e:
            logger.error(f"Ошибка при получении данных лунного календаря: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при получении данных лунного календаря: {str(e)}"
            )
    
    def _prepare_user_message(self, calendar_data: Dict[str, Any], user_type: str) -> str:
        """
        Подготовка сообщения пользователя для OpenRouter
        
        :param calendar_data: Данные лунного календаря
        :param user_type: Тип пользователя (free/premium)
        :return: Сообщение пользователя
        """
        if user_type == "free":
            # Для бесплатных пользователей - только основная информация
            moon_day = calendar_data["moon_days"][0] if calendar_data["moon_days"] else {}
            
            return (
                f"Дата: {calendar_data['date']}\n"
                f"Фаза луны: {calendar_data['moon_phase']}\n"
                f"Лунный день: {moon_day.get('name', 'Не определен')}\n"
                f"Информация: {moon_day.get('info', 'Информация отсутствует')}"
            )
        else:
            # Для премиум пользователей - полная информация
            moon_days_text = "\n\n".join([
                f"{day.get('name', '')}: ({day.get('start', '')} - {day.get('end', '')})\n{day.get('info', '')}"
                for day in calendar_data["moon_days"]
            ])
            
            recommendations_text = "\n".join([
                f"{title}: {text}"
                for title, text in calendar_data["recommendations"].items()
            ])
            
            return (
                f"Дата: {calendar_data['date']}\n"
                f"Фаза луны: {calendar_data['moon_phase']}\n\n"
                f"Лунные дни:\n{moon_days_text}\n\n"
                f"Рекомендации:\n{recommendations_text}"
            )
    
    def _get_prompt_config(self, user_type: str) -> Dict[str, Any]:
        """
        Получение конфигурации промпта для типа пользователя
        
        :param user_type: Тип пользователя (free/premium)
        :return: Конфигурация промпта
        """
        # Если тип пользователя не определен или не найден в конфигурации,
        # используем конфигурацию для бесплатных пользователей
        return self.prompts_config.get(user_type, self.prompts_config["free"])
    
    async def _get_cached_response(self, calendar_date: date, user_type: str) -> Optional[str]:
        """
        Получение кэшированного ответа OpenRouter
        
        :param calendar_date: Дата календаря
        :param user_type: Тип пользователя
        :return: Кэшированный ответ или None
        """
        # Генерируем ключ кэша
        cache_key = f"openrouter_response_{calendar_date.isoformat()}_{user_type}"
        
        # Проверяем кэш
        cached_response = await self.cache_manager.get(date(1970, 1, 1))  # Используем фиктивную дату
        if cached_response and cache_key in cached_response:
            logger.info(f"Использую кэшированный ответ OpenRouter для {calendar_date} и типа {user_type}")
            return cached_response[cache_key]
        
        return None
    
    async def _cache_response(self, calendar_date: date, user_type: str, response: str) -> None:
        """
        Кэширование ответа OpenRouter
        
        :param calendar_date: Дата календаря
        :param user_type: Тип пользователя
        :param response: Ответ OpenRouter
        """
        # Генерируем ключ кэша
        cache_key = f"openrouter_response_{calendar_date.isoformat()}_{user_type}"
        
        # Получаем текущие кэшированные ответы
        cached_responses = await self.cache_manager.get(date(1970, 1, 1)) or {}
        
        # Добавляем новый ответ
        cached_responses[cache_key] = response
        
        # Сохраняем в кэш
        await self.cache_manager.set(date(1970, 1, 1), cached_responses)
        
        logger.info(f"Кэширован ответ OpenRouter для {calendar_date} и типа {user_type}")
    
    async def get_moon_calendar_response(self, calendar_date: date, user_type: str) -> ApiResponse:
        """
        Получение ответа лунного календаря для пользователя
        
        :param calendar_date: Дата календаря
        :param user_type: Тип пользователя (free/premium)
        :return: Ответ API
        """
        logger.info(f"Запрос лунного календаря для даты {calendar_date} и типа пользователя {user_type}")
        
        try:
            # Проверяем наличие кэшированного ответа
            cached_response = await self._get_cached_response(calendar_date, user_type)
            if cached_response:
                logger.info(f"Возвращаем кэшированный ответ для {calendar_date} и типа {user_type}")
                return ApiResponse(
                    success=True,
                    data=cached_response,
                    cached=True
                )
            
            # Получаем данные календаря
            try:
                calendar_data = await self._get_calendar_data(calendar_date)
                if not calendar_data:
                    logger.error(f"Не удалось получить данные календаря для {calendar_date}")
                    return ApiResponse(
                        success=False,
                        error="Не удалось получить данные лунного календаря",
                        cached=False
                    )
            except Exception as e:
                logger.error(f"Ошибка при получении данных календаря: {e}")
                return ApiResponse(
                    success=False,
                    error=f"Ошибка при получении данных лунного календаря: {str(e)}",
                    cached=False
                )
            
            # Получаем конфигурацию промпта
            prompt_config = self._get_prompt_config(user_type)
            
            # Подготавливаем сообщение пользователя
            user_message = self._prepare_user_message(calendar_data, user_type)
            
            # Логируем информацию о запросе
            logger.info(f"Подготовлен запрос к OpenRouter для {calendar_date} и типа {user_type}")
            logger.debug(f"Сообщение пользователя: {user_message[:100]}...")
            
            # Проверка доступности моделей
            try:
                # Простой запрос для проверки доступности API
                async with aiohttp.ClientSession() as session:
                    models_url = "https://openrouter.ai/api/v1/models"
                    async with session.get(
                        models_url,
                        headers={"Authorization": f"Bearer {self.openrouter_client._get_current_key()}"},
                        timeout=30
                    ) as response:
                        if response.status == 200:
                            models_data = await response.json()
                            available_models = [model.get('id') for model in models_data.get('data', [])]
                            logger.info(f"Доступные модели: {available_models}")
                            
                            # Проверяем, доступна ли наша модель
                            current_model = self.openrouter_client._get_current_model()
                            
                            if current_model not in available_models:
                                logger.error(f"Модель {current_model} недоступна! Доступные модели: {available_models}")
                                # Пробуем найти альтернативную модель
                                if 'google/gemini' in current_model:
                                    for model in available_models:
                                        if 'google/gemini' in model:
                                            logger.info(f"Найдена альтернативная модель: {model}")
                                            self.openrouter_client.models = [model]
                                            break
                        else:
                            logger.error(f"Ошибка при получении списка моделей: {response.status}, {await response.text()}")
            except Exception as e:
                logger.error(f"Ошибка при проверке доступности моделей: {e}")
            
            # Генерируем ответ через OpenRouter
            try:
                response = await self.openrouter_client.generate_text(
                    system_message=prompt_config["system_message"],
                    user_message=user_message,
                    max_tokens=prompt_config["max_tokens"],
                    temperature=prompt_config["temperature"]
                )
                
                # Проверка на пустой ответ
                if not response or not response.strip():
                    logger.error("Получен пустой ответ от OpenRouter")
                    
                    # Пробуем получить данные без обработки через OpenRouter
                    fallback_response = self._generate_fallback_response(calendar_data, user_type)
                    
                    # Кэшируем ответ
                    await self._cache_response(calendar_date, user_type, fallback_response)
                    
                    return ApiResponse(
                        success=True,
                        data=fallback_response,
                        cached=False,
                        fallback=True
                    )
                
                # Кэшируем ответ
                await self._cache_response(calendar_date, user_type, response)
                
                return ApiResponse(
                    success=True,
                    data=response,
                    cached=False
                )
                
            except HTTPException as e:
                logger.error(f"HTTP ошибка при генерации ответа: {e}")
                
                # Пробуем получить данные без обработки через OpenRouter
                fallback_response = self._generate_fallback_response(calendar_data, user_type)
                
                return ApiResponse(
                    success=True,
                    data=fallback_response,
                    cached=False,
                    fallback=True
                )
                
            except Exception as e:
                logger.error(f"Ошибка при генерации ответа: {e}")
                
                # Пробуем получить данные без обработки через OpenRouter
                fallback_response = self._generate_fallback_response(calendar_data, user_type)
                
                return ApiResponse(
                    success=True,
                    data=fallback_response,
                    cached=False,
                    fallback=True
                )
                
        except Exception as e:
            logger.error(f"Общая ошибка при обработке запроса лунного календаря: {e}")
            return ApiResponse(
                success=False,
                error=f"Ошибка при обработке запроса: {str(e)}",
                cached=False
            )
    
    def _generate_fallback_response(self, calendar_data: Dict[str, Any], user_type: str) -> str:
        """
        Генерация резервного ответа при ошибке OpenRouter
        
        :param calendar_data: Данные лунного календаря
        :param user_type: Тип пользователя
        :return: Резервный ответ
        """
        logger.info(f"Генерация резервного ответа для типа пользователя {user_type}")
        
        fallback_response = (
            f"Дата: {calendar_data['date']}\n"
            f"Фаза луны: {calendar_data['moon_phase']}\n\n"
        )
        
        if calendar_data['moon_days']:
            if user_type == "free":
                # Для бесплатных пользователей - только первый лунный день
                moon_day = calendar_data['moon_days'][0]
                fallback_response += (
                    f"Лунный день: {moon_day.get('name', '')}\n"
                    f"Период: {moon_day.get('start', '')} - {moon_day.get('end', '')}\n"
                    f"Информация: {moon_day.get('info', '')}\n\n"
                )
            else:
                # Для премиум пользователей - все лунные дни
                fallback_response += "Лунные дни:\n\n"
                for moon_day in calendar_data['moon_days']:
                    fallback_response += (
                        f"{moon_day.get('name', '')}\n"
                        f"Период: {moon_day.get('start', '')} - {moon_day.get('end', '')}\n"
                        f"Информация: {moon_day.get('info', '')}\n\n"
                    )
        
        if calendar_data['recommendations']:
            fallback_response += "Рекомендации:\n\n"
            for title, text in calendar_data['recommendations'].items():
                fallback_response += f"{title}: {text}\n\n"
        
        return fallback_response 