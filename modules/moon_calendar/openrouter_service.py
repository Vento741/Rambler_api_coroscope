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
        
        # Сопоставление типов пользователей и моделей (с приоритетом)
        self.user_type_models = {
            "free": [
                "google/gemini-2.0-flash-001", 
                "google/gemini-2.0-flash-exp:free", 
                "deepseek-r1-0528-qwen3-8b:free", # Добавили как одну из основных
                "deepseek/deepseek-prover-v2:free" 
            ],
            "premium": [
                "google/gemini-2.0-flash-001", 
                "qwen/qwen2.5-vl-72b-instruct:free", 
                "deepseek-r1-0528-qwen3-8b:free"  # Добавили как одну из основных
            ]
        }
    
    async def _get_calendar_data(self, calendar_date: date) -> Dict[str, Any]:
        """
        Получение данных лунного календаря
        
        :param calendar_date: Дата календаря
        :return: Данные лунного календаря
        """
        # Проверяем, что calendar_date - это объект типа date
        if isinstance(calendar_date, str):
            logger.warning(f"Передана строка вместо объекта date: {calendar_date}. Преобразуем в date.")
            try:
                from datetime import datetime
                calendar_date = datetime.fromisoformat(calendar_date).date()
            except ValueError as e:
                logger.error(f"Не удалось преобразовать строку в date: {e}")
                raise ValueError(f"Неверный формат даты: {calendar_date}")
                
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
                f"Информация: {moon_day.get('info', 'Информация отсутствует')}\n\n"
                f"Важно: Используй только простые символы. Избегай сложного форматирования. "
                f"Для заголовков используй ЗАГЛАВНЫЕ БУКВЫ. Не используй звездочки, только обычный текст."
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
                f"Рекомендации:\n{recommendations_text}\n\n"
                f"Важно: Используй только простые символы. Избегай сложного форматирования. "
                f"Для заголовков используй ЗАГЛАВНЫЕ БУКВЫ. Не используй звездочки, только обычный текст."
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
        # Проверяем, что calendar_date - это объект типа date
        if isinstance(calendar_date, str):
            logger.warning(f"Передана строка вместо объекта date: {calendar_date}. Преобразуем в date.")
            try:
                from datetime import datetime
                calendar_date = datetime.fromisoformat(calendar_date).date()
            except ValueError as e:
                logger.error(f"Не удалось преобразовать строку в date: {e}")
                return None
                
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
        # Проверяем, что calendar_date - это объект типа date
        if isinstance(calendar_date, str):
            logger.warning(f"Передана строка вместо объекта date: {calendar_date}. Преобразуем в date.")
            try:
                from datetime import datetime
                calendar_date = datetime.fromisoformat(calendar_date).date()
            except ValueError as e:
                logger.error(f"Не удалось преобразовать строку в date: {e}")
                return
                
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
    
    async def _clean_model_response(self, response: str) -> str:
        """
        Очистка ответа модели от потенциально проблемных символов
        
        :param response: Исходный ответ модели
        :return: Очищенный ответ
        """
        import re
        
        # Замена сложных символов Unicode на простые аналоги
        cleaned = response
        
        # Удаление потенциально проблемных комбинаций символов
        cleaned = re.sub(r'\*\*(.+?)\*\*', r'\1', cleaned)  # Удаление маркеров жирного текста
        cleaned = re.sub(r'```.*?```', '', cleaned, flags=re.DOTALL)  # Удаление блоков кода
        cleaned = re.sub(r'`(.*?)`', r'\1', cleaned)  # Удаление инлайн-кода
        
        # Замена разделителей текста на простые переносы строк
        cleaned = re.sub(r'---+', '\n\n', cleaned)
        cleaned = re.sub(r'\*\*\*+', '\n\n', cleaned)
        cleaned = re.sub(r'===+', '\n\n', cleaned)
        
        # Нормализация переносов строк
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        # Проверка наличия текста после очистки
        if not cleaned.strip():
            logger.warning("После очистки ответа модели получен пустой текст")
            return "Извините, возникла техническая проблема. Пожалуйста, попробуйте еще раз."
        
        return cleaned
    
    async def get_moon_calendar_response(self, calendar_date: date, user_type: str) -> ApiResponse:
        """
        Получение ответа лунного календаря для пользователя (только из кэша).
        AI-генерация теперь происходит в фоновой задаче.
        
        :param calendar_date: Дата календаря
        :param user_type: Тип пользователя (free/premium)
        :return: Ответ API
        """
        try:
            # Проверяем, что calendar_date - это объект типа date
            if isinstance(calendar_date, str):
                logger.warning(f"Передана строка вместо объекта date: {calendar_date}. Преобразуем в date.")
                try:
                    from datetime import datetime
                    calendar_date = datetime.fromisoformat(calendar_date).date()
                except ValueError as e:
                    logger.error(f"Не удалось преобразовать строку в date: {e}")
                    return ApiResponse(
                        success=False,
                        error=f"Неверный формат даты: {calendar_date}"
                    )
                    
            # Проверяем наличие кэшированного AI-ответа
            cached_ai_response = await self._get_cached_response(calendar_date, user_type)
            
            if cached_ai_response:
                logger.info(f"Возвращаю кэшированный AI-ответ для {calendar_date} и типа {user_type}")
                return ApiResponse(
                    success=True,
                    data=cached_ai_response,
                    cached=True,
                    model="cached_ai_response" 
                )
            else:
                # Если AI-ответа нет, проверяем, есть ли хотя бы спарсенные данные
                # Это поможет понять, была ли уже запущена фоновая задача для этой даты
                parsed_data_from_cache = await self.cache_manager.get(calendar_date)
                if parsed_data_from_cache:
                    logger.warning(f"Кэшированный AI-ответ для {calendar_date} (тип: {user_type}) НЕ НАЙДЕН, но спарсенные данные ЕСТЬ. Возможно, AI-генерация еще не завершена.")
                    return ApiResponse(
                        success=False,
                        error=f"Прогноз для {calendar_date} (тип: {user_type}) еще не готов. Пожалуйста, попробуйте позже.",
                        model="parsed_data_exists_no_ai_response"
                    )
                else:
                    logger.warning(f"ДАННЫЕ для {calendar_date} НЕ НАЙДЕНЫ в кэше. Фоновая задача, возможно, еще не обработала эту дату.")
                    return ApiResponse(
                        success=False,
                        error=f"Данные для {calendar_date} еще не обработаны. Пожалуйста, попробуйте позже.",
                        model="no_data_in_cache"
                    )

        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении кэшированного AI-ответа для {calendar_date} (тип: {user_type}): {e}", exc_info=True)
            return ApiResponse(
                success=False,
                error=f"Внутренняя ошибка сервера при получении прогноза: {str(e)}"
            )

    async def background_generate_and_cache_ai_responses(self, calendar_date: date):
        """
        Фоновая генерация и кэширование AI-ответов для всех типов пользователей.
        Этот метод вызывается из MoonCalendarTasks.
        Предполагается, что спарсенные данные для calendar_date уже лежат в кэше.
        """
        # Проверяем, что calendar_date - это объект типа date
        if isinstance(calendar_date, str):
            logger.warning(f"[BG_AI_GEN] Передана строка вместо объекта date: {calendar_date}. Преобразуем в date.")
            try:
                from datetime import datetime
                calendar_date = datetime.fromisoformat(calendar_date).date()
            except ValueError as e:
                logger.error(f"[BG_AI_GEN] Не удалось преобразовать строку в date: {e}")
                return
                
        logger.info(f"[BG_AI_GEN] Запуск генерации AI-ответов для {calendar_date}")
        
        try:
            # Получаем спарсенные данные календаря (должны быть уже в кэше)
            calendar_data = await self._get_calendar_data(calendar_date)
            if not calendar_data:
                logger.error(f"[BG_AI_GEN] Спарсенные данные для {calendar_date} не найдены в кэше. AI-генерация прервана.")
                return

            user_types_to_process = ["free", "premium"]

            for user_type in user_types_to_process:
                logger.info(f"[BG_AI_GEN] Генерация для {calendar_date}, тип: {user_type}")
                try:
                    # Проверяем, нет ли уже свежего AI ответа для этого типа (на всякий случай, если задача перезапустилась)
                    # Это нестрогая проверка, основная логика в get_moon_calendar_response
                    # if await self._get_cached_response(calendar_date, user_type):
                    #     logger.info(f"[BG_AI_GEN] AI-ответ для {calendar_date} (тип: {user_type}) уже существует и свежий. Пропускаем.")
                    #     continue
                        
                    prompt_config = self._get_prompt_config(user_type)
                    user_message = self._prepare_user_message(calendar_data, user_type)
                    models = self._get_models_for_user_type(user_type)
                    
                    logger.info(f"[BG_AI_GEN] Подготовлен запрос к OpenRouter для {calendar_date}, тип: {user_type}. Доступные модели: {models}")
                    
                    ai_response_text = None
                    selected_model = None
                    last_error_details = "Неизвестная ошибка"

                    for model_name in models:
                        try:
                            logger.info(f"[BG_AI_GEN] Пробуем модель: {model_name} для {calendar_date} (тип: {user_type})")
                            response_content = await self.openrouter_client.generate_text(
                                system_message=prompt_config["system_message"],
                                user_message=user_message,
                                max_tokens=prompt_config["max_tokens"],
                                temperature=prompt_config["temperature"],
                                model=model_name
                            )
                            
                            if response_content and response_content.strip():
                                ai_response_text = await self._clean_model_response(response_content)
                                selected_model = model_name
                                logger.info(f"[BG_AI_GEN] Успешно получен и очищен ответ от модели {model_name} для {calendar_date} (тип: {user_type})")
                                break # Успех, выходим из цикла моделей
                            else:
                                logger.warning(f"[BG_AI_GEN] Модель {model_name} вернула пустой ответ для {calendar_date} (тип: {user_type}). Пробуем следующую.")
                                last_error_details = f"Модель {model_name} вернула пустой ответ."
                        except Exception as e_model:
                            last_error_details = str(e_model)
                            logger.error(f"[BG_AI_GEN] Ошибка при использовании модели {model_name} для {calendar_date} (тип: {user_type}): {e_model}", exc_info=True)
                            continue # Пробуем следующую модель
                    
                    if ai_response_text and selected_model:
                        await self._cache_response(calendar_date, user_type, ai_response_text)
                        logger.info(f"[BG_AI_GEN] AI-ответ от {selected_model} для {calendar_date} (тип: {user_type}) сохранен в кэш.")
                    else:
                        logger.error(f"[BG_AI_GEN] Не удалось получить AI-ответ ни от одной модели для {calendar_date} (тип: {user_type}). Последняя ошибка: {last_error_details}")

                except Exception as e_user_type:
                    logger.error(f"[BG_AI_GEN] Ошибка при генерации AI-ответа для {calendar_date} (тип: {user_type}): {e_user_type}", exc_info=True)
            
            logger.info(f"[BG_AI_GEN] Завершение генерации AI-ответов для {calendar_date}")

        except Exception as e_main:
            logger.error(f"[BG_AI_GEN] Общая ошибка в background_generate_and_cache_ai_responses для {calendar_date}: {e_main}", exc_info=True) 