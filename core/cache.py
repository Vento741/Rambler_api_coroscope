"""
Менеджер кэша для API
"""
from datetime import datetime, date
from typing import Dict, Any, Optional
import logging

# Настройка логирования
logger = logging.getLogger(__name__)

class CacheManager:
    """Асинхронный менеджер кэша с TTL"""
    
    def __init__(self, ttl_minutes: int = 30):
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
        
        if key in self._cache:
            cache_entry = self._cache[key]
            if not self._is_expired(cache_entry):
                logger.info(f"Cache HIT for {date_obj}")
                return cache_entry['data']
            else:
                # Удаляем устаревшие данные
                del self._cache[key]
                logger.info(f"Cache EXPIRED for {date_obj}")
        
        logger.info(f"Cache MISS for {date_obj}")
        return None
    
    async def set(self, date_obj: date, data: Dict) -> None:
        """Сохранение данных в кэш"""
        key = self._generate_key(date_obj)
        self._cache[key] = {
            'data': data,
            'cached_at': datetime.now().isoformat()
        }
        logger.info(f"Cache SET for {date_obj}")
    
    async def clear_expired(self) -> None:
        """Очистка устаревших записей"""
        expired_keys = []
        for key, cache_entry in self._cache.items():
            if self._is_expired(cache_entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"Cleared {len(expired_keys)} expired cache entries") 