"""
Менеджер кэша для API - исправленная версия
"""
from datetime import datetime, date
from typing import Dict, Any, Optional, Union
import logging
import copy

from config import BACKGROUND_TASKS

logger = logging.getLogger(__name__)

class CacheManager:
    """Асинхронный менеджер кэша с TTL и улучшенной обработкой типов"""
    
    def __init__(self, update_cache_interval_minutes: int = BACKGROUND_TASKS["update_cache_interval_minutes"]):
        self._cache: Dict[str, Dict] = {}
        self._ttl_minutes = update_cache_interval_minutes
    
    def _normalize_date(self, date_input: Union[str, date, datetime]) -> date:
        """Нормализация входных данных в объект date"""
        if isinstance(date_input, date):
            return date_input
        elif isinstance(date_input, datetime):
            return date_input.date()
        elif isinstance(date_input, str):
            try:
                # Пробуем несколько форматов
                if 'T' in date_input or ' ' in date_input:
                    return datetime.fromisoformat(date_input.replace('Z', '+00:00')).date()
                else:
                    return datetime.strptime(date_input, '%Y-%m-%d').date()
            except ValueError as e:
                logger.error(f"Не удалось преобразовать строку '{date_input}' в date: {e}")
                raise ValueError(f"Неверный формат даты: {date_input}")
        else:
            raise TypeError(f"Неподдерживаемый тип для даты: {type(date_input)}")
    
    def _generate_key(self, date_obj: Union[str, date, datetime]) -> str:
        """Генерация ключа для кэша с нормализацией типов"""
        try:
            normalized_date = self._normalize_date(date_obj)
            return f"moon_calendar_{normalized_date.isoformat()}"
        except Exception as e:
            logger.error(f"Критическая ошибка в _generate_key для {date_obj}: {e}")
            # Fallback для отладки
            if isinstance(date_obj, str):
                return f"moon_calendar_{date_obj}"
            raise
    
    def _is_expired(self, cache_entry: Dict) -> bool:
        """Проверка истечения времени кэша"""
        try:
            cached_time = datetime.fromisoformat(cache_entry['cached_at'])
            ttl_seconds = cache_entry.get('ttl', self._ttl_minutes * 60)
            return (datetime.now() - cached_time).total_seconds() > ttl_seconds
        except (KeyError, ValueError) as e:
            logger.warning(f"Ошибка при проверке TTL кэша: {e}")
            return True  # Считаем истекшим при ошибке
    
    async def get(self, date_obj: Union[str, date, datetime]) -> Optional[Dict]:
        """Получение данных из кэша"""
        try:
            key = self._generate_key(date_obj)
            
            if key in self._cache:
                cache_entry = self._cache[key]
                if not self._is_expired(cache_entry):
                    logger.info(f"Кеш найден для: {date_obj}")
                    return copy.deepcopy(cache_entry['data'])
                else:
                    del self._cache[key]
                    logger.info(f"Кеш устарел для: {date_obj}")
            
            logger.info(f"Кеш не найден для: {date_obj}")
            return None
            
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка при получении из кэша для {date_obj}: {e}")
            return None
    
    async def set(self, date_obj: Union[str, date, datetime], data: Dict) -> None:
        """Сохранение данных в кэш"""
        try:
            key = self._generate_key(date_obj)
            
            # Проверяем существующие данные
            existing_data = None
            if key in self._cache and not self._is_expired(self._cache[key]):
                existing_data = self._cache[key]['data']
            
            # Умное слияние данных
            final_data = self._merge_cache_data(existing_data, data)
            
            self._cache[key] = {
                'data': copy.deepcopy(final_data),
                'cached_at': datetime.now().isoformat(),
                'ttl': self._ttl_minutes * 60
            }
            
            logger.info(f"Кеш установлен для: {date_obj}")
            
        except (ValueError, TypeError) as e:
            logger.error(f"Ошибка при сохранении в кэш для {date_obj}: {e}")
    
    def _merge_cache_data(self, existing: Optional[Dict], new: Dict) -> Dict:
        """Умное слияние данных кэша"""
        if not existing or not isinstance(existing, dict) or not isinstance(new, dict):
            return new
        
        merged = copy.deepcopy(existing)
        
        # Специальная обработка для openrouter_responses
        if 'openrouter_responses' in new:
            if 'openrouter_responses' not in merged:
                merged['openrouter_responses'] = {}
            
            for user_type, response in new['openrouter_responses'].items():
                merged['openrouter_responses'][user_type] = response
            
            # Обновляем остальные поля
            new_copy = copy.deepcopy(new)
            del new_copy['openrouter_responses']
            merged.update(new_copy)
        else:
            merged.update(new)
        
        return merged
    
    async def add(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        """Атомарное добавление записи"""
        if key in self._cache and not self._is_expired(self._cache[key]):
            logger.debug(f"Ключ уже существует: {key}")
            return False
        
        ttl = ttl_seconds if ttl_seconds is not None else (self._ttl_minutes * 60)
        self._cache[key] = {
            'data': copy.deepcopy(value),
            'cached_at': datetime.now().isoformat(),
            'ttl': ttl
        }
        
        logger.debug(f"Ключ добавлен: {key}")
        return True
    
    async def delete(self, key: str) -> bool:
        """Удаление записи из кэша"""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Ключ удален: {key}")
            return True
        
        logger.debug(f"Ключ не найден: {key}")
        return False
    
    async def clear_expired(self) -> None:
        """Очистка устаревших записей"""
        expired_keys = [
            key for key, entry in self._cache.items() 
            if self._is_expired(entry)
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"Очищено {len(expired_keys)} устаревших записей")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Статистика кэша для мониторинга"""
        total_entries = len(self._cache)
        expired_count = sum(1 for entry in self._cache.values() if self._is_expired(entry))
        
        return {
            'total_entries': total_entries,
            'active_entries': total_entries - expired_count,
            'expired_entries': expired_count,
            'cache_hit_ratio': None  # Можно добавить счетчики для расчета
        }