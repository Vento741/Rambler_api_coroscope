"""
Система надежной обработки дат для лунного календаря
"""
from datetime import date, datetime, timedelta
from typing import Union, Optional
import logging
from functools import wraps

logger = logging.getLogger(__name__)

class DateHandler:
    """Централизованная обработка дат для всей системы"""
    
    @staticmethod
    def normalize_date(date_input: Union[str, date, datetime, None]) -> Optional[date]:
        """
        Единая точка нормализации всех входных дат
        
        :param date_input: Входные данные любого типа
        :return: Нормализованный объект date или None при ошибке
        """
        if date_input is None:
            return None
            
        if isinstance(date_input, date):
            return date_input
            
        if isinstance(date_input, datetime):
            return date_input.date()
            
        if isinstance(date_input, str):
            try:
                # Обработка различных форматов строк
                date_input = date_input.strip()
                
                if 'T' in date_input or ' ' in date_input:
                    # ISO формат с временем
                    return datetime.fromisoformat(date_input.replace('Z', '+00:00')).date()
                else:
                    # Простой формат даты
                    return datetime.strptime(date_input, '%Y-%m-%d').date()
                    
            except (ValueError, TypeError) as e:
                logger.error(f"Ошибка парсинга даты '{date_input}': {e}")
                return None
        
        logger.error(f"Неподдерживаемый тип для даты: {type(date_input)}")
        return None
    
    @staticmethod
    def safe_date(func):
        """
        Декоратор для автоматической нормализации дат в методах
        Применяется к первому аргументу после self
        """
        @wraps(func)
        async def wrapper(self, date_arg, *args, **kwargs):
            normalized_date = DateHandler.normalize_date(date_arg)
            if normalized_date is None:
                raise ValueError(f"Не удалось нормализовать дату: {date_arg}")
            return await func(self, normalized_date, *args, **kwargs)
        return wrapper

# Обновленный CacheManager с интегрированной обработкой дат
class RobustCacheManager:
    """Кэш-менеджер с надежной обработкой дат"""
    
    def __init__(self, ttl_minutes: int = 60):
        self._cache = {}
        self._ttl_minutes = ttl_minutes
        self.date_handler = DateHandler()
    
    def _generate_key(self, date_obj: date) -> str:
        """Генерация ключа - принимает только нормализованные объекты date"""
        return f"moon_calendar_{date_obj.isoformat()}"
    
    def _is_expired(self, cache_entry: dict) -> bool:
        """Проверка истечения TTL"""
        try:
            cached_time = datetime.fromisoformat(cache_entry['cached_at'])
            ttl_seconds = cache_entry.get('ttl', self._ttl_minutes * 60)
            return (datetime.now() - cached_time).total_seconds() > ttl_seconds
        except (KeyError, ValueError):
            return True
    
    @DateHandler.safe_date
    async def get(self, date_obj: date) -> Optional[dict]:
        """Получение из кэша с автоматической нормализацией даты"""
        key = self._generate_key(date_obj)
        
        if key not in self._cache:
            logger.info(f"Кэш не найден: {date_obj}")
            return None
            
        cache_entry = self._cache[key]
        if self._is_expired(cache_entry):
            del self._cache[key]
            logger.info(f"Кэш устарел: {date_obj}")
            return None
        
        logger.info(f"Кэш найден: {date_obj}")
        return cache_entry['data'].copy() if isinstance(cache_entry['data'], dict) else cache_entry['data']
    
    @DateHandler.safe_date
    async def set(self, date_obj: date, data: dict) -> None:
        """Сохранение в кэш с автоматической нормализацией даты"""
        key = self._generate_key(date_obj)
        
        # Умное слияние с существующими данными
        final_data = data
        if key in self._cache and not self._is_expired(self._cache[key]):
            existing = self._cache[key]['data']
            if isinstance(existing, dict) and isinstance(data, dict):
                final_data = self._merge_data(existing, data)
        
        self._cache[key] = {
            'data': final_data.copy() if isinstance(final_data, dict) else final_data,
            'cached_at': datetime.now().isoformat(),
            'ttl': self._ttl_minutes * 60
        }
        
        logger.info(f"Кэш установлен: {date_obj}")
    
    def _merge_data(self, existing: dict, new: dict) -> dict:
        """Умное слияние данных кэша"""
        merged = existing.copy()
        
        # Специальная логика для openrouter_responses
        if 'openrouter_responses' in new:
            if 'openrouter_responses' not in merged:
                merged['openrouter_responses'] = {}
            
            for user_type, response in new['openrouter_responses'].items():
                merged['openrouter_responses'][user_type] = response
            
            # Обновляем остальные поля
            new_without_responses = {k: v for k, v in new.items() if k != 'openrouter_responses'}
            merged.update(new_without_responses)
        else:
            merged.update(new)
        
        return merged

