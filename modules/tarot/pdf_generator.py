"""
Модуль для генерации PDF-файлов с результатами гадания на Таро
"""
import io
import logging
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

class TarotPDFGenerator:
    """
    Класс для генерации PDF-файлов с результатами гадания на Таро
    """
    
    def __init__(self):
        """
        Инициализация генератора PDF
        Регистрация шрифтов для поддержки кириллицы
        """
        # Попытка регистрации шрифта с поддержкой кириллицы
        try:
            pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
            pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))
            self.font_name = 'DejaVuSans'
        except:
            # Если не удалось зарегистрировать DejaVu, используем стандартный Helvetica
            logger.warning("Не удалось загрузить шрифт DejaVuSans, используем Helvetica")
            self.font_name = 'Helvetica'
    
    async def download_image(self, url: str) -> Optional[Image.Image]:
        """
        Асинхронная загрузка изображения по URL
        
        Args:
            url: URL изображения
            
        Returns:
            Объект изображения или None в случае ошибки
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        return Image.open(io.BytesIO(image_data))
                    else:
                        logger.error(f"Ошибка загрузки изображения: {response.status}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка при загрузке изображения: {e}")
            return None
    
    def _create_styles(self) -> Dict[str, ParagraphStyle]:
        """
        Создание стилей для PDF-документа
        
        Returns:
            Словарь стилей
        """
        styles = getSampleStyleSheet()
        
        # Создаем кастомные стили с поддержкой кириллицы
        styles.add(
            ParagraphStyle(
                name='Title',
                fontName=f'{self.font_name}-Bold',
                fontSize=18,
                alignment=1,  # По центру
                spaceAfter=12
            )
        )
        
        styles.add(
            ParagraphStyle(
                name='Heading',
                fontName=f'{self.font_name}-Bold',
                fontSize=14,
                alignment=0,  # По левому краю
                spaceAfter=10
            )
        )
        
        styles.add(
            ParagraphStyle(
                name='Normal',
                fontName=self.font_name,
                fontSize=11,
                alignment=0,  # По левому краю
                spaceAfter=8
            )
        )
        
        styles.add(
            ParagraphStyle(
                name='CardName',
                fontName=f'{self.font_name}-Bold',
                fontSize=12,
                alignment=1,  # По центру
                spaceAfter=6
            )
        )
        
        styles.add(
            ParagraphStyle(
                name='CardPosition',
                fontName=self.font_name,
                fontSize=10,
                alignment=1,  # По центру
                spaceAfter=4
            )
        )
        
        styles.add(
            ParagraphStyle(
                name='Footer',
                fontName=self.font_name,
                fontSize=8,
                alignment=1,  # По центру
                textColor=colors.gray
            )
        )
        
        return styles
    
    async def generate_reading_pdf(self, reading_data: Dict[str, Any]) -> bytes:
        """
        Генерация PDF-файла с результатами гадания
        
        Args:
            reading_data: Данные гадания
            
        Returns:
            Байты PDF-файла
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        styles = self._create_styles()
        elements = []
        
        # Добавляем заголовок
        elements.append(Paragraph(f"Гадание на Таро: {reading_data['spread_name']}", styles['Title']))
        elements.append(Spacer(1, 0.5*cm))
        
        # Добавляем дату
        date_str = datetime.fromisoformat(reading_data['timestamp']).strftime('%d.%m.%Y %H:%M')
        elements.append(Paragraph(f"Дата: {date_str}", styles['Normal']))
        elements.append(Spacer(1, 0.3*cm))
        
        # Добавляем вопрос
        elements.append(Paragraph(f"Вопрос: {reading_data['question']}", styles['Normal']))
        elements.append(Spacer(1, 1*cm))
        
        # Загружаем изображения карт асинхронно
        card_images = []
        tasks = []
        
        for card in reading_data['cards']:
            task = asyncio.create_task(self.download_image(card['card_image_url']))
            tasks.append((card, task))
        
        # Ждем загрузки всех изображений
        for card, task in tasks:
            image = await task
            if image:
                # Если карта перевернутая, поворачиваем изображение
                if card.get('is_reversed', False):
                    image = image.rotate(180)
                card_images.append((card, image))
        
        # Создаем таблицу с картами
        if card_images:
            # Определяем количество колонок в зависимости от количества карт
            if len(card_images) <= 3:
                cols = len(card_images)
            elif len(card_images) <= 6:
                cols = 3
            else:
                cols = 4
            
            # Вычисляем количество строк
            rows = (len(card_images) + cols - 1) // cols
            
            # Создаем данные для таблицы
            table_data = []
            card_index = 0
            
            for row in range(rows):
                row_data = []
                for col in range(cols):
                    if card_index < len(card_images):
                        card, image = card_images[card_index]
                        
                        # Изменяем размер изображения
                        max_width = 120  # в пикселях
                        width, height = image.size
                        ratio = max_width / width
                        new_size = (int(width * ratio), int(height * ratio))
                        resized_image = image.resize(new_size)
                        
                        # Сохраняем изображение в буфер
                        img_buffer = io.BytesIO()
                        resized_image.save(img_buffer, format='PNG')
                        img_buffer.seek(0)
                        
                        # Создаем элемент изображения для ReportLab
                        img = ReportLabImage(img_buffer, width=new_size[0], height=new_size[1])
                        
                        # Создаем ячейку с изображением и текстом
                        cell_elements = [
                            img,
                            Paragraph(card['position_name'], styles['CardPosition']),
                            Paragraph(f"{card['card_name']} {'(перевернутая)' if card.get('is_reversed', False) else ''}", styles['CardName'])
                        ]
                        
                        row_data.append(cell_elements)
                        card_index += 1
                    else:
                        row_data.append("")  # Пустая ячейка
                
                table_data.append(row_data)
            
            # Создаем таблицу
            col_widths = [4*cm] * cols
            table = Table(table_data, colWidths=col_widths)
            
            # Стиль таблицы
            table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.white),  # Убираем границы
                ('BACKGROUND', (0, 0), (-1, -1), colors.white),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 1*cm))
        
        # Добавляем интерпретацию
        elements.append(Paragraph("Интерпретация", styles['Heading']))
        elements.append(Spacer(1, 0.3*cm))
        
        # Разбиваем интерпретацию на абзацы для лучшей читаемости
        interpretation_paragraphs = reading_data['interpretation'].split('\n\n')
        for paragraph in interpretation_paragraphs:
            if paragraph.strip():
                elements.append(Paragraph(paragraph, styles['Normal']))
                elements.append(Spacer(1, 0.2*cm))
        
        # Добавляем информацию о картах
        elements.append(Spacer(1, 0.5*cm))
        elements.append(Paragraph("Информация о картах", styles['Heading']))
        elements.append(Spacer(1, 0.3*cm))
        
        for card in reading_data['cards']:
            card_title = f"{card['card_name']} {'(перевернутая)' if card.get('is_reversed', False) else ''}"
            elements.append(Paragraph(card_title, styles['CardName']))
            elements.append(Paragraph(f"Позиция: {card['position_name']}", styles['CardPosition']))
            if 'position_description' in card:
                elements.append(Paragraph(f"Значение позиции: {card['position_description']}", styles['Normal']))
            elements.append(Spacer(1, 0.5*cm))
        
        # Добавляем футер
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph("Гадание создано с помощью PuzzleBot.top", styles['Footer']))
        
        # Собираем документ
        doc.build(elements)
        
        # Возвращаем байты PDF
        buffer.seek(0)
        return buffer.getvalue()
