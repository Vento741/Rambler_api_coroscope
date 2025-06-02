"""
Утилиты для работы с Таро
"""
import os
import logging
import aiohttp
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


async def download_font(url: str, save_path: str) -> bool:
    """
    Загружает шрифт с поддержкой кириллицы по URL
    
    Args:
        url: URL шрифта
        save_path: Путь для сохранения файла
        
    Returns:
        True в случае успешной загрузки, False в случае ошибки
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(save_path, "wb") as f:
                        f.write(content)
                    logger.info(f"Шрифт успешно загружен и сохранен в {save_path}")
                    return True
                else:
                    logger.error(f"Ошибка загрузки шрифта: {response.status}")
                    return False
    except Exception as e:
        logger.error(f"Ошибка при загрузке шрифта: {e}")
        return False


def format_reading_data(reading_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Форматирует данные гадания для генерации PDF
    
    Args:
        reading_data: Исходные данные гадания
        
    Returns:
        Отформатированные данные гадания
    """
    # Проверяем наличие timestamp или добавляем текущее время
    if 'timestamp' not in reading_data:
        reading_data['timestamp'] = datetime.now().isoformat()
    
    # Проверяем и форматируем карты
    if 'cards' in reading_data:
        for card in reading_data['cards']:
            # Добавляем признак перевернутой карты, если его нет
            if 'is_reversed' not in card:
                card['is_reversed'] = False
            
            # Проверяем наличие обязательных полей
            if 'card_name' not in card:
                card['card_name'] = "Неизвестная карта"
            
            if 'position_name' not in card:
                card['position_name'] = "Неизвестная позиция"
    
    return reading_data


def save_reading_to_json(reading_data: Dict[str, Any], file_path: str) -> bool:
    """
    Сохраняет данные гадания в JSON-файл
    
    Args:
        reading_data: Данные гадания
        file_path: Путь для сохранения файла
        
    Returns:
        True в случае успешного сохранения, False в случае ошибки
    """
    try:
        # Создаем директорию, если она не существует
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Преобразуем datetime в строку
        data_copy = reading_data.copy()
        if 'timestamp' in data_copy and isinstance(data_copy['timestamp'], datetime):
            data_copy['timestamp'] = data_copy['timestamp'].isoformat()
        
        # Сохраняем в JSON
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_copy, f, ensure_ascii=False, indent=2)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при сохранении данных гадания: {e}")
        return False


def load_reading_from_json(file_path: str) -> Optional[Dict[str, Any]]:
    """
    Загружает данные гадания из JSON-файла
    
    Args:
        file_path: Путь к файлу
        
    Returns:
        Данные гадания или None в случае ошибки
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"Файл {file_path} не существует")
            return None
        
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data
    except Exception as e:
        logger.error(f"Ошибка при загрузке данных гадания: {e}")
        return None 