"""
Кастомные исключения для API
"""
from fastapi import HTTPException

class ParserException(Exception):
    """Базовое исключение для ошибок парсера"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class NetworkException(ParserException):
    """Исключение для сетевых ошибок"""
    pass

class ParseException(ParserException):
    """Исключение для ошибок парсинга"""
    pass

class CacheException(Exception):
    """Исключение для ошибок кэша"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

def parser_exception_handler(exc: ParserException):
    """Обработчик исключений парсера"""
    if isinstance(exc, NetworkException):
        return HTTPException(
            status_code=503,
            detail=f"Ошибка сети: {exc.message}"
        )
    elif isinstance(exc, ParseException):
        return HTTPException(
            status_code=500,
            detail=f"Ошибка парсинга: {exc.message}"
        )
    return HTTPException(
        status_code=500,
        detail=f"Ошибка: {exc.message}"
    ) 