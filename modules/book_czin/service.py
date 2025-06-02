"""
Сервис для работы с Книгой Перемен (И-Цзин)
"""
import json
import os
import random
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from fastapi import HTTPException

from .models import ApiResponse, RandomHexagramResponse

logger = logging.getLogger(__name__)

class BookCzinService:
    """Сервис для работы с Книгой Перемен"""
    
    def __init__(self, base_url: str):
        """
        Инициализация сервиса
        
        :param base_url: Базовый URL для формирования полных URL к изображениям
        """
        self.base_url = base_url
        self.hexagrams_dir = Path("modules/book_czin/hexagrams")
        self.images_dir = Path("modules/book_czin/image_hex")
        
        # Проверка существования директорий
        if not self.hexagrams_dir.exists():
            logger.error(f"Директория с гексаграммами не найдена: {self.hexagrams_dir}")
            raise ValueError(f"Директория с гексаграммами не найдена: {self.hexagrams_dir}")
            
        if not self.images_dir.exists():
            logger.error(f"Директория с изображениями не найдена: {self.images_dir}")
            raise ValueError(f"Директория с изображениями не найдена: {self.images_dir}")
        
        # Получаем список доступных гексаграмм
        self.available_hexagrams = self._get_available_hexagrams()
        
        if not self.available_hexagrams:
            logger.error("Не найдено ни одной гексаграммы")
            raise ValueError("Не найдено ни одной гексаграммы")
            
        logger.info(f"Сервис BookCzin инициализирован. Доступно {len(self.available_hexagrams)} гексаграмм")
    
    def _get_available_hexagrams(self) -> list:
        """
        Получение списка доступных гексаграмм
        
        :return: Список номеров доступных гексаграмм
        """
        hexagrams = []
        
        try:
            # Получаем список файлов JSON
            json_files = [f for f in os.listdir(self.hexagrams_dir) if f.endswith('.json')]
            
            for json_file in json_files:
                try:
                    # Извлекаем номер из имени файла
                    hexagram_number = int(json_file.split('.')[0])
                    
                    # Проверяем наличие соответствующего изображения
                    image_file = f"{hexagram_number}.png"
                    if os.path.exists(os.path.join(self.images_dir, image_file)):
                        hexagrams.append(hexagram_number)
                    else:
                        logger.warning(f"Для гексаграммы {hexagram_number} не найдено изображение {image_file}")
                        
                except ValueError:
                    logger.warning(f"Невозможно извлечь номер гексаграммы из файла {json_file}")
                    
        except Exception as e:
            logger.error(f"Ошибка при получении списка гексаграмм: {e}")
            
        return hexagrams
    
    def _load_hexagram_data(self, hexagram_number: int) -> Dict[str, Any]:
        """
        Загрузка данных гексаграммы из JSON-файла
        
        :param hexagram_number: Номер гексаграммы
        :return: Данные гексаграммы
        """
        try:
            json_path = os.path.join(self.hexagrams_dir, f"{hexagram_number}.json")
            
            if not os.path.exists(json_path):
                raise FileNotFoundError(f"Файл с данными гексаграммы {hexagram_number} не найден")
                
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных гексаграммы {hexagram_number}: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Ошибка при загрузке данных гексаграммы: {str(e)}"
            )
    
    def get_random_hexagram(self) -> ApiResponse:
        """
        Получение случайной гексаграммы
        
        :return: Ответ API с данными случайной гексаграммы
        """
        try:
            # Выбираем случайный номер гексаграммы из доступных
            if not self.available_hexagrams:
                return ApiResponse(
                    success=False,
                    error="Нет доступных гексаграмм"
                )
                
            hexagram_number = random.choice(self.available_hexagrams)
            
            # Загружаем данные гексаграммы
            hexagram_data = self._load_hexagram_data(hexagram_number)
            
            # Формируем URL изображения
            image_url = f"{self.base_url}/api/v1/book-czin/image/{hexagram_number}"
            
            # Создаем ответ
            response_data = RandomHexagramResponse(
                number=hexagram_data["number"],
                title=hexagram_data["title"],
                description=hexagram_data["description"],
                image_url=image_url,
                sections=hexagram_data["sections"]
            )
            
            return ApiResponse(
                success=True,
                data=response_data
            )
            
        except Exception as e:
            logger.error(f"Ошибка при получении случайной гексаграммы: {e}", exc_info=True)
            return ApiResponse(
                success=False,
                error=f"Внутренняя ошибка сервера: {str(e)}"
            )
    
    def get_hexagram_image_path(self, hexagram_number: int) -> Optional[str]:
        """
        Получение пути к изображению гексаграммы
        
        :param hexagram_number: Номер гексаграммы
        :return: Путь к файлу изображения или None, если файл не найден
        """
        try:
            # Проверяем, что номер гексаграммы в допустимом диапазоне
            if hexagram_number not in self.available_hexagrams:
                logger.warning(f"Запрошена гексаграмма с недопустимым номером: {hexagram_number}")
                return None
                
            # Формируем путь к файлу изображения
            image_path = os.path.join(self.images_dir, f"{hexagram_number}.png")
            
            # Проверяем существование файла
            if not os.path.exists(image_path):
                logger.warning(f"Файл изображения для гексаграммы {hexagram_number} не найден: {image_path}")
                return None
                
            return image_path
            
        except Exception as e:
            logger.error(f"Ошибка при получении пути к изображению гексаграммы {hexagram_number}: {e}")
            return None 