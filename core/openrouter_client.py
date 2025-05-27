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
        retry_count: int = 1
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
        
        # Логируем информацию о запросе
        logger.info(f"Запрос к OpenRouter API: модель={model}, max_tokens={max_tokens}")
        logger.info(f"Используемый API ключ: {self._get_current_key()[:10]}...")
        
        # Проверяем статус API ключа
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                auth_url = "https://openrouter.ai/api/v1/auth/key"
                async with session.get(
                    auth_url,
                    headers={"Authorization": f"Bearer {self._get_current_key()}"}
                ) as response:
                    if response.status == 200:
                        key_info = await response.json()
                        logger.info(f"Статус API ключа: {key_info}")
                    else:
                        logger.error(f"Ошибка при проверке API ключа: {response.status}, {await response.text()}")
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса API ключа: {e}")
        
        for attempt in range(retry_count):
            try:
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                    headers = self._prepare_headers()
                    logger.debug(f"Заголовки запроса: {headers}")
                    
                    # Логируем URL и payload для диагностики
                    logger.debug(f"URL запроса: {self.api_url}")
                    logger.debug(f"Payload запроса: {json.dumps(payload)}")
                    
                    async with session.post(
                        self.api_url,
                        headers=headers,
                        json=payload
                    ) as response:
                        response_text = await response.text()
                        logger.info(f"Статус ответа: {response.status}")
                        logger.debug(f"Тело ответа: {response_text}")
                        
                        if response.status == 200:
                            try:
                                result = json.loads(response_text)
                                # Проверка структуры ответа
                                if not result or 'choices' not in result:
                                    logger.warning(f"Получен некорректный ответ от OpenRouter: {response_text}")
                                    # Ротация ключа при некорректном ответе
                                    self._rotate_key()
                                    if attempt == retry_count - 1:
                                        raise NetworkException("Некорректный ответ от OpenRouter API")
                                    continue
                                    
                                # Проверка наличия списка choices и его непустоты
                                if not result.get('choices'):
                                    logger.warning("Получен ответ с пустым списком choices")
                                    # Ротация ключа при пустом списке choices
                                    self._rotate_key()
                                    if attempt == retry_count - 1:
                                        raise NetworkException("Получен ответ с пустым списком choices")
                                    continue
                                
                                # Проверка первого элемента списка choices
                                try:
                                    first_choice = result['choices'][0]
                                    if 'message' not in first_choice or 'content' not in first_choice.get('message', {}):
                                        logger.warning("Некорректная структура первого элемента choices")
                                        # Ротация ключа при некорректной структуре
                                        self._rotate_key()
                                        if attempt == retry_count - 1:
                                            raise NetworkException("Некорректная структура ответа от OpenRouter API")
                                        continue
                                except IndexError:
                                    logger.warning("Ошибка при доступе к первому элементу списка choices")
                                    # Ротация ключа при ошибке индекса
                                    self._rotate_key()
                                    if attempt == retry_count - 1:
                                        raise NetworkException("Ошибка индекса при обработке ответа от OpenRouter API")
                                    continue
                                
                                return result
                            except json.JSONDecodeError as e:
                                logger.error(f"Ошибка декодирования JSON: {e}")
                                logger.error(f"Ответ: {response_text}")
                                # Ротация ключа при ошибке декодирования
                                self._rotate_key()
                                if attempt == retry_count - 1:
                                    raise NetworkException(f"Ошибка декодирования JSON: {str(e)}")
                                continue
                        
                        # Обработка ошибок API
                        logger.error(f"OpenRouter API ошибка: {response.status}, {response_text}")
                        
                        if response.status == 401 or response.status == 403:
                            # Проблема с API ключом - ротация ключа
                            logger.error(f"Ошибка авторизации с ключом: {self._get_current_key()[:10]}...")
                            self._rotate_key()
                        elif response.status == 404:
                            # Проблема с моделью - ротация модели
                            logger.error(f"Модель не найдена: {model}")
                            self._rotate_model()
                        elif response.status == 429:
                            # Rate limit - ротация ключа и увеличенная пауза
                            logger.error(f"Превышен лимит запросов с ключом: {self._get_current_key()[:10]}...")
                            self._rotate_key()
                            await asyncio.sleep(2)  # Увеличенная пауза при rate limit
                        elif response.status == 402:
                            # Payment Required - недостаточно средств
                            logger.error(f"Недостаточно средств на ключе: {self._get_current_key()[:10]}...")
                            self._rotate_key()
                        else:
                            # Другие ошибки
                            logger.error(f"Неизвестная ошибка API: {response.status}")
                            self._rotate_key()  # Пробуем другой ключ для любой ошибки
                            
                        # Если это последняя попытка, выбрасываем исключение
                        if attempt == retry_count - 1:
                            raise NetworkException(f"Ошибка OpenRouter API: {response.status}, {response_text}")
                            
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
        Извлечение текста из ответа API
        
        :param response: Ответ API
        :return: Извлеченный текст
        """
        try:
            # Проверяем наличие необходимых ключей
            if not response:
                logger.error("Пустой ответ от API")
                return ""
            
            if 'choices' not in response:
                logger.error(f"В ответе отсутствует ключ 'choices': {response}")
                return ""
            
            choices = response['choices']
            if not choices or not isinstance(choices, list):
                logger.error(f"Пустой или некорректный список 'choices': {choices}")
                return ""
            
            # Безопасное получение первого элемента
            try:
                first_choice = choices[0]
            except IndexError:
                logger.error(f"Индекс за пределами списка 'choices': {choices}")
                return ""
            
            # Проверяем наличие message в первом элементе
            if 'message' not in first_choice:
                logger.error(f"В первом элементе 'choices' отсутствует ключ 'message': {first_choice}")
                return ""
            
            message = first_choice['message']
            
            # Проверяем наличие content в message
            if 'content' not in message:
                logger.error(f"В 'message' отсутствует ключ 'content': {message}")
                return ""
            
            content = message['content']
            
            # Проверяем, что content - строка
            if not isinstance(content, str):
                logger.error(f"'content' не является строкой: {content}")
                return ""
            
            return content.strip()
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении текста из ответа: {e}")
            logger.error(f"Структура ответа: {response}")
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
        
        # Логируем запрос для диагностики
        logger.info(f"Отправка запроса к OpenRouter с моделью: {self._get_current_model()}")
        logger.debug(f"Параметры запроса: max_tokens={max_tokens}, temperature={temperature}")
        
        # Проверяем доступность модели
        try:
            # Базовый URL без /chat/completions
            base_url = self.api_url.rsplit('/', 2)[0]
            models_url = f"{base_url}/models"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    models_url,
                    headers={"Authorization": f"Bearer {self._get_current_key()}"}
                ) as response:
                    if response.status == 200:
                        models_data = await response.json()
                        available_models = [model.get('id') for model in models_data.get('data', [])]
                        
                        current_model = self._get_current_model()
                        if current_model not in available_models:
                            logger.error(f"Модель {current_model} недоступна в OpenRouter!")
                            logger.info(f"Доступные модели: {available_models}")
                            
                            # Если модель недоступна, пробуем найти альтернативу
                            if 'google/gemini' in current_model:
                                for model in available_models:
                                    if 'google/gemini' in model:
                                        logger.info(f"Найдена альтернативная модель: {model}")
                                        self.models = [model]
                                        break
                            elif 'anthropic/claude' in current_model:
                                for model in available_models:
                                    if 'anthropic/claude' in model:
                                        logger.info(f"Найдена альтернативная модель: {model}")
                                        self.models = [model]
                                        break
                            elif 'meta-llama' in current_model:
                                for model in available_models:
                                    if 'meta-llama' in model:
                                        logger.info(f"Найдена альтернативная модель: {model}")
                                        self.models = [model]
                                        break
                    else:
                        logger.error(f"Ошибка при получении списка моделей: {response.status}")
        except Exception as e:
            logger.error(f"Ошибка при проверке доступности модели: {e}")
        
        # Счетчик попыток для всех моделей и ключей
        total_attempts = 1  # Уменьшаем до 1 попытки
        
        for attempt in range(total_attempts):
            try:
                response = await self.make_request(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                
                text = self.extract_response_text(response)
                
                # Если текст пустой, пробуем другую модель/ключ
                if not text.strip():
                    logger.warning("Получен пустой ответ от OpenRouter, пробуем другую модель/ключ")
                    if attempt % 2 == 0:
                        self._rotate_key()
                    else:
                        self._rotate_model()
                    continue
                
                return text
                
            except Exception as e:
                logger.error(f"Ошибка при генерации текста (попытка {attempt+1}/{total_attempts}): {e}")
                
                # Если это последняя попытка, выбрасываем исключение
                if attempt == total_attempts - 1:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Не удалось сгенерировать текст после {total_attempts} попыток: {str(e)}"
                    )
                
                # Чередуем ротацию ключей и моделей
                if attempt % 2 == 0:
                    self._rotate_key()
                else:
                    self._rotate_model()
                
                # Пауза перед повторной попыткой
                await asyncio.sleep(1)
        
        # Этот код не должен выполниться, но на всякий случай
        raise HTTPException(
            status_code=500,
            detail="Не удалось сгенерировать текст: превышено максимальное количество попыток"
        ) 