"""
Эндпоинты для Книги Перемен (И-Цзин)
"""
import os
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import FileResponse

from modules.book_czin import ApiResponse, BookCzinService
import config

router = APIRouter(prefix="/api/v1/book-czin")

@router.get("/random", response_model=ApiResponse)
async def get_random_hexagram(request: Request):
    """
    Получение случайной гексаграммы из Книги Перемен
    
    Эндпоинт возвращает случайно выбранную гексаграмму с её описанием и URL изображения.
    Используется для интеграции с Telegram-ботами через платформу puzzlebot.top.
    """
    # Получаем сервис из state приложения
    service = request.app.state.book_czin_service
    
    # Получаем случайную гексаграмму (без await, т.к. метод не асинхронный)
    return service.get_random_hexagram()

@router.get("/image/{hexagram_number}")
async def get_hexagram_image(hexagram_number: int, request: Request):
    """
    Получение изображения гексаграммы по её номеру
    
    :param hexagram_number: Номер гексаграммы (1-64)
    :return: Файл изображения
    """
    # Получаем сервис из state приложения
    service = request.app.state.book_czin_service
    
    # Получаем путь к файлу изображения
    image_path = service.get_hexagram_image_path(hexagram_number)
    
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(
            status_code=404,
            detail=f"Изображение для гексаграммы {hexagram_number} не найдено"
        )
    
    # Возвращаем файл изображения
    return FileResponse(image_path, media_type="image/png") 