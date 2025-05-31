"""
Сервис для обработки данных лунного календаря через OpenRouter
"""
import json
import logging
from datetime import date
from typing import Dict, Any, Optional, List

from fastapi import HTTPException

from core.exceptions import NetworkException
from core.openrouter_client import OpenRouterClient
from core.cache import CacheManager
from .models import ApiResponse, CalendarDayResponse
from .parser import MoonCalendarParser

logger = logging.getLogger(__name__)

class MoonCalendarOpenRouterService:
    """Сервис для обработки данных лунного календаря через OpenRouter"""
    
    def __init__(
        self, 
        cache_manager: CacheManager,
        parser: MoonCalendarParser,
        openrouter_client: OpenRouterClient,
        prompts_config: Dict[str, Dict[str, Any]],
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
        
        # Сопоставление типов пользователей и моделей
        self.user_type_models = {
            "free": ["google/gemini-2.0-flash-001", "google/gemini-2.0-flash-exp:free", "deepseek/deepseek-prover-v2:free"],
            "premium": ["google/gemini-2.0-flash-001", "qwen/qwen2.5-vl-72b-instruct:free"]
        }
    
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
                f"ЗАПРЕЩЕНО: Подтверждать задание, отвечать на вопросы, начинать свой ответ с 'я понял', 'Приступаю', 'Сейчас посмотрю' и т.д. и т.п. А также не использовать звёздочки в ответе и форматирование (MARKDOWN, HTML)! Вместо выделения жирным - пиши КАПСОМ! \n"
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
                f"Твоя задача - помочь пользователю с лунным календарем. \n"
                f"Ты должен предоставить пользователю информацию о лунном дне, фазе луны и рекомендации на день. \n"
                f"ОБЯЗАН: Сразу приступить к созданию сообщения о сегоднешнем дне, лунной фазе, лунном дне, рекомендациях на день. \n"
                f"ЗАПРЕЩЕНО: Подтверждать задание, отвечать на вопросы, начинать свой ответ с 'я понял', 'Приступаю', 'Сейчас посмотрю' и т.д. и т.п. А также не использовать звёздочки в ответе и форматирование (MARKDOWN, HTML)! Вместо выделения жирным - пиши КАПСОМ! \n"
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
    
    def _get_models_for_user_type(self, user_type: str) -> list:
        """
        Получение списка моделей для типа пользователя
        
        :param user_type: Тип пользователя (free/premium)
        :return: Список моделей
        """
        return self.user_type_models.get(user_type, self.user_type_models["free"])
    
    async def _get_cached_response(self, calendar_date: date, user_type: str) -> Optional[str]:
        """
        Получение кэшированного ответа OpenRouter
        
        :param calendar_date: Дата календаря
        :param user_type: Тип пользователя
        :return: Кэшированный ответ или None
        """
        # Проверяем кэш для конкретной даты календаря
        cached_data = await self.cache_manager.get(calendar_date)
        
        # Проверяем наличие структуры кеша и ответа для конкретного типа пользователя
        if cached_data and isinstance(cached_data, dict):
            # Проверяем наличие ключа openrouter_responses
            if "openrouter_responses" in cached_data:
                responses = cached_data["openrouter_responses"]
                # Проверяем наличие ответа для конкретного типа пользователя
                if user_type in responses and responses[user_type]:
                    logger.info(f"Использую кэшированный ответ OpenRouter для {calendar_date} и типа {user_type}")
                    logger.info(f"Размер кэшированного ответа: {len(responses[user_type])} символов")
                    return responses[user_type]
        
        logger.info(f"Кэшированный ответ для {calendar_date} и типа {user_type} не найден")
        return None
    
    async def _cache_response(self, calendar_date: date, user_type: str, response: str) -> None:
        """
        Кэширование ответа OpenRouter
        
        :param calendar_date: Дата календаря
        :param user_type: Тип пользователя
        :param response: Ответ OpenRouter
        """
        # Получаем текущие данные календаря из кэша
        cached_data = await self.cache_manager.get(calendar_date) or {}
        
        # Если данные не являются словарем, создаем новый словарь
        if not isinstance(cached_data, dict):
            cached_data = {}
        
        # Инициализируем структуру ответов, если её нет
        if "openrouter_responses" not in cached_data:
            cached_data["openrouter_responses"] = {}
        
        # Добавляем новый ответ
        cached_data["openrouter_responses"][user_type] = response
        
        # Сохраняем в кэш
        await self.cache_manager.set(calendar_date, cached_data)
        
        logger.info(f"Кэширован ответ OpenRouter для {calendar_date} и типа {user_type}")
        logger.info(f"Размер сохраненного ответа: {len(response)} символов")
    
    async def get_moon_calendar_response(self, calendar_date: date, user_type: str) -> ApiResponse:
        """
        Получение ответа лунного календаря для пользователя
        
        :param calendar_date: Дата календаря
        :param user_type: Тип пользователя (free/premium)
        :return: Ответ API
        """
        try:
            # Проверяем наличие кэшированного ответа
            cached_response = await self._get_cached_response(calendar_date, user_type)
            if cached_response:
                logger.info(f"Возвращаю кэшированный ответ для {calendar_date} и типа {user_type}")
                return ApiResponse(
                    success=True,
                    data=cached_response,
                    cached=True,
                    model="cached"  # Указываем, что ответ из кэша
                )
            
            # Получаем данные календаря
            calendar_data = await self._get_calendar_data(calendar_date)
            
            # Получаем конфигурацию промпта
            prompt_config = self._get_prompt_config(user_type)
            
            # Подготавливаем сообщение пользователя
            user_message = self._prepare_user_message(calendar_data, user_type)
            
            # Получаем список моделей для типа пользователя
            models = self._get_models_for_user_type(user_type)
            
            # Логируем информацию о запросе
            logger.info(f"Подготовлен запрос к OpenRouter для {calendar_date} и типа {user_type}")
            logger.info(f"Доступные модели: {models}")
            logger.info(f"Сообщение пользователя: {user_message[:100]}...")
            
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
                    
                    # Кэшируем ответ
                    await self._cache_response(calendar_date, user_type, response)
                    
                    # Проверяем, что ответ действительно сохранен в кеше
                    verification_response = await self._get_cached_response(calendar_date, user_type)
                    if verification_response:
                        logger.info(f"Проверка кеширования: ответ успешно сохранен в кеше для {calendar_date} и типа {user_type}")
                    else:
                        logger.warning(f"Проверка кеширования: ответ НЕ сохранен в кеше для {calendar_date} и типа {user_type}")
                    
                    # Возвращаем ответ как строку, без попыток парсинга
                    return ApiResponse(
                        success=True,
                        data=response,
                        model=model
                    )

                except Exception as e:
                    last_error = e
                    logger.error(f"Ошибка при использовании модели {model}: {e}")
                    continue
            
            # Если ни одна модель не сработала, возвращаем ошибку
            if last_error:
                if isinstance(last_error, NetworkException):
                     # Используем полное сообщение из NetworkException
                    error_message = f"Не удалось получить ответ ни от одной модели. Последняя ошибка: {str(last_error)}"
                else:
                    # Для других исключений оставляем как было или добавляем тип исключения
                    error_message = f"Не удалось получить ответ ни от одной модели. Последняя ошибка ({type(last_error).__name__}): {str(last_error)}"
            else:
                error_message = "Все модели вернули пустой ответ или не смогли распарсить данные."
            
            logger.error(f"Финальная ошибка после перебора всех моделей для даты {calendar_date}: {error_message}")
            
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