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
        timeout: int = 60  # Увеличиваем таймаут по умолчанию до 60 секунд
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
        self.api_keys = api_keys  # Присваиваем напрямую
        self.models = models      # Присваиваем напрямую
        self.timeout = timeout
        self.model_configs = model_configs or {}
        self.model_api_keys = model_api_keys or {}
        
        self.current_key_index = 0
        self.current_model_index = 0
        
        if not self.api_keys:
            logger.critical("ALARM! OpenRouterClient получил ПУСТОЙ список api_keys. Клиент не сможет работать!")
            raise ValueError("Список api_keys не может быть пустым для OpenRouterClient.")
        else:
            logger.info(f"OpenRouterClient инициализирован. URL: {self.api_url}, Количество API ключей: {len(self.api_keys)}, Первый ключ (начало): {self.api_keys[0][:10]}...")
            
        if not self.models:
            logger.warning("OpenRouterClient получил ПУСТОЙ список models. Некоторые функции могут не работать корректно.")
            # Можно не возбуждать ошибку, если клиент может работать без списка моделей по умолчанию,
            # но это плохая практика для текущей реализации _get_current_model()
        else:
            logger.info(f"OpenRouterClient: Количество моделей по умолчанию: {len(self.models)}, Первая модель: {self.models[0]}")
    
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
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stop": None  # Явно указываем, что маркеры остановки не используются
        }
        
        # Специфичная обработка для моделей Gemini
        if "gemini" in model.lower():
            # Преобразуем системное сообщение в формат, понятный Gemini
            formatted_messages = []
            for msg in messages:
                if msg["role"] == "system":
                    # Переводим системное сообщение в пользовательское для Gemini
                    formatted_messages.append({"role": "user", "content": f"Инструкция: {msg['content']}"})
                else:
                    formatted_messages.append(msg)
            
            # Обновляем сообщения в payload
            payload["messages"] = formatted_messages
            
            # Добавляем дополнительные параметры для Gemini
            payload["response_format"] = {"type": "text"}
        
        return payload
    
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
        
        for attempt in range(retry_count):
            try:
                current_model_for_attempt = model # Используем model, которая может меняться между попытками (из-за ротации)
                api_key = self._get_key_for_model(current_model_for_attempt)

                # Проверка API ключа
                if not api_key or len(api_key) < 20:
                    logger.error(f"Некорректный API ключ для модели {current_model_for_attempt} (попытка {attempt+1}): {api_key}")
                    if attempt == retry_count - 1:
                        raise NetworkException(f"Некорректный API ключ для модели {current_model_for_attempt} после всех попыток.")
                    await asyncio.sleep(1) # Небольшая пауза перед сменой ключа/модели
                    self._rotate_key() # Пробуем другой ключ, если текущий невалиден
                    continue

                # Подготавливаем payload в зависимости от типа запроса
                if request_type == "openai": # request_type должен быть актуален для current_model_for_attempt
                    payload = self._prepare_openai_payload(current_model_for_attempt, messages, max_tokens, temperature)
                else:
                    payload = self._prepare_standard_payload(current_model_for_attempt, messages, max_tokens, temperature)
                
                logger.info(f"Попытка {attempt+1}/{retry_count}: Запрос к OpenRouter API: модель={current_model_for_attempt}, max_tokens={max_tokens}")

                # Используем увеличенный таймаут для всех моделей
                actual_timeout = max(model_timeout, 60)  # Минимум 60 секунд для всех запросов
                
                if attempt > 0: # Пауза перед повторными попытками
                    # Используем минимальную фиксированную задержку
                    backoff_time = 0.3  # Фиксированная задержка 0.5 секунды между попытками
                    logger.info(f"Пауза перед повторной попыткой: {backoff_time} сек.")
                    await asyncio.sleep(backoff_time)
                
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=actual_timeout)) as session:
                    headers = self._prepare_headers(api_key)
                    logger.debug(f"Заголовки запроса (попытка {attempt+1}): {headers}")
                    logger.debug(f"URL запроса (попытка {attempt+1}): {self.api_url}")
                    logger.debug(f"Payload запроса (попытка {attempt+1}): {json.dumps(payload, ensure_ascii=False)}")
                    
                    try:
                        async with session.post(
                            self.api_url,
                            headers=headers,
                            json=payload,
                            ssl=False
                        ) as response:
                            response_text = await response.text()
                            
                            if response.status == 200:
                                try:
                                    result = json.loads(response_text)
                                    if not result or 'choices' not in result or not result.get('choices') or \
                                       'message' not in result['choices'][0] or 'content' not in result['choices'][0].get('message', {}):
                                        logger.warning(f"Получен некорректный/пустой успешный ответ от OpenRouter (модель {current_model_for_attempt}, попытка {attempt+1}): {response_text}")
                                        # Не ротируем ключ сразу, дадим шанс другим моделям или следующей попытке с этим же ключом, если ошибка временная
                                        if attempt == retry_count - 1:
                                            raise NetworkException(f"Некорректный ответ от OpenRouter API для модели {current_model_for_attempt} после всех попыток: {response_text}")
                                        # Продолжаем цикл, возможно, следующая попытка сработает или будет ротация
                                        continue
                                    logger.info(f"Успешный ответ от модели {current_model_for_attempt} (попытка {attempt+1})")
                                    return result

                                except json.JSONDecodeError as e_json:
                                    logger.error(f"Ошибка декодирования JSON (модель {current_model_for_attempt}, попытка {attempt+1}): {e_json}. Ответ: {response_text}")
                                    if attempt == retry_count - 1:
                                        raise NetworkException(f"Ошибка декодирования JSON от OpenRouter для модели {current_model_for_attempt}: {response_text}")
                                    continue # Пробуем следующую попытку

                            # Обработка ошибок API (статус не 200)
                            logger.error(f"OpenRouter API ошибка (модель {current_model_for_attempt}, попытка {attempt+1}): Статус={response.status}, Ответ={response_text}")
                            
                            error_data = {}
                            try:
                                error_data = json.loads(response_text)
                            except json.JSONDecodeError:
                                logger.warning(f"Не удалось декодировать JSON из ответа об ошибке (модель {current_model_for_attempt}): {response_text}")
                                
                            extracted_error_message = error_data.get('error', {}).get('message', 'Сообщение об ошибке не найдено в JSON.')
                            detailed_error_for_exception = f"Статус={response.status}, Модель='{current_model_for_attempt}', Сообщение='{extracted_error_message}', ОтветOpenRouter='{response_text}'"

                            if response.status in [401, 403]: # Ошибка авторизации
                                logger.warning(f"Ошибка авторизации (401/403) для ключа {api_key[:10]}... (модель {current_model_for_attempt}). Ротация ключа.")
                                self._rotate_key() 
                            elif response.status == 404: # Модель не найдена
                                logger.warning(f"Модель не найдена (404): {current_model_for_attempt}. Ротация модели.")
                                model = self._rotate_model() # Обновляем основную 'model' для следующих попыток
                                request_type = self._get_model_config(model).get("request_type", "standard") # Обновляем тип запроса для новой модели
                            elif response.status == 429: # Превышен лимит запросов
                                logger.warning(f"Превышен лимит запросов (429) для ключа {api_key[:10]}... или модели {current_model_for_attempt}.")
                                if ":free" in current_model_for_attempt: # Если бесплатная модель, сразу меняем ее
                                    logger.info(f"Бесплатная модель {current_model_for_attempt} временно недоступна, ротация модели.")
                                    model = self._rotate_model()
                                    request_type = self._get_model_config(model).get("request_type", "standard")
                                else: # Для платных моделей сначала ротируем ключ
                                    self._rotate_key()
                                # Фиксированная задержка при 429 вместо экспоненциальной
                                current_backoff_429 = 0.3  # Минимальная задержка 0.5 секунды при 429
                                logger.info(f"Дополнительная задержка из-за Rate limit (429): {current_backoff_429} сек.")
                                await asyncio.sleep(current_backoff_429)
                            else: # Другие ошибки сервера
                                logger.warning(f"Неизвестная ошибка API ({response.status}) для модели {current_model_for_attempt}. Ротация ключа.")
                                self._rotate_key()
                                
                            if attempt == retry_count - 1:
                                raise NetworkException(f"Ошибка OpenRouter API после всех попыток: {detailed_error_for_exception}")
                            # Пауза для остальных ошибок перед следующей попыткой будет в начале цикла

                    except aiohttp.ClientConnectionError as e_conn:
                        logger.error(f"Ошибка соединения с API (модель {current_model_for_attempt}, попытка {attempt+1}/{retry_count}): {e_conn}")
                        if attempt == retry_count - 1:
                            raise NetworkException(f"Ошибка соединения с OpenRouter для модели {current_model_for_attempt}: {str(e_conn)}")
                        self._rotate_key() # Пробуем другой ключ
                        # Пауза будет в начале следующей итерации
                    
                    except asyncio.TimeoutError as e_timeout: # Отдельно ловим TimeoutError, т.к. он не всегда ClientError
                        logger.error(f"Таймаут запроса (модель {current_model_for_attempt}, попытка {attempt+1}/{retry_count}): {e_timeout}")
                        if attempt == retry_count - 1:
                            raise NetworkException(f"Таймаут при запросе к OpenRouter для модели {current_model_for_attempt}: {str(e_timeout)}")
                        self._rotate_key() # Пробуем другой ключ
                        # Пауза будет в начале следующей итерации

            except (aiohttp.ClientError) as e_client_other: # Ловим остальные ClientError, которые не ConnectionError
                logger.error(f"Общая ошибка клиента aiohttp (модель {model}, попытка {attempt+1}/{retry_count}): {e_client_other}") # здесь model - это исходная модель на начало цикла
                if attempt == retry_count - 1:
                    raise NetworkException(f"Общая ошибка клиента aiohttp при запросе к OpenRouter для модели {model}: {str(e_client_other)}")
                self._rotate_key()
                # Пауза будет в начале следующей итерации
            
            except NetworkException: # Перехватываем NetworkException, чтобы не попасть в общий Exception ниже
                raise # И пробрасываем дальше, если это последняя попытка или нужно выйти
            except Exception as e_general: # Ловим вообще все остальные неожиданные ошибки
                logger.error(f"Неожиданная ошибка в make_request (модель {model}, попытка {attempt+1}/{retry_count}): {e_general}", exc_info=True)
                if attempt == retry_count - 1:
                    raise NetworkException(f"Неожиданная ошибка при запросе к OpenRouter для модели {model}: {str(e_general)}")
                # При общих ошибках, возможно, стоит просто перейти к следующей попытке без ротации или с ротацией ключа
                self._rotate_key() # Как минимум, попробуем другой ключ
                # Пауза будет в начале следующей итерации

        # Этот код не должен быть достигнут, если retry_count > 0,
        # так как последняя попытка либо вернет результат, либо выбросит исключение.
        # Но на всякий случай:
        final_model_tried = model # или current_model_for_attempt, если определена в этой области видимости
        raise NetworkException(f"Не удалось выполнить запрос к модели {final_model_tried} после {retry_count} попыток по неизвестной причине (код достиг конца функции make_request).")

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
        model: Optional[str] = None # Изначально переданная модель (или None)
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
        
        initial_model_param = model # Сохраняем исходный параметр model
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # Если модель не указана явно, начинаем с текущей в ротации клиента
        current_model_to_try = initial_model_param if initial_model_param else self._get_current_model()
        
        # Количество общих попыток, учитывая ротацию моделей и ключей внутри make_request
        # Здесь retry_count для make_request будет управлять внутренними попытками для ОДНОЙ модели
        # А этот цикл будет управлять перебором моделей, если make_request для текущей модели фейлится окончательно
        
        num_models_available = len(self.models)
        num_keys_available = len(self.api_keys)
        
        # Попробуем каждую доступную модель хотя бы раз
        for model_attempt_num in range(num_models_available): 
            logger.info(f"Попытка генерации текста с моделью: {current_model_to_try} (общая попытка {model_attempt_num+1}/{num_models_available})")
            logger.info(f"Параметры запроса: max_tokens={max_tokens}, temperature={temperature}")

            try:
                # make_request теперь сам управляет ротацией ключей и несколькими попытками для ОДНОЙ модели
                # Передаем current_model_to_try в make_request.
                # retry_count для make_request можно оставить по умолчанию (e.g., 3) или сделать настраиваемым.
                response_data = await self.make_request(
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    model=current_model_to_try, # Передаем текущую модель для попытки
                    retry_count=max(1, num_keys_available) # Даем шанс каждому ключу для текущей модели
                )
                
                text = self.extract_response_text(response_data)
                
                if text and text.strip():
                    logger.info(f"Успешно сгенерирован текст моделью {current_model_to_try}")
                    return text
                else:
                    logger.warning(f"Модель {current_model_to_try} вернула пустой ответ. Пробуем следующую модель.")
            
            except NetworkException as e:
                # NetworkException из make_request означает, что все попытки для current_model_to_try провалились
                logger.error(f"NetworkException при попытке генерации моделью {current_model_to_try}: {e}. Пробуем следующую модель.")
            except Exception as e_gen: # Другие неожиданные ошибки на этом уровне
                logger.error(f"Неожиданная ошибка на уровне generate_text с моделью {current_model_to_try}: {e_gen}", exc_info=True)

            # Если дошли сюда, значит, текущая модель не сработала или вернула пустой ответ
            # Ротируем модель для следующей попытки цикла generate_text
            # Важно: если initial_model_param был задан, мы не должны бесконечно ротировать, а только попробовать 1 раз.
            if initial_model_param and model_attempt_num == 0: # Если модель была задана явно, и это была первая (и единственная) попытка для нее
                logger.warning(f"Явно указанная модель {initial_model_param} не смогла сгенерировать текст.")
                break # Выходим из цикла, если модель была указана и не сработала
            
            current_model_to_try = self._rotate_model() # Получаем следующую модель из списка клиента
            if initial_model_param is None and current_model_to_try == self.models[0] and model_attempt_num > 0:
                # Если переданная модель была None, и мы сделали полный круг по моделям
                logger.warning("Сделан полный круг по всем доступным моделям, ни одна не сработала.")
                break 
        
        # Если все модели перебраны и текст не получен
        detail_message = f"Не удалось сгенерировать текст после попыток со всеми доступными моделями."
        if initial_model_param:
            detail_message = f"Не удалось сгенерировать текст с использованием указанной модели: {initial_model_param}."
        
        logger.error(detail_message)
        raise HTTPException(
            status_code=500,
            detail=detail_message
        ) 