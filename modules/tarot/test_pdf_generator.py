"""
Тестирование генератора PDF для гадания на Таро
"""
import asyncio
import os
import sys
import logging
from datetime import datetime

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Импортируем модули
from pdf_generator import TarotPDFGenerator
from example_data import get_example_reading_data


async def test_pdf_generation():
    """
    Тестирование генерации PDF с результатами гадания
    """
    try:
        # Получаем тестовые данные
        reading_data = get_example_reading_data()
        
        # Создаем генератор PDF
        pdf_generator = TarotPDFGenerator()
        
        # Генерируем PDF
        logger.info("Начинаем генерацию PDF...")
        pdf_data = await pdf_generator.generate_reading_pdf(reading_data)
        
        if pdf_data:
            # Сохраняем PDF в файл
            output_file = f"test_tarot_reading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            with open(output_file, "wb") as f:
                f.write(pdf_data)
            
            logger.info(f"PDF успешно сгенерирован и сохранен в файл: {output_file}")
            logger.info(f"Размер файла: {len(pdf_data) / 1024:.2f} КБ")
            return True
        else:
            logger.error("Не удалось сгенерировать PDF")
            return False
    
    except Exception as e:
        logger.error(f"Ошибка при тестировании генерации PDF: {e}")
        return False


if __name__ == "__main__":
    # Запускаем тест
    result = asyncio.run(test_pdf_generation())
    
    if result:
        logger.info("Тест успешно выполнен")
        sys.exit(0)
    else:
        logger.error("Тест завершился с ошибкой")
        sys.exit(1) 