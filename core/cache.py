"""
Менеджер кэша для API
"""
from datetime import datetime, date
from typing import Dict, Any, Optional
import logging
import copy

# Настройка логирования
logger = logging.getLogger(__name__)

class CacheManager:
    """Асинхронный менеджер кэша с TTL"""
    
    def __init__(self, ttl_minutes: int = 60):  # Увеличиваем время жизни кеша до 60 минут
        self._cache: Dict[str, Dict] = {}
        self._ttl_minutes = ttl_minutes
        
    def _generate_key(self, date_obj: date) -> str:
        """Генерация ключа для кэша"""
        return f"moon_calendar_{date_obj.isoformat()}"
    
    def _is_expired(self, cache_entry: Dict) -> bool:
        """Проверка истечения времени кэша"""
        cached_time = datetime.fromisoformat(cache_entry['cached_at'])
        return (datetime.now() - cached_time).total_seconds() > (self._ttl_minutes * 60)
    
    async def get(self, date_obj: date) -> Optional[Dict]:
        """Получение данных из кэша"""
        key = self._generate_key(date_obj)
        logger.info(f"Попытка кэширования GET для ключа: {key}. Текущий размер кэша: {len(self._cache)}")
        
        if key in self._cache:
            cache_entry = self._cache[key]
            if not self._is_expired(cache_entry):
                logger.info(f"Получен HIT для ключа: {key} (date: {date_obj})")
                return copy.deepcopy(cache_entry['data'])  # Возвращаем копию данных
            else:
                # Удаляем устаревшие данные
                logger.warning(f"Кэш истек для ключа: {key} (date: {date_obj}). Удаляем сейчас.")
                del self._cache[key]
                logger.info(f"После удаления устаревших данных для {key}. Текущий размер кэша: {len(self._cache)}")
        
        logger.info(f"Кэш MISS для ключа: {key} (date: {date_obj})")
        return None
    
    async def set(self, date_obj: date, data: Dict) -> None:
        """Сохранение данных в кэш"""
        key = self._generate_key(date_obj)
        logger.info(f"Попытка кэширования SET для ключа: {key} (date: {date_obj}). Ключи данных: {list(data.keys()) if isinstance(data, dict) else 'Не словарь'}. Текущий размер кэша перед сохранением: {len(self._cache)}")
        
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
        
        logger.info(f"Кэширование SET успешно для ключа: {key} (date: {date_obj}). Текущий размер кэша после сохранения: {len(self._cache)}")
    
    async def clear_expired(self) -> None:
        """Очистка устаревших записей"""
        expired_keys = []
        logger.debug(f"Запуск clear_expired. Текущий размер кэша: {len(self._cache)}")
        for key, cache_entry in list(self._cache.items()): # Iterate over a copy of items for safe deletion
            if self._is_expired(cache_entry):
                logger.info(f"clear_expired: Найден устаревший ключ {key} (cached_at: {cache_entry['cached_at']})")
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"Очищено {len(expired_keys)} устаревших записей кэша. Текущий размер кэша: {len(self._cache)}")
        else:
            logger.debug(f"clear_expired: Не найдено устаревших записей. Текущий размер кэша: {len(self._cache)}") 