"""
Устаревший файл для обратной совместимости
Все компоненты перенесены в соответствующие модули
"""

# Импортируем приложение из main.py для обратной совместимости
from main import app

# Для обратной совместимости с импортами
from .models import MoonDayResponse, CalendarDayResponse, ApiResponse
from .parser import MoonCalendarParser
from .service import MoonCalendarService

__all__ = [
    'app',
    'MoonDayResponse',
    'CalendarDayResponse',
    'ApiResponse',
    'MoonCalendarParser',
    'MoonCalendarService'
] 