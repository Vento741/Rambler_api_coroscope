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
    
    Эндпоинт возвращает случайно выбранную гексаграмму с её описанием, 
    URL изображения и URL PDF-файла.
    Используется для интеграции с Telegram-ботами через платформу puzzlebot.top.
    """
    # Получаем сервис из state приложения
    service = request.app.state.book_czin_service
    
    # Получаем случайную гексаграмму (без await, т.к. метод не асинхронный)
    return service.get_random_hexagram()

@router.get("/image/{hexagram_number}.png")
async def get_hexagram_image(hexagram_number: int, request: Request):
    """
    Получение изображения гексаграммы по её номеру.
    URL должен заканчиваться на .png
    
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
    
    # Возвращаем файл изображения с дополнительными заголовками для кэширования и CORS
    response = FileResponse(
        image_path, 
        media_type="image/png",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=86400",
            "X-Hexagram-Number": str(hexagram_number)
        }
    )
    
    return response 

@router.get("/pdf/{hexagram_number}.pdf")
async def get_hexagram_pdf(hexagram_number: int, request: Request):
    """
    Получение PDF-файла гексаграммы по её номеру.
    URL должен заканчиваться на .pdf

    :param hexagram_number: Номер гексаграммы (1-64)
    :return: Файл PDF
    """
    service = request.app.state.book_czin_service
    pdf_path = service.get_hexagram_pdf_path(hexagram_number)
    
    if not pdf_path or not pdf_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"PDF-файл для гексаграммы {hexagram_number} не найден"
        )
    
    return FileResponse(
        pdf_path, 
        media_type="application/pdf",
        filename=f"hexagram_{hexagram_number}.pdf",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "public, max-age=86400",
            "X-Hexagram-Number": str(hexagram_number)
        }
    ) 