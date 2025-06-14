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
        Получение ответа лунного календаря с обработкой через OpenRouter
        
        :param calendar_date: Дата календаря
        :param user_type: Тип пользователя (free/premium)
        :return: Ответ API
        """
        try:
            # Проверяем наличие кэшированного ответа
            ai_response = await self._get_cached_response(calendar_date, user_type)
            
            if ai_response:
                logger.info(f"Возвращаю кэшированный AI-ответ для {calendar_date} и типа {user_type}")
                return ApiResponse(
                    date=calendar_date.isoformat(),
                    response=ai_response,
                    error=None
                )
            
            # Если кэшированный ответ не найден, проверяем наличие данных календаря
            calendar_data = await self._get_calendar_data(calendar_date)
            
            if not calendar_data:
                # Если данных нет, пробуем их спарсить и сохранить
                logger.warning(f"ДАННЫЕ для {calendar_date} НЕ НАЙДЕНЫ в кэше. Пробуем спарсить заново.")
                try:
                    calendar_data = await self.parser.parse_calendar_day(calendar_date)
                    await self.cache_manager.set(calendar_date, calendar_data)
                    logger.info(f"Данные для {calendar_date} успешно спарсены и сохранены в кэш.")
                except Exception as e:
                    logger.error(f"Ошибка при попытке спарсить данные для {calendar_date}: {e}", exc_info=True)
                    return ApiResponse(
                        date=calendar_date.isoformat(),
                        response=None,
                        error=f"Данные лунного календаря для {calendar_date} не найдены в кэше и не могут быть получены: {str(e)}"
                    )
            
            # Теперь у нас есть данные календаря, но нет AI-ответа. Генерируем его.
            logger.info(f"Генерация AI-ответа для {calendar_date} и типа {user_type} в реальном времени...")
            
            # Получаем конфигурацию промпта
            prompt_config = self._get_prompt_config(user_type)
            
            # Подготавливаем сообщение пользователя
            user_message = self._prepare_user_message(calendar_data, user_type)
            
            # Получаем модели для данного типа пользователя
            models = self._get_models_for_user_type(user_type)
            
            # Генерируем ответ
            try:
                ai_response_text = await self.openrouter_client.generate_text(
                    system_message=prompt_config["system_message"],
                    user_message=user_message,
                    max_tokens=prompt_config["max_tokens"],
                    temperature=prompt_config["temperature"],
                    model=models[0] if models else None
                )
                
                # Очищаем ответ
                ai_response_text = await self._clean_model_response(ai_response_text)
                
                # Кэшируем ответ
                await self._cache_response(calendar_date, user_type, ai_response_text)
                
                logger.info(f"AI-ответ для {calendar_date} и типа {user_type} успешно сгенерирован и кэширован.")
                
                return ApiResponse(
                    date=calendar_date.isoformat(),
                    response=ai_response_text,
                    error=None
                )
            except Exception as e:
                logger.error(f"Ошибка при генерации AI-ответа для {calendar_date} и типа {user_type}: {e}", exc_info=True)
                return ApiResponse(
                    date=calendar_date.isoformat(),
                    response=None,
                    error=f"Ошибка при генерации AI-ответа: {str(e)}"
                )
            
        except Exception as e:
            logger.error(f"Общая ошибка в get_moon_calendar_response для {calendar_date} и типа {user_type}: {e}", exc_info=True)
            return ApiResponse(
                date=calendar_date.isoformat(),
                response=None,
                error=f"Внутренняя ошибка сервера при получении прогноза: {str(e)}"
            )

    async def background_generate_and_cache_ai_responses(self, calendar_date: date):
        """
        Фоновая генерация и кэширование AI-ответов для всех типов пользователей.
        Этот метод вызывается из MoonCalendarTasks.
        Предполагается, что спарсенные данные для calendar_date уже лежат в кэше.
        """
        logger.info(f"[BG_AI_GEN] Запуск генерации AI-ответов для {calendar_date}")
        
        try:
            # Получаем спарсенные данные календаря (должны быть уже в кэше из tasks.py,
            # или _get_calendar_data их спарсит/возьмет из кеша, если tasks.py еще не отработал или кеш устарел)
            current_parsed_data = await self._get_calendar_data(calendar_date)
            if not current_parsed_data:
                logger.error(f"[BG_AI_GEN] Спарсенные данные для {calendar_date} не найдены/не удалось получить. AI-генерация прервана.")
                return

            # Мы будем модифицировать копию, чтобы не влиять на другие возможные ссылки на current_parsed_data,
            # и чтобы собрать все AI ответы перед единовременной записью в кеш.
            # CacheManager.get() уже возвращает deepcopy, но для явности можно оставить.
            import copy # Убедитесь, что copy импортирован в начале файла, если еще нет
            data_to_cache_with_ai = copy.deepcopy(current_parsed_data)
            
            # Гарантируем наличие ключа для AI-ответов
            if "openrouter_responses" not in data_to_cache_with_ai:
                data_to_cache_with_ai["openrouter_responses"] = {}

            user_types_to_process = ["free", "premium"]
            at_least_one_ai_response_generated = False

            for user_type in user_types_to_process:
                logger.info(f"[BG_AI_GEN] Генерация для {calendar_date}, тип: {user_type}")
                try:
                    # Если мы хотим перезаписывать существующие AI ответы в кеше при каждом запуске фоновой задачи,
                    # то не нужно проверять их наличие здесь. Если хотим дописывать только отсутствующие - нужна проверка.
                    # Текущая логика подразумевает перезапись для свежести.

                    prompt_config = self._get_prompt_config(user_type)
                    # Важно: используем current_parsed_data (неизмененные данные, полученные в начале) для генерации промпта
                    user_message = self._prepare_user_message(current_parsed_data, user_type)
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
                            logger.error(f"[BG_AI_GEN] Ошибка при использовании модели {model_name} для {calendar_date} (тип: {user_type}): {e_model}", exc_info=False) # exc_info=False чтобы не засорять логи, если это частая ошибка модели
                            continue # Пробуем следующую модель
                    
                    if ai_response_text and selected_model:
                        # Добавляем AI ответ в структуру, которую будем кешировать целиком
                        data_to_cache_with_ai["openrouter_responses"][user_type] = ai_response_text
                        at_least_one_ai_response_generated = True
                        logger.info(f"[BG_AI_GEN] AI-ответ от {selected_model} для {calendar_date} (тип: {user_type}) подготовлен к кэшированию.")
                    else:
                        logger.error(f"[BG_AI_GEN] Не удалось получить AI-ответ ни от одной модели для {calendar_date} (тип: {user_type}). Последняя ошибка: {last_error_details}")
                        # Если для какого-то типа не удалось сгенерировать, возможно, стоит удалить старый ответ из data_to_cache_with_ai, если он там был
                        if user_type in data_to_cache_with_ai["openrouter_responses"]:
                            del data_to_cache_with_ai["openrouter_responses"][user_type]


                except Exception as e_user_type:
                    logger.error(f"[BG_AI_GEN] Ошибка при генерации AI-ответа для {calendar_date} (тип: {user_type}): {e_user_type}", exc_info=True)
                    if user_type in data_to_cache_with_ai["openrouter_responses"]:
                        del data_to_cache_with_ai["openrouter_responses"][user_type]
            
            # После цикла по user_type, сохраняем data_to_cache_with_ai ОДИН РАЗ.
            # Это сохранит исходные спарсенные данные вместе со всеми успешно сгенерированными AI-ответами.
            # Если какие-то AI-ответы не сгенерировались, их ключи будут отсутствовать в openrouter_responses.
            # CacheManager.set сам по себе обрабатывает обновление или создание новой записи.
            await self.cache_manager.set(calendar_date, data_to_cache_with_ai)
            logger.info(f"[BG_AI_GEN] Данные (спарсенные + AI-ответы) для {calendar_date} сохранены в кэш.")
            
            logger.info(f"[BG_AI_GEN] Завершение генерации AI-ответов для {calendar_date}")

        except Exception as e_main:
            logger.error(f"[BG_AI_GEN] Общая ошибка в background_generate_and_cache_ai_responses для {calendar_date}: {e_main}", exc_info=True) 