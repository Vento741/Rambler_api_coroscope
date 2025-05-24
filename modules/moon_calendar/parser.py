"""
Парсер лунного календаря
"""
from datetime import datetime, date
from typing import Dict, Any, Optional
import asyncio
import logging
from enum import Enum

import aiohttp
from bs4 import BeautifulSoup
from fastapi import HTTPException

from core.utils import format_datetime_ru

# Настройка логирования
logger = logging.getLogger(__name__)

class Months(Enum):
    """Перечисление месяцев на русском"""
    Jan = "января"
    Feb = "февраля" 
    Mar = "марта"
    Apr = "апреля"
    May = "мая"
    Jun = "июня"
    Jul = "июля"
    Aug = "августа"
    Sep = "сентября"
    Oct = "октября"
    Nov = "ноября"
    Dec = "декабря"

class MoonCalendarParser:
    """Асинхронный парсер лунного календаря"""
    
    BASE_URL = "https://horoscopes.rambler.ru/moon/calendar/{date}/"
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
    
    def _normalize_text(self, element) -> str:
        """Нормализация текста элемента"""
        if not element:
            return ""
        return (element.text
                .replace('\xa0', ' ')
                .replace('  ', ' ')
                .strip())
    
    def _parse_datetime(self, date_str: str, year: int) -> datetime:
        """Преобразование строки в datetime"""
        try:
            day, month, time = date_str.split()
            month_name = Months(month).name
            
            dt = datetime.strptime(f"{year}{day}{month_name}{time}", "%Y%d%b%H:%M")
            # Устанавливаем московское время (UTC+3)
            return dt.replace(tzinfo=datetime.now().astimezone().tzinfo)
        except Exception as e:
            logger.error(f"Error parsing datetime {date_str}: {e}")
            return datetime.now()
    
    async def _fetch_page(self, calendar_date: date) -> BeautifulSoup:
        """Асинхронное получение страницы"""
        url = self.BASE_URL.format(date=calendar_date)
        
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status, 
                            detail=f"Failed to fetch calendar data: HTTP {response.status}"
                        )
                    
                    content = await response.read()
                    return BeautifulSoup(content, "html.parser")
                    
        except asyncio.TimeoutError:
            raise HTTPException(status_code=408, detail="Request timeout")
        except Exception as e:
            logger.error(f"Error fetching page: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to fetch calendar data: {str(e)}")
    
    def _parse_moon_days(self, soup: BeautifulSoup, year: int) -> list[Dict]:
        """Парсинг лунных дней"""
        moon_days = []
        
        try:
            moon_info = soup.find("div", {"class": "eG1Gp s63PD _3IJOS"})
            if not moon_info:
                return moon_days
            
            day_names = [self._normalize_text(day) for day in 
                        moon_info.findAll("span", {"class": "ZciAj"})]
            
            periods = [self._normalize_text(period) for period in 
                      moon_info.findAll("span", {"class": "_4FHaJ DSpR9 v5AKG"})]
            
            # Получаем описания дней
            moon_desc = soup.find("div", {"class": "dGWT9 cidDQ"})
            descriptions = []
            
            if moon_desc:
                element = moon_desc.next
                current_desc = []
                
                while element:
                    if hasattr(element, 'get') and element.get("class") == ['R2dbF', 'inVfT', '_8OzEU']:
                        break
                    elif hasattr(element, 'get') and element.get("class") == ['_1uCdn', 'iVDG2']:
                        if current_desc:
                            descriptions.append("\n".join(current_desc))
                            current_desc = []
                    elif hasattr(element, 'get') and element.get("class") == ['_5yHoW', 'AjIPq']:
                        text = self._normalize_text(element)
                        if text:
                            current_desc.append(text)
                    
                    element = element.next
                
                if current_desc:
                    descriptions.append("\n".join(current_desc))
            
            # Собираем лунные дни
            for i, (name, period) in enumerate(zip(day_names, periods)):
                if " — " in period:
                    start_str, end_str = period.split(" — ")
                    start_dt = self._parse_datetime(start_str, year)
                    end_dt = self._parse_datetime(end_str, year)
                    
                    # Корректировка для перехода через полночь
                    if start_dt > end_dt:
                        end_dt = end_dt.replace(year=end_dt.year + 1)
                    
                    moon_days.append({
                        "name": name,
                        "start": format_datetime_ru(start_dt),
                        "end": format_datetime_ru(end_dt),
                        "info": descriptions[i] if i < len(descriptions) else ""
                    })
            
        except Exception as e:
            logger.error(f"Error parsing moon days: {e}")
        
        return moon_days
    
    def _parse_recommendations(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Парсинг рекомендаций"""
        recommendations = {}
        
        try:
            # Находим все заголовки рекомендаций h3 с классом PzAWM AW4W0
            headers = soup.find_all("h3", {"class": "PzAWM AW4W0"})
            
            # Для каждого заголовка находим соответствующий текст
            for header in headers:
                title = self._normalize_text(header)
                
                # Находим следующий абзац с классом _5yHoW AjIPq
                content_elem = header.find_next("p", {"class": "_5yHoW AjIPq"})
                if content_elem:
                    content = self._normalize_text(content_elem)
                    if title and content:
                        recommendations[title] = content
                
        except Exception as e:
            logger.error(f"Error parsing recommendations: {e}")
        
        return recommendations
    
    def _parse_moon_phase(self, soup: BeautifulSoup) -> str:
        """Парсинг фазы луны"""
        try:
            # Ищем SVG элемент с классом Pf77m, содержащий информацию о фазе луны в атрибуте title
            phase_svg = soup.find("svg", {"class": "Pf77m"})
            if phase_svg and "title" in phase_svg.attrs:
                # Извлекаем текст из атрибута title и удаляем префикс "Фаза луны - "
                phase_text = phase_svg["title"]
                return phase_text.replace("Фаза луны - ", "").strip()
                
        except Exception as e:
            logger.error(f"Error parsing moon phase: {e}")
        
        return "Не определена"
    
    async def parse_calendar_day(self, calendar_date: date) -> Dict:
        """Основной метод парсинга дня календаря"""
        soup = await self._fetch_page(calendar_date)
        
        moon_phase = self._parse_moon_phase(soup)
        moon_days = self._parse_moon_days(soup, calendar_date.year)
        recommendations = self._parse_recommendations(soup)
        
        return {
            "date": calendar_date.isoformat(),
            "moon_phase": moon_phase,
            "moon_days": moon_days,
            "recommendations": recommendations
        }
