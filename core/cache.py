"""
Менеджер кэша для API
"""
from datetime import datetime, date
from typing import Dict, Any, Optional
import logging
import copy
import pickle
import aioredis
import config

# Настройка логирования
logger = logging.getLogger(__name__)

class CacheManager:
    """Асинхронный менеджер кэша с TTL на базе Redis"""

    def __init__(self, ttl_minutes: int = 60):
        """
        Инициализация менеджера кэша с подключением к Redis.

        :param ttl_minutes: Время жизни кэша в минутах.
        """
        self._ttl_seconds = ttl_minutes * 60
        self.redis: Optional[aioredis.Redis] = None # Будет инициализирован в connect()

    async def connect(self):
        """Устанавливает асинхронное подключение к Redis."""
        try:
            # Если соединение уже есть, сначала закроем его
            if self.redis:
                try:
                    await self.redis.close()
                    logger.info("Закрыто предыдущее соединение с Redis перед повторным подключением.")
                except Exception as e:
                    logger.warning(f"Ошибка при закрытии предыдущего соединения с Redis: {e}")
            
            # Используем from_url для подключения с пулом соединений
            self.redis = aioredis.from_url(config.REDIS_URL, encoding="utf-8", decode_responses=False) # decode_responses=False для работы с pickle
            logger.info(f"Успешно подключено к Redis по адресу: {config.REDIS_URL}")
            
            # Проверяем соединение
            await self.redis.ping()
            logger.info("Redis connection ping successful.")
        except aioredis.RedisError as e:
            logger.critical(f"НЕ УДАЛОСЬ ПОДКЛЮЧИТЬСЯ К REDIS по адресу {config.REDIS_URL}: {e}", exc_info=True)
            self.redis = None
        except Exception as e:
            logger.critical(f"Неожиданная ошибка при подключении к REDIS по адресу {config.REDIS_URL}: {e}", exc_info=True)
            # В продакшене, возможно, стоит здесь предпринять другие действия (например, завершить приложение)
            # В рамках текущей задачи просто логируем критическую ошибку.
            self.redis = None # Убедимся, что self.redis None при ошибке

    async def close(self):
        """Закрывает соединение с Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Соединение с Redis закрыто.")

    def _generate_key(self, date_obj: date) -> str:
        """Генерация ключа для кэша"""
        return f"moon_calendar_{date_obj.isoformat()}"

    async def get(self, date_obj: date) -> Optional[Dict]:
        """
        Получение данных из кэша Redis.

        :param date_obj: Дата, для которой нужно получить данные.
        :return: Данные из кэша или None, если нет данных или Redis недоступен.
        """
        if not self.redis:
            logger.error("Попытка GET из кэша, но Redis не подключен. Пробуем переподключиться...")
            await self.connect()
            if not self.redis:
                logger.error("Переподключение к Redis не удалось. GET невозможен.")
                return None

        key = self._generate_key(date_obj)
        logger.info(f"Попытка кэширования GET для ключа: {key}")

        try:
            cached_data_bytes = await self.redis.get(key)

            if cached_data_bytes is not None:
                try:
                    # Десериализация данных из байтов
                    cached_data = pickle.loads(cached_data_bytes)
                    logger.info(f"Получен HIT для ключа: {key} (date: {date_obj})")
                    # Redis TTL управляет сроком жизни, отдельная проверка не нужна
                    return cached_data
                except (pickle.UnpicklingError, EOFError, AttributeError) as e:
                    logger.error(f"Ошибка десериализации данных для ключа {key}: {e}. Удаляю некорректную запись.", exc_info=True)
                    await self.redis.delete(key) # Удаляем поврежденную запись
                    logger.info(f"Удалена некорректная запись для ключа {key}")
                    return None # Возвращаем None после удаления некорректных данных
            else:
                logger.info(f"Кэш MISS для ключа: {key} (date: {date_obj})")
                return None

        except aioredis.exceptions.ConnectionError as e:
            logger.error(f"Ошибка соединения с Redis при GET для ключа {key}: {e}", exc_info=True)
            logger.info("Пробуем переподключиться к Redis...")
            await self.connect()
            if self.redis:
                logger.info("Переподключение к Redis успешно. Повторяем GET...")
                return await self.get(date_obj) # Рекурсивно повторяем запрос после переподключения
            return None
        except aioredis.exceptions.RedisError as e:
            logger.error(f"Redis error during GET operation for key {key}: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка в CacheManager.get для ключа {key}: {e}", exc_info=True)
            return None

    async def set(self, date_obj: date, data: Dict) -> None:
        """
        Сохранение данных в кэш Redis с установленным TTL.
        Обрабатывает слияние данных при частичном обновлении (например, добавлении AI-ответа).

        :param date_obj: Дата, для которой нужно сохранить данные.
        :param data: Данные для сохранения (словарь).
        """
        if not self.redis:
            logger.error("Попытка SET в кэш, но Redis не подключен. Пробуем переподключиться...")
            await self.connect()
            if not self.redis:
                logger.error("Переподключение к Redis не удалось. SET невозможен.")
                return

        key = self._generate_key(date_obj)
        logger.info(f"Попытка кэширования SET для ключа: {key} (date: {date_obj})")
        logger.debug(f"Данные для сохранения (начало): {str(data)[:200]}...") # Логируем начало данных

        try:
            # Перед сохранением новых данных, попробуем получить текущие из Redis
            # Это нужно для реализации логики слияния данных (парсинг + AI-ответы)
            existing_data_bytes = await self.redis.get(key)
            existing_data = None
            if existing_data_bytes:
                try:
                     existing_data = pickle.loads(existing_data_bytes)
                     # Проверяем, что существующие данные - это словарь, иначе игнорируем их
                     if not isinstance(existing_data, dict):
                         logger.warning(f"Существующие данные для ключа {key} не являются словарем. Игнорирую их.")
                         existing_data = None
                except (pickle.UnpicklingError, EOFError, AttributeError) as e:
                     logger.warning(f"Ошибка десериализации существующих данных для ключа {key} при SET: {e}. Игнорирую их.", exc_info=True)
                     existing_data = None # Игнорируем поврежденные данные

            data_to_save = data # Начинаем с данных, которые переданы в SET

            # Логика слияния данных:
            # Если существующие данные есть И это словари, пытаемся их объединить.
            # Предполагается, что data_to_save уже содержит спарсенные данные (если они были получены)
            # и может содержать новый AI-ответ вложенный в 'openrouter_responses'.
            # Цель: сохранить ВСЕ AI-ответы, которые уже есть в кеше, если их нет в текущих data_to_save.
            if existing_data and isinstance(existing_data, dict) and isinstance(data_to_save, dict):
                # Создаем копию существующих данных, чтобы не модифицировать их напрямую, если они используются где-то еще (хотя CacheManager.get уже возвращает копию)
                merged_data = existing_data #existing_data уже является копией из get()

                # Если в новых данных есть openrouter_responses, сливаем их с существующими
                if 'openrouter_responses' in data_to_save and isinstance(data_to_save['openrouter_responses'], dict):
                     if 'openrouter_responses' not in merged_data or not isinstance(merged_data['openrouter_responses'], dict):
                        merged_data['openrouter_responses'] = {}

                     # Объединяем ответы для разных типов пользователей
                     merged_data['openrouter_responses'].update(data_to_save['openrouter_responses'])

                     # Удаляем openrouter_responses из data_to_save, чтобы избежать их дублирования
                     # (остальные поля из data_to_save будут просто обновлены)
                     data_without_ai_responses = {k: v for k, v in data_to_save.items() if k != 'openrouter_responses'}
                else:
                     # Если в новых данных нет openrouter_responses, используем data_to_save как есть
                     # и сохраняем существующие AI-ответы из merged_data (если они были)
                     data_without_ai_responses = data_to_save # просто переименовываем для ясности

                # Обновляем остальные поля в merged_data из data_to_save
                # Важно: это перезапишет не-AI поля из existing_data данными из data_to_save
                # Это правильно, т.к. SET вызывается для сохранения свежих данных (либо парсинга, либо после парсинга+AI)
                merged_data.update(data_without_ai_responses)

                data_to_save = merged_data # Теперь сохраняем объединенные данные

            # Сериализация данных в байты
            pickled_data = pickle.dumps(data_to_save)

            # Сохранение данных в Redis с TTL
            await self.redis.set(key, pickled_data, ex=self._ttl_seconds)

            logger.info(f"Кэширование SET успешно для ключа: {key} (date: {date_obj}) с TTL {self._ttl_seconds} сек.")

        except aioredis.exceptions.ConnectionError as e:
            logger.error(f"Ошибка соединения с Redis при SET для ключа {key}: {e}", exc_info=True)
            logger.info("Пробуем переподключиться к Redis...")
            await self.connect()
            if self.redis:
                logger.info("Переподключение к Redis успешно. Повторяем SET...")
                await self.set(date_obj, data) # Рекурсивно повторяем запрос после переподключения
        except aioredis.exceptions.RedisError as e:
            logger.error(f"Redis error during SET operation for key {key}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Неожиданная ошибка в CacheManager.set для ключа {key}: {e}", exc_info=True)

    # Метод clear_expired теперь может быть упрощен или удален,
    # так как Redis автоматически удаляет ключи по TTL.
    # Если вам нужна функция очистки для других целей (например, ручного сброса),
    # ее можно адаптировать для удаления ключей по шаблону, но для TTL она не нужна.
    # Оставляю заглушку, чтобы не ломать код, который может ее вызывать, но по сути она не делает ничего для TTL.
    async def clear_expired(self) -> None:
        """
        Заглушка для совместимости. Redis автоматически удаляет ключи по TTL.
        Этот метод ничего не делает для TTL-очистки.
        """
        logger.debug("CacheManager.clear_expired вызван, но Redis управляет TTL автоматически.")
        # Если нужна очистка по шаблону или другим критериям,
        # здесь можно добавить логику с использованием await self.redis.delete() или других команд.
        pass 