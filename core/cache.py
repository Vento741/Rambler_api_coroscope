"""
Менеджер кэша для API
"""
from datetime import datetime, date
from typing import Dict, Any, Optional
import logging
import copy

from config import BACKGROUND_TASKS

# Настройка логирования
logger = logging.getLogger(__name__)

class CacheManager:
    """Асинхронный менеджер кэша с TTL"""
    
    def __init__(self, update_cache_interval_minutes: int = BACKGROUND_TASKS["update_cache_interval_minutes"]):  # Увеличиваем время жизни кеша до 60 минут
        self._cache: Dict[str, Dict] = {}
        self._ttl_minutes = update_cache_interval_minutes
        
    def _generate_key(self, date_obj: date) -> str:
        """Генерация ключа для кэша"""
        return f"moon_calendar_{date_obj.isoformat()}"
    
    def _is_expired(self, cache_entry: Dict) -> bool:
        """Проверка истечения времени кэша"""
        cached_time = datetime.fromisoformat(cache_entry['cached_at'])
        return (datetime.now() - cached_time).total_seconds() > (self._ttl_minutes * 60)
    
    async def get(self, date_obj: date) -> Optional[Dict]:
        """Получение данных из кэша"""
        # Проверяем, что date_obj - это объект типа date
        if isinstance(date_obj, str):
            logger.warning(f"Передана строка вместо объекта date: {date_obj}. Преобразуем в date.")
            try:
                date_obj = datetime.fromisoformat(date_obj).date()
            except ValueError as e:
                logger.error(f"Не удалось преобразовать строку в date: {e}")
                return None
                
        key = self._generate_key(date_obj)
        
        if key in self._cache:
            cache_entry = self._cache[key]
            if not self._is_expired(cache_entry):
                logger.info(f"Кеш: {date_obj} найден")
                return copy.deepcopy(cache_entry['data'])  # Возвращаем копию данных
            else:
                # Удаляем устаревшие данные
                del self._cache[key]
                logger.info(f"Кеш: {date_obj} устарел")
        
        logger.info(f"Кеш: {date_obj} не найден")
        return None
    
    async def set(self, date_obj: date, data: Dict) -> None:
        """Сохранение данных в кэш"""
        # Проверяем, что date_obj - это объект типа date
        if isinstance(date_obj, str):
            logger.warning(f"Передана строка вместо объекта date: {date_obj}. Преобразуем в date.")
            try:
                date_obj = datetime.fromisoformat(date_obj).date()
            except ValueError as e:
                logger.error(f"Не удалось преобразовать строку в date: {e}")
                return
                
        key = self._generate_key(date_obj)
        
        # Проверяем, есть ли уже данные в кеше
        existing_data = None
        if key in self._cache and not self._is_expired(self._cache[key]):
            existing_data = self._cache[key]['data']
        
        # Если данные уже есть, обновляем только новые поля, сохраняя существующие
        if existing_data and isinstance(existing_data, dict) and isinstance(data, dict):
            # Создаем глубокую копию существующих данных
            merged_data = copy.deepcopy(existing_data)
            
            # Если в новых данных есть openrouter_responses, обрабатываем их отдельно
            if 'openrouter_responses' in data:
                if 'openrouter_responses' not in merged_data:
                    merged_data['openrouter_responses'] = {}
                
                # Обновляем или добавляем ответы для каждого типа пользователя
                for user_type, response in data['openrouter_responses'].items():
                    merged_data['openrouter_responses'][user_type] = response
                
                # Удаляем openrouter_responses из data, чтобы избежать дублирования
                data_copy = copy.deepcopy(data)
                del data_copy['openrouter_responses']
                
                # Обновляем остальные поля
                merged_data.update(data_copy)
            else:
                # Если нет openrouter_responses, просто обновляем данные
                merged_data.update(data)
            
            # Сохраняем объединенные данные
            self._cache[key] = {
                'data': merged_data,
                'cached_at': datetime.now().isoformat()
            }
        else:
            # Если данных нет или они не словари, просто сохраняем новые данные
            self._cache[key] = {
                'data': copy.deepcopy(data),  # Сохраняем копию данных
                'cached_at': datetime.now().isoformat()
            }
        
        logger.info(f"Кеш: {date_obj} установлен")
    
    async def add(self, key: str, value: Any, ttl_seconds: int = None) -> bool:
        """
        Атомарно добавляет запись только если её нет
        
        :param key: Ключ для добавления
        :param value: Значение для добавления
        :param ttl_seconds: Время жизни в секундах (если None, используется ttl_minutes)
        :return: True если запись добавлена, False если ключ уже существует
        """
        # Если ключ уже существует и не истек, возвращаем False
        if key in self._cache:
            cache_entry = self._cache[key]
            if not self._is_expired(cache_entry):
                logger.debug(f"Кеш: key {key} уже существует")
                return False
        
        # Добавляем новую запись
        ttl = ttl_seconds if ttl_seconds is not None else (self._ttl_minutes * 60)
        self._cache[key] = {
            'data': copy.deepcopy(value),
            'cached_at': datetime.now().isoformat(),
            'ttl': ttl
        }
        logger.debug(f"Кеш: key {key} добавлен")
        return True
    
    async def delete(self, key: str) -> bool:
        """
        Удаляет запись из кэша
        
        :param key: Ключ для удаления
        :return: True если запись была удалена, False если ключ не существует
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Кеш: key {key} удален")
            return True
        logger.debug(f"Кеш: key {key} не найден")
        return False
    
    async def clear_expired(self) -> None:
        """Очистка устаревших записей"""
        expired_keys = []
        for key, cache_entry in self._cache.items():
            if self._is_expired(cache_entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"Очищено {len(expired_keys)} устаревших записей в кэше") 