# Обновленный MoonCalendarTasks
class RobustMoonCalendarTasks:
    """Фоновые задачи с надежной обработкой дат"""
    
    def __init__(self, cache_manager, parser, openrouter_service):
        self.cache_manager = cache_manager
        self.parser = parser
        self.openrouter_service = openrouter_service
        self._lock_key = "moon_calendar_task_lock"
        self._lock_ttl = 60
    
    async def _acquire_lock(self) -> bool:
        """Получение блокировки задачи"""
        lock_id = f"task_{datetime.now().timestamp()}"
        return await self.cache_manager.add(self._lock_key, lock_id, self._lock_ttl)
    
    async def _release_lock(self):
        """Освобождение блокировки"""
        await self.cache_manager.delete(self._lock_key)
    
    async def update_calendar_cache_and_generate_ai_responses(self):
        """Основная логика обновления с надежной обработкой дат"""
        if not await self._acquire_lock():
            logger.info("Задача уже выполняется другим процессом")
            return
        
        try:
            # Явное создание объектов date
            today = date.today()
            tomorrow = date.today() + timedelta(days=1)
            
            logger.info(f"Обновление данных для {today}, {tomorrow}")
            
            for calendar_date in [today, tomorrow]:
                await self._process_single_date(calendar_date)
                
        except Exception as e:
            logger.error(f"Критическая ошибка в фоновой задаче: {e}", exc_info=True)
        finally:
            await self._release_lock()
    
    async def _process_single_date(self, calendar_date: date):
        """Обработка одной даты"""
        try:
            # Парсинг данных
            logger.info(f"Парсинг данных: {calendar_date}")
            calendar_data = await self.parser.parse_calendar_day(calendar_date)
            await self.cache_manager.set(calendar_date, calendar_data)
            
            # Генерация AI ответов
            logger.info(f"Генерация AI ответов: {calendar_date}")
            await self.openrouter_service.background_generate_and_cache_ai_responses(calendar_date)
            
            logger.info(f"Обработка завершена: {calendar_date}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки {calendar_date}: {e}", exc_info=True)

# Обновленный OpenRouter сервис
class RobustOpenRouterService:
    """OpenRouter сервис с надежной обработкой дат"""
    
    def __init__(self, cache_manager, parser, openrouter_client, prompts_config):
        self.cache_manager = cache_manager
        self.parser = parser
        self.openrouter_client = openrouter_client
        self.prompts_config = prompts_config
        self.date_handler = DateHandler()
    
    @DateHandler.safe_date
    async def get_moon_calendar_response(self, calendar_date: date, user_type: str):
        """Получение ответа с автоматической нормализацией даты"""
        try:
            cached_response = await self._get_cached_response(calendar_date, user_type)
            
            if cached_response:
                return {
                    "success": True,
                    "data": cached_response,
                    "cached": True,
                    "model": "cached_response"
                }
            
            # Проверка наличия базовых данных
            base_data = await self.cache_manager.get(calendar_date)
            if base_data:
                return {
                    "success": False,
                    "error": f"AI-ответ для {calendar_date} еще не готов",
                    "model": "processing"
                }
            
            return {
                "success": False,
                "error": f"Данные для {calendar_date} еще не обработаны",
                "model": "no_data"
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения ответа для {calendar_date}: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Внутренняя ошибка: {str(e)}"
            }
    
    @DateHandler.safe_date
    async def background_generate_and_cache_ai_responses(self, calendar_date: date):
        """Фоновая генерация AI ответов с автоматической нормализацией даты"""
        logger.info(f"Запуск AI генерации: {calendar_date}")
        
        try:
            # Получение базовых данных
            calendar_data = await self.cache_manager.get(calendar_date)
            if not calendar_data:
                logger.error(f"Базовые данные не найдены: {calendar_date}")
                return
            
            # Генерация для каждого типа пользователя
            for user_type in ["free", "premium"]:
                await self._generate_for_user_type(calendar_date, user_type, calendar_data)
                
        except Exception as e:
            logger.error(f"Ошибка AI генерации для {calendar_date}: {e}", exc_info=True)
    
    async def _generate_for_user_type(self, calendar_date: date, user_type: str, calendar_data: dict):
        """Генерация ответа для конкретного типа пользователя"""
        try:
            # Проверка существующего ответа
            if await self._get_cached_response(calendar_date, user_type):
                logger.info(f"AI ответ уже существует: {calendar_date} ({user_type})")
                return
            
            # Подготовка запроса
            prompt_config = self.prompts_config.get(user_type, self.prompts_config["free"])
            user_message = self._prepare_user_message(calendar_data, user_type)
            
            # Генерация ответа
            response = await self._generate_ai_response(
                prompt_config, user_message, user_type
            )
            
            if response:
                await self._cache_response(calendar_date, user_type, response)
                logger.info(f"AI ответ сохранен: {calendar_date} ({user_type})")
            else:
                logger.error(f"Не удалось сгенерировать ответ: {calendar_date} ({user_type})")
                
        except Exception as e:
            logger.error(f"Ошибка генерации для {user_type}: {e}", exc_info=True)
    
    @DateHandler.safe_date  
    async def _get_cached_response(self, calendar_date: date, user_type: str) -> Optional[str]:
        """Получение кэшированного ответа"""
        cached_data = await self.cache_manager.get(calendar_date)
        
        if not isinstance(cached_data, dict):
            return None
            
        responses = cached_data.get("openrouter_responses", {})
        return responses.get(user_type)
    
    @DateHandler.safe_date
    async def _cache_response(self, calendar_date: date, user_type: str, response: str):
        """Кэширование ответа"""
        cache_data = {
            "openrouter_responses": {
                user_type: response
            }
        }
        await self.cache_manager.set(calendar_date, cache_data)
    
    def _prepare_user_message(self, calendar_data: dict, user_type: str) -> str:
        """Подготовка сообщения для AI"""
        if user_type == "free":
            moon_day = calendar_data.get("moon_days", [{}])[0]
            return f"""Дата: {calendar_data.get('date')}
Фаза луны: {calendar_data.get('moon_phase')}
Лунный день: {moon_day.get('name', 'Не определен')}
Информация: {moon_day.get('info', 'Отсутствует')}

Важно: Используй простые символы, избегай сложного форматирования."""
        
        # Для premium - расширенная информация
        moon_days = "\n".join([
            f"{day.get('name', '')}: {day.get('info', '')}"
            for day in calendar_data.get("moon_days", [])
        ])
        
        recommendations = "\n".join([
            f"{title}: {text}"
            for title, text in calendar_data.get("recommendations", {}).items()
        ])
        
        return f"""Дата: {calendar_data.get('date')}
Фаза луны: {calendar_data.get('moon_phase')}

Лунные дни:
{moon_days}

Рекомендации:
{recommendations}

Важно: Используй простые символы, избегай сложного форматирования."""
    
    async def _generate_ai_response(self, prompt_config: dict, user_message: str, user_type: str) -> Optional[str]:
        """Генерация AI ответа с fallback по моделям"""
        models = self._get_models_for_user_type(user_type)
        
        for model in models:
            try:
                response = await self.openrouter_client.generate_text(
                    system_message=prompt_config["system_message"],
                    user_message=user_message,
                    max_tokens=prompt_config["max_tokens"],
                    temperature=prompt_config["temperature"],
                    model=model
                )
                
                if response and response.strip():
                    return self._clean_response(response)
                    
            except Exception as e:
                logger.error(f"Ошибка модели {model}: {e}")
                continue
        
        return None
    
    def _get_models_for_user_type(self, user_type: str) -> list:
        """Получение списка моделей для типа пользователя"""
        models_map = {
            "free": [
                "google/gemini-2.0-flash-001",
                "google/gemini-2.0-flash-exp:free",
                "deepseek-r1-0528-qwen3-8b:free"
            ],
            "premium": [
                "google/gemini-2.0-flash-001",
                "qwen/qwen2.5-vl-72b-instruct:free",
                "deepseek-r1-0528-qwen3-8b:free"
            ]
        }
        return models_map.get(user_type, models_map["free"])
    
    def _clean_response(self, response: str) -> str:
        """Очистка ответа от проблемных символов"""
        import re
        
        # Удаление markdown форматирования
        cleaned = re.sub(r'\*\*(.+?)\*\*', r'\1', response)
        cleaned = re.sub(r'```.*?```', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'`(.+?)`', r'\1', cleaned)
        
        # Нормализация разделителей
        cleaned = re.sub(r'[-=*]{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned.strip() or "Техническая ошибка. Попробуйте позже."