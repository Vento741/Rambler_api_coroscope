# Модуль для генерации PDF с результатами гадания на Таро

Этот модуль предоставляет функциональность для создания PDF-документов с результатами гадания на картах Таро.

## Возможности

- Генерация PDF с результатами гадания на Таро
- Поддержка различных раскладов карт
- Отображение изображений карт
- Поддержка перевернутых карт
- Интерпретация расклада
- Поддержка кириллицы

## Установка зависимостей

```bash
pip install reportlab pillow aiohttp
```

## Структура модуля

- `pdf_generator.py` - Основной класс для генерации PDF
- `service.py` - Сервис для работы с PDF-генератором
- `models.py` - Модели данных для работы с Таро
- `routes.py` - API-маршруты для работы с PDF-генератором
- `utils.py` - Вспомогательные функции
- `example_data.py` - Пример данных для тестирования
- `test_pdf_generator.py` - Тест для проверки работы PDF-генератора

## Использование

### Генерация PDF через API

```python
import aiohttp
import json

async def generate_pdf():
    # Данные для гадания
    reading_data = {
        "spread_name": "Кельтский крест",
        "question": "Какие изменения ждут меня в ближайшем будущем?",
        "cards": [
            {
                "card_name": "Маг",
                "position_name": "Настоящее положение",
                "card_image_url": "https://www.trustedtarot.com/img/cards/the-magician.png",
                "is_reversed": False
            },
            # ... другие карты
        ],
        "interpretation": "Интерпретация расклада..."
    }
    
    # Отправляем запрос на API
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "http://localhost:8000/tarot/generate-pdf",
            json={"reading": reading_data}
        ) as response:
            if response.status == 200:
                result = await response.json()
                if result["success"]:
                    # Скачиваем PDF
                    async with session.get(
                        f"http://localhost:8000/tarot/download-pdf/{result['filename']}"
                    ) as pdf_response:
                        if pdf_response.status == 200:
                            # Сохраняем PDF
                            with open("tarot_reading.pdf", "wb") as f:
                                f.write(await pdf_response.read())
                            print("PDF успешно сохранен")
                        else:
                            print(f"Ошибка при скачивании PDF: {pdf_response.status}")
                else:
                    print(f"Ошибка при генерации PDF: {result['error']}")
            else:
                print(f"Ошибка запроса: {response.status}")
```

### Прямое использование генератора PDF

```python
import asyncio
from modules.tarot.pdf_generator import TarotPDFGenerator
from modules.tarot.example_data import get_example_reading_data

async def generate_pdf():
    # Получаем тестовые данные
    reading_data = get_example_reading_data()
    
    # Создаем генератор PDF
    pdf_generator = TarotPDFGenerator()
    
    # Генерируем PDF
    pdf_data = await pdf_generator.generate_reading_pdf(reading_data)
    
    if pdf_data:
        # Сохраняем PDF в файл
        with open("tarot_reading.pdf", "wb") as f:
            f.write(pdf_data)
        print("PDF успешно сгенерирован и сохранен")
    else:
        print("Не удалось сгенерировать PDF")

# Запускаем функцию
asyncio.run(generate_pdf())
```

## Формат данных

Для генерации PDF требуется следующий формат данных:

```json
{
    "spread_name": "Название расклада",
    "question": "Вопрос для гадания",
    "timestamp": "2023-11-01T12:00:00",  // Опционально, ISO формат
    "cards": [
        {
            "card_name": "Название карты",
            "position_name": "Название позиции",
            "position_description": "Описание позиции",  // Опционально
            "card_image_url": "URL изображения карты",
            "is_reversed": false  // Признак перевернутой карты
        },
        // ... другие карты
    ],
    "interpretation": "Интерпретация расклада"
}
```

## Тестирование

Для тестирования генератора PDF можно использовать скрипт `test_pdf_generator.py`:

```bash
cd modules/tarot
python test_pdf_generator.py
```

## Примечания

- Для корректного отображения кириллицы необходимо наличие шрифта DejaVuSans
- При отсутствии шрифта DejaVuSans будет использован стандартный шрифт Helvetica 