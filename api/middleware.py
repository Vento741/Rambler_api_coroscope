"""
Middleware для API
"""
import time
from fastapi import Request
import logging

logger = logging.getLogger(__name__)

async def log_request_middleware(request: Request, call_next):
    """Middleware для логирования запросов"""
    start_time = time.time()
    
    # Получаем IP клиента
    client_host = request.client.host if request.client else "unknown"
    
    # Логируем начало запроса
    logger.info(f"Старт запроса: {request.method} {request.url.path} от {client_host}")
    
    # Обрабатываем запрос
    response = await call_next(request)
    
    # Вычисляем время выполнения
    process_time = time.time() - start_time
    
    # Логируем завершение запроса
    logger.info(
        f"Запрос завершен: {request.method} {request.url.path} "
        f"от {client_host} - Статус: {response.status_code} "
        f"- Время: {process_time:.4f}s"
    )
    
    # Добавляем заголовок с временем обработки
    response.headers["X-Process-Time"] = str(process_time)
    
    return response 