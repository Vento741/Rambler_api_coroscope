"""
Сервис для работы с Таро
"""
import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from .pdf_generator import TarotPDFGenerator

logger = logging.getLogger(__name__)

class TarotService:
    """
    Сервис для работы с Таро, включая генерацию PDF с результатами гадания
    """
    
    def __init__(self):
        """
        Инициализация сервиса
        """
        self.pdf_generator = TarotPDFGenerator()
    
    async def generate_reading_pdf(self, reading_data: Dict[str, Any]) -> Optional[bytes]:
        """
        Генерирует PDF с результатами гадания
        
        Args:
            reading_data: Данные гадания
            
        Returns:
            Байты PDF-файла или None в случае ошибки
        """
        try:
            # Проверяем наличие необходимых полей
            required_fields = ['spread_name', 'question', 'cards', 'interpretation']
            for field in required_fields:
                if field not in reading_data:
                    logger.error(f"Отсутствует обязательное поле '{field}' в данных гадания")
                    return None
            
            # Проверяем наличие timestamp или добавляем текущее время
            if 'timestamp' not in reading_data:
                reading_data['timestamp'] = datetime.now().isoformat()
            
            # Проверяем формат карт
            for card in reading_data['cards']:
                if 'card_name' not in card or 'position_name' not in card or 'card_image_url' not in card:
                    logger.error(f"Некорректный формат данных карты: {card}")
                    return None
            
            # Генерируем PDF
            return await self.pdf_generator.generate_reading_pdf(reading_data)
        
        except Exception as e:
            logger.error(f"Ошибка при генерации PDF: {e}")
            return None 