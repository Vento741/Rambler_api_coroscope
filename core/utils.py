"""
Вспомогательные функции
"""
import asyncio
from typing import Callable, Coroutine, TypeVar, Any
import datetime

T = TypeVar('T')

async def run_with_timeout(coro: Coroutine[Any, Any, T], timeout: float) -> T:
    """Запуск корутины с таймаутом"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Запрос занял больше {timeout} секунд")

def format_date_ru(date_str: str) -> str:
    """Форматирование даты в русском формате"""
    
    date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
    months_ru = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    
    return f"{date_obj.day} {months_ru[date_obj.month - 1]} {date_obj.year}"

def format_datetime_ru(dt_obj: datetime.datetime) -> str:
    """Форматирование datetime объекта в русском формате"""
    months_ru = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    return f"{dt_obj.day} {months_ru[dt_obj.month - 1]} {dt_obj.year} г., {dt_obj.strftime('%H:%M')}" 