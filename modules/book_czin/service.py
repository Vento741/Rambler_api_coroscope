"""
Сервис для работы с Книгой Перемен (И-Цзин)
"""
import json
import os
import random
import logging
import base64
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from fastapi import HTTPException

from .models import ApiResponse, RandomHexagramResponse

logger = logging.getLogger(__name__)

class BookCzinService:
    """Сервис для работы с Книгой Перемен"""
    
    def __init__(self, base_url: str):
        """
        Инициализация сервиса
        
        :param base_url: Базовый URL для формирования полных URL к ресурсам
        """
        self.base_url = base_url
        self.hexagrams_dir = Path("modules/book_czin/hexagrams")
        self.images_dir = Path("modules/book_czin/image_hex")
        self.hexagrams_pdf_dir = Path("modules/book_czin/hexagrams_pdf")
        
        # Проверка существования директорий
        if not self.hexagrams_dir.exists():
            logger.error(f"Директория с гексаграммами (JSON) не найдена: {self.hexagrams_dir}")
            raise ValueError(f"Директория с гексаграммами (JSON) не найдена: {self.hexagrams_dir}")
            
        if not self.images_dir.exists():
            logger.error(f"Директория с изображениями не найдена: {self.images_dir}")
            raise ValueError(f"Директория с изображениями не найдена: {self.images_dir}")

        if not self.hexagrams_pdf_dir.exists():
            logger.error(f"Директория с PDF-файлами не найдена: {self.hexagrams_pdf_dir}")
            raise ValueError(f"Директория с PDF-файлами не найдена: {self.hexagrams_pdf_dir}")
        
        # Получаем список доступных гексаграмм
        self.available_hexagrams = self._get_available_hexagrams()
        
        if not self.available_hexagrams:
            logger.error("Не найдено ни одной гексаграммы (JSON, изображение и PDF должны совпадать)")
            raise ValueError("Не найдено ни одной гексаграммы (JSON, изображение и PDF должны совпадать)")
            
        logger.info(f"Сервис BookCzin инициализирован. Доступно {len(self.available_hexagrams)} гексаграмм.")
    
    def _get_available_hexagrams(self) -> list:
        """
        Получение списка доступных гексаграмм.
        Гексаграмма считается доступной, если для нее есть JSON, PNG и PDF файлы.
        
        :return: Список номеров доступных гексаграмм
        """
        hexagram_numbers = []
        json_files = {f.stem: f for f in self.hexagrams_dir.glob('*.json')}
        
        for number_str, json_file_path in json_files.items():
            try:
                hexagram_number = int(number_str)
                image_file = self.images_dir / f"{hexagram_number}.png"
                pdf_file = self.hexagrams_pdf_dir / f"{hexagram_number}.pdf"

                if image_file.exists() and pdf_file.exists():
                    hexagram_numbers.append(hexagram_number)
                else:
                    if not image_file.exists():
                        logger.warning(f"Для гексаграммы {hexagram_number} (JSON: {json_file_path.name}) не найдено изображение: {image_file.name}")
                    if not pdf_file.exists():
                        logger.warning(f"Для гексаграммы {hexagram_number} (JSON: {json_file_path.name}) не найден PDF: {pdf_file.name}")
                        
            except ValueError:
                logger.warning(f"Невозможно извлечь номер гексаграммы из JSON-файла: {json_file_path.name}")
                
        if not hexagram_numbers:
            logger.warning("В результате проверки не найдено ни одной полной гексаграммы (JSON, PNG, PDF).")
        return hexagram_numbers
    
    def _load_hexagram_data(self, hexagram_number: int) -> Dict[str, Any]:
        """
        Загрузка данных гексаграммы из JSON-файла
        
        :param hexagram_number: Номер гексаграммы
        :return: Данные гексаграммы
        """
        try:
            json_path = self.hexagrams_dir / f"{hexagram_number}.json"
            if not json_path.exists():
                raise FileNotFoundError(f"Файл с данными гексаграммы {hexagram_number} не найден: {json_path}")
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка при загрузке данных гексаграммы {hexagram_number}: {e}")
            raise HTTPException(status_code=500, detail=f"Ошибка при загрузке данных гексаграммы: {str(e)}")
    
    def _format_hexagram_text(self, hexagram_data: Dict[str, Any]) -> str:
        """
        Форматирование текста гексаграммы для отображения в Telegram
        
        :param hexagram_data: Данные гексаграммы
        :return: Отформатированный текст
        """
        sections = hexagram_data["sections"]
        result = [
            f"*{hexagram_data['number']}. {hexagram_data['title']}*",
            f"{hexagram_data['description']}",
            "",
            f"*НАЗВАНИЕ:* {sections.get('Название', '')}",
            "",
            f"*ОПРЕДЕЛЕНИЕ:* {sections.get('Определение', '')}",
            "",
            f"*СИМВОЛ:* {sections.get('Символ', '')}",
            "",
            f"*ОБРАЗНЫЙ РЯД:* {sections.get('Образный ряд', '')}"
        ]
        lines = []
        if sections.get('Вначале девятка'): lines.append(f"*9️⃣ В НАЧАЛЕ ДЕВЯТКА:* {sections['Вначале девятка']}")
        if sections.get('Девятка вторая'): lines.append(f"*9️⃣ ВТОРАЯ ДЕВЯТКА:* {sections['Девятка вторая']}")
        if sections.get('Девятка третья'): lines.append(f"*9️⃣ ТРЕТЬЯ ДЕВЯТКА:* {sections['Девятка третья']}")
        if sections.get('Девятка четвертая'): lines.append(f"*9️⃣ ЧЕТВЕРТАЯ ДЕВЯТКА:* {sections['Девятка четвертая']}")
        if sections.get('Девятка пятая'): lines.append(f"*9️⃣ ПЯТАЯ ДЕВЯТКА:* {sections['Девятка пятая']}")
        if sections.get('Наверху девятка'): lines.append(f"*9️⃣ НАВЕРХУ ДЕВЯТКА:* {sections['Наверху девятка']}")
        if sections.get('Все девятки'): lines.append(f"*9️⃣ ВСЕ ДЕВЯТКИ:* {sections['Все девятки']}")
        if lines:
            result.append("")
            result.append("*ЛИНИИ ГЕКСАГРАММЫ:*")
            result.extend(lines)
        return "\n".join(result)
    
    def get_random_hexagram(self) -> ApiResponse:
        """
        Получение случайной гексаграммы
        
        :return: Ответ API с данными случайной гексаграммы
        """
        try:
            if not self.available_hexagrams:
                return ApiResponse(success=False, error="Нет доступных гексаграмм (отсутствуют JSON, PNG или PDF файлы)")
                
            hexagram_number = random.choice(self.available_hexagrams)
            hexagram_data = self._load_hexagram_data(hexagram_number)
            
            # Обновленный URL для изображения с расширением .png
            image_url = f"{self.base_url}/api/v1/book-czin/image/{hexagram_number}.png" 
            # URL для PDF
            pdf_url = f"{self.base_url}/api/v1/book-czin/pdf/{hexagram_number}.pdf"

            hexagram_text = self._format_hexagram_text(hexagram_data)
            
            response_data = RandomHexagramResponse(
                number=hexagram_data["number"],
                title=hexagram_data["title"],
                description=hexagram_data["description"],
                image_url=image_url,
                pdf_url=pdf_url,
                sections=hexagram_data["sections"],
                formatted_text=hexagram_text
            )
            return ApiResponse(success=True, data=response_data)
        except Exception as e:
            logger.error(f"Ошибка при получении случайной гексаграммы: {e}", exc_info=True)
            return ApiResponse(success=False, error=f"Внутренняя ошибка сервера: {str(e)}")
    
    def get_hexagram_image_path(self, hexagram_number: int) -> Optional[Path]:
        """
        Получение пути к изображению гексаграммы
        
        :param hexagram_number: Номер гексаграммы
        :return: Путь к файлу изображения или None, если файл не найден
        """
        try:
            if hexagram_number not in self.available_hexagrams:
                logger.warning(f"Запрошена гексаграмма {hexagram_number} без соответствующего изображения, PDF или JSON.")
                return None
            image_path = self.images_dir / f"{hexagram_number}.png"
            if not image_path.exists():
                logger.warning(f"Файл изображения для гексаграммы {hexagram_number} не найден: {image_path}")
                return None
            return image_path
        except Exception as e:
            logger.error(f"Ошибка при получении пути к изображению гексаграммы {hexagram_number}: {e}")
            return None

    def get_hexagram_pdf_path(self, hexagram_number: int) -> Optional[Path]:
        """
        Получение пути к PDF-файлу гексаграммы.
        
        :param hexagram_number: Номер гексаграммы
        :return: Путь к файлу PDF или None, если файл не найден
        """
        try:
            if hexagram_number not in self.available_hexagrams:
                logger.warning(f"Запрошена гексаграмма {hexagram_number} без соответствующего PDF, изображения или JSON.")
                return None
            pdf_path = self.hexagrams_pdf_dir / f"{hexagram_number}.pdf"
            if not pdf_path.exists():
                logger.warning(f"PDF-файл для гексаграммы {hexagram_number} не найден: {pdf_path}")
                return None
            return pdf_path
        except Exception as e:
            logger.error(f"Ошибка при получении пути к PDF-файлу гексаграммы {hexagram_number}: {e}")
            return None 