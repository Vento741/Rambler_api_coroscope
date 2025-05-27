"""
Клиент для работы с OpenRouter API
"""
import logging
import json
from typing import Dict, List, Any, Optional, Union
import asyncio

import aiohttp
from fastapi import HTTPException

from core.exceptions import NetworkException

logger = logging.getLogger(__name__)

class OpenRouterClient:
    """
    Клиент для работы с OpenRouter API с механизмом ротации ключей и моделей
    """
    
    def __init__(
        self, 
        api_url: str,
        api_keys: List[str],
        models: List[str],
        timeout: int = 30
    ):
        """
        Инициализация клиента
        
        :param api_url: URL API OpenRouter
        :param api_keys: Список API ключей
        :param models: Список моделей
        :param timeout: Таймаут запроса в секундах
        """
        self.api_url = api_url
        self.api_keys = api_keys
        self.models = models
        self.timeout = timeout
        
        self.current_key_index = 0
        self.current_model_index = 0
        
        logger.info(f"OpenRouter клиент инициализирован с {len(api_keys)} ключами и {len(models)} моделями")
    
    def _get_current_key(self) -> str:
        """Получение текущего API ключа"""
        return self.api_keys[self.current_key_index]
    
    def _get_current_model(self) -> str:
        """Получение текущей модели"""
        return self.models[self.current_model_index]
    
    def _rotate_key(self) -> str:
        """Ротация API ключа"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.info(f"Ротация API ключа на индекс {self.current_key_index}")
        return self._get_current_key()
    
    def _rotate_model(self) -> str:
        """Ротация модели"""
        self.current_model_index = (self.current_model_index + 1) % len(self.models)
        logger.info(f"Ротация модели на индекс {self.current_model_index}")
        # При смене модели сбрасываем индекс ключа на 0
        self.current_key_index = 0
        return self._get_current_model()
    
    def _prepare_headers(self) -> Dict[str, str]:
        """Подготовка заголовков запроса"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._get_current_key()}"
        }
    
    async def make_request(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: int = 500,
        temperature: float = 0.7,
        model: Optional[str] = None,
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Выполнение запроса к API OpenRouter
        
        :param messages: Список сообщений для модели
        :param max_tokens: Максимальное количество токенов в ответе
        :param temperature: Температура генерации
        :param model: Модель (если None, используется текущая)
        :param retry_count: Количество попыток при ошибке
        :return: Ответ API
        """
        if not model:
            model = self._get_current_model()
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        for attempt in range(retry_count):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    async with session.post(
                        self.api_url,
                        headers=self._prepare_headers(),
                        json=payload
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        
                        # Обработка ошибок API
                        error_text = await response.text()
                        logger.error(f"OpenRouter API ошибка: {response.status}, {error_text}")
                        
                        if response.status == 401 or response.status == 403:
                            # Проблема с API ключом - ротация ключа
                            self._rotate_key()
                        elif response.status == 404:
                            # Проблема с моделью - ротация модели
                            self._rotate_model()
                        else:
                            # Другие ошибки
                            logger.error(f"Неизвестная ошибка API: {response.status}")
                            
                        # Если это последняя попытка, выбрасываем исключение
                        if attempt == retry_count - 1:
                            raise NetworkException(f"Ошибка OpenRouter API: {response.status}, {error_text}")
                            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"Ошибка сети при запросе к OpenRouter: {e}")
                
                # Если это последняя попытка, выбрасываем исключение
                if attempt == retry_count - 1:
                    raise NetworkException(f"Ошибка сети при запросе к OpenRouter: {str(e)}")
                
                # Ротация ключа при ошибке сети
                self._rotate_key()
                
                # Пауза перед повторной попыткой
                await asyncio.sleep(1)
    
    def extract_response_text(self, response: Dict[str, Any]) -> str:
        """
        Извлечение текста ответа из ответа API
        
        :param response: Ответ API
        :return: Текст ответа
        """
        try:
            return response.get("choices", [{}])[0].get("message", {}).get("content", "")
        except (IndexError, KeyError, AttributeError) as e:
            logger.error(f"Ошибка при извлечении текста ответа: {e}")
            return ""
    
    async def generate_text(
        self,
        system_message: str,
        user_message: str,
        max_tokens: int = 500,
        temperature: float = 0.7
    ) -> str:
        """
        Генерация текста с помощью OpenRouter API
        
        :param system_message: Системное сообщение
        :param user_message: Сообщение пользователя
        :param max_tokens: Максимальное количество токенов в ответе
        :param temperature: Температура генерации
        :return: Сгенерированный текст
        """
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        try:
            response = await self.make_request(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return self.extract_response_text(response)
        except Exception as e:
            logger.error(f"Ошибка при генерации текста: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при генерации текста: {str(e)}"
            ) 