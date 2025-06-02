"""
Маршруты API для работы с Таро
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
import os
import uuid
from typing import Optional

from .models import TarotPDFRequest, TarotPDFResponse
from .service import TarotService

logger = logging.getLogger(__name__)

# Создаем роутер
router = APIRouter(prefix="/tarot", tags=["tarot"])

# Директория для временных файлов
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)


def get_tarot_service() -> TarotService:
    """
    Зависимость для получения экземпляра TarotService
    """
    return TarotService()


def remove_file(file_path: str):
    """
    Функция для удаления временного файла
    """
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
    except Exception as e:
        logger.error(f"Ошибка при удалении файла {file_path}: {e}")


@router.post("/generate-pdf", response_model=TarotPDFResponse)
async def generate_pdf(
    request: TarotPDFRequest,
    background_tasks: BackgroundTasks,
    tarot_service: TarotService = Depends(get_tarot_service)
):
    """
    Генерирует PDF с результатами гадания на Таро
    """
    try:
        # Генерируем PDF
        pdf_data = await tarot_service.generate_reading_pdf(request.reading.dict())
        
        if not pdf_data:
            return TarotPDFResponse(
                success=False,
                error="Не удалось сгенерировать PDF"
            )
        
        # Создаем уникальное имя файла
        filename = f"tarot_reading_{uuid.uuid4()}.pdf"
        file_path = os.path.join(TEMP_DIR, filename)
        
        # Сохраняем PDF во временный файл
        with open(file_path, "wb") as f:
            f.write(pdf_data)
        
        # Добавляем задачу на удаление файла после отправки
        background_tasks.add_task(remove_file, file_path)
        
        return TarotPDFResponse(
            success=True,
            filename=filename
        )
    
    except Exception as e:
        logger.error(f"Ошибка при генерации PDF: {e}")
        return TarotPDFResponse(
            success=False,
            error=f"Внутренняя ошибка сервера: {str(e)}"
        )


@router.get("/download-pdf/{filename}")
async def download_pdf(
    filename: str,
    background_tasks: BackgroundTasks
):
    """
    Скачивание сгенерированного PDF-файла
    """
    file_path = os.path.join(TEMP_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    # Добавляем задачу на удаление файла после отправки
    background_tasks.add_task(remove_file, file_path)
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf",
        background=background_tasks
    ) 