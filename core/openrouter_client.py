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
        model_configs: Optional[Dict[str, Dict[str, Any]]] = None,
        model_api_keys: Optional[Dict[str, str]] = None,
        timeout: int = 30
    ):
        """
        Инициализация клиента
        
        :param api_url: URL API OpenRouter
        :param api_keys: Список API ключей
        :param models: Список моделей
        :param model_configs: Конфигурации для моделей (опционально)
        :param model_api_keys: Соответствие моделей и их API ключей (опционально)
        :param timeout: Таймаут запроса в секундах
        """
        self.api_url = api_url
        self.api_keys = api_keys
        self.models = models
        self.timeout = timeout
        self.model_configs = model_configs or {}
        self.model_api_keys = model_api_keys or {}
        
        self.current_key_index = 0
        self.current_model_index = 0
        
        logger.info(f"OpenRouter клиент инициализирован с {len(api_keys)} ключами и {len(models)} моделями")
    
    def _get_current_key(self) -> str:
        """Получение текущего API ключа"""
        return self.api_keys[self.current_key_index]
    
    def _get_current_model(self) -> str:
        """Получение текущей модели"""
        return self.models[self.current_model_index]
    
    def _get_key_for_model(self, model: str) -> str:
        """Получение API ключа для конкретной модели"""
        # Если есть соответствие модели и ключа, используем его
        if model in self.model_api_keys and self.model_api_keys[model]:
            return self.model_api_keys[model]
        # Иначе используем текущий ключ
        return self._get_current_key()
    
    def _get_model_config(self, model: str) -> Dict[str, Any]:
        """Получение конфигурации для модели"""
        # Если есть конфигурация для модели, используем её
        if model in self.model_configs:
            return self.model_configs[model]
        # Иначе возвращаем конфигурацию по умолчанию
        return {"request_type": "standard", "timeout": self.timeout}
    
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
    
    def _prepare_headers(self, api_key: str) -> Dict[str, str]:
        """Подготовка заголовков запроса"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://puzzlebot.top",  # Добавлено для требований OpenRouter
            "X-Title": "PuzzleBot"  # Добавлено для требований OpenRouter
        }
    
    def _prepare_standard_payload(
        self, 
        model: str, 
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Подготовка стандартного payload для запроса"""
        return {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
    
    def _prepare_openai_payload(
        self, 
        model: str, 
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Подготовка payload для OpenAI-совместимых моделей"""
        return {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
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
        
        # Получаем конфигурацию модели
        model_config = self._get_model_config(model)
        request_type = model_config.get("request_type", "standard")
        model_timeout = model_config.get("timeout", self.timeout)
        
        # Получаем API ключ для модели
        api_key = self._get_key_for_model(model)
        
        # Подготавливаем payload в зависимости от типа запроса
        if request_type == "openai":
            payload = self._prepare_openai_payload(model, messages, max_tokens, temperature)
        else:
            payload = self._prepare_standard_payload(model, messages, max_tokens, temperature)
        
        # Логируем информацию о запросе
        logger.info(f"Запрос к OpenRouter API: модель={model}, max_tokens={max_tokens}, request_type={request_type}")
        
        for attempt in range(retry_count):
            try:
                # Увеличиваем таймаут до минимум 3 секунд
                actual_timeout = max(model_timeout, 3)
                
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=actual_timeout)) as session:
                    headers = self._prepare_headers(api_key)
                    logger.debug(f"Заголовки запроса: {headers}")
                    
                    # Логируем URL для диагностики
                    logger.debug(f"URL запроса: {self.api_url}")
                    
                    # Логируем payload для отладки
                    logger.debug(f"Payload запроса: {json.dumps(payload, ensure_ascii=False)}")
                    
                    async with session.post(
                        self.api_url,
                        headers=headers,
                        json=payload
                    ) as response:
                        if response.status == 200:
                            try:
                                result = await response.json()
                                # Проверка структуры ответа
                                if not result or 'choices' not in result:
                                    logger.info(f"Получен некорректный ответ от OpenRouter: {await response.text()}")
                                    # Ротация ключа при некорректном ответе
                                    self._rotate_key()
                                    if attempt == retry_count - 1:
                                        raise NetworkException("Некорректный ответ от OpenRouter API")
                                    continue
                                    
                                # Проверка наличия списка choices и его непустоты
                                if not result.get('choices'):
                                    logger.info("Получен ответ с пустым списком choices")
                                    # Ротация ключа при пустом списке choices
                                    self._rotate_key()
                                    if attempt == retry_count - 1:
                                        raise NetworkException("Получен ответ с пустым списком choices")
                                    continue
                                
                                # Проверка первого элемента списка choices
                                try:
                                    first_choice = result['choices'][0]
                                    if 'message' not in first_choice or 'content' not in first_choice.get('message', {}):
                                        logger.info("Некорректная структура первого элемента choices")
                                        # Ротация ключа при некорректной структуре
                                        self._rotate_key()
                                        if attempt == retry_count - 1:
                                            raise NetworkException("Некорректная структура ответа от OpenRouter API")
                                        continue
                                except IndexError:
                                    logger.info("Ошибка при доступе к первому элементу списка choices")
                                    # Ротация ключа при ошибке индекса
                                    self._rotate_key()
                                    if attempt == retry_count - 1:
                                        raise NetworkException("Ошибка индекса при обработке ответа от OpenRouter API")
                                    continue
                                
                                return result
                            except json.JSONDecodeError as e:
                                logger.error(f"Ошибка декодирования JSON: {e}")
                                logger.error(f"Ответ: {await response.text()}")
                                # Ротация ключа при ошибке декодирования
                                self._rotate_key()
                                if attempt == retry_count - 1:
                                    raise NetworkException(f"Ошибка декодирования JSON: {str(e)}")
                                continue
                        
                        # Обработка ошибок API
                        error_text = await response.text()
                        logger.error(f"OpenRouter API ошибка: {response.status}, {error_text}")
                        
                        if response.status == 401 or response.status == 403:
                            # Проблема с API ключом - ротация ключа
                            self._rotate_key()
                        elif response.status == 404:
                            # Проблема с моделью - ротация модели
                            self._rotate_model()
                        elif response.status == 429:
                            # Rate limit - ротация ключа и увеличенная пауза
                            self._rotate_key()
                            await asyncio.sleep(2)  # Увеличенная пауза при rate limit
                        else:
                            # Другие ошибки
                            logger.error(f"Неизвестная ошибка API: {response.status}")
                            self._rotate_key()  # Пробуем другой ключ для любой ошибки
                            
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
            # Подробное логирование структуры ответа для диагностики
            logger.debug(f"Получен ответ от OpenRouter: {json.dumps(response, ensure_ascii=False)}")
            
            # Проверяем наличие ключевых полей перед обращением к ним
            if not response:
                logger.error("Получен пустой ответ от OpenRouter API")
                return ""
                
            if 'choices' not in response:
                logger.error("В ответе отсутствует поле 'choices'")
                return ""
                
            if not response['choices']:
                logger.error("Список 'choices' в ответе пуст")
                return ""
            
            # Безопасное получение первого элемента списка choices
            try:
                first_choice = response['choices'][0]
            except IndexError:
                logger.error("Ошибка при доступе к первому элементу списка 'choices' (list index out of range)")
                return ""
            
            # Проверяем наличие message и content в первом выборе
            if 'message' not in first_choice:
                logger.error("В ответе отсутствует поле 'message'")
                return ""
                
            if 'content' not in first_choice['message']:
                logger.error("В ответе отсутствует поле 'content'")
                return ""
                
            content = first_choice['message']['content']
            logger.debug(f"Извлечен текст ответа длиной {len(content)} символов")
            return content
            
        except IndexError as e:
            logger.error(f"Ошибка индекса при извлечении текста ответа: {e}")
            logger.error(f"Структура ответа: {response}")
            return ""
        except (KeyError, AttributeError, TypeError) as e:
            logger.error(f"Ошибка при извлечении текста ответа: {e}")
            logger.error(f"Структура ответа: {response}")
            return ""
    
    async def generate_text(
        self,
        system_message: str,
        user_message: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        model: Optional[str] = None
    ) -> str:
        """
        Генерация текста с помощью OpenRouter API
        
        :param system_message: Системное сообщение
        :param user_message: Сообщение пользователя
        :param max_tokens: Максимальное количество токенов в ответе
        :param temperature: Температура генерации
        :param model: Конкретная модель для использования (опционально)
        :return: Сгенерированный текст
        """
        # Если модель не указана, используем текущую
        if not model:
            model = self._get_current_model()
            
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # Логируем запрос для диагностики
        logger.info(f"Отправка запроса к OpenRouter с моделью: {model}")
        logger.debug(f"Параметры запроса: max_tokens={max_tokens}, temperature={temperature}")
        
        # Счетчик попыток для всех моделей и ключей
        total_attempts = len(self.api_keys) * len(self.models) * 2
        
        for attempt in range(total_attempts):
            try:
                response = await self.make_request(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    model=model
                )
                
                text = self.extract_response_text(response)
                
                # Если текст пустой, пробуем другую модель/ключ
                if not text.strip():
                    logger.info("Получен пустой ответ от OpenRouter, пробуем другую модель/ключ")
                    if attempt % 2 == 0:
                        self._rotate_key()
                    else:
                        model = self._rotate_model()
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
                    model = self._rotate_model()
                
                # Пауза перед повторной попыткой
                await asyncio.sleep(1)
        
        # Этот код не должен выполниться, но на всякий случай
        raise HTTPException(
            status_code=500,
            detail="Не удалось сгенерировать текст: превышено максимальное количество попыток"
        ) 