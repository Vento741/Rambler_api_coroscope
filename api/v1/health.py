"""
Эндпоинты проверки здоровья сервиса
"""
from datetime import datetime
from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/")
async def root():
    """Корневой эндпоинт"""
    return {
        "service": "Moon Calendar API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "current": "/api/v1/moon-calendar/current",
            "specific_date": "/api/v1/moon-calendar/{date}",
            "health": "/health"
        }
    } 