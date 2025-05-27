#!/usr/bin/env python3
"""
Скрипт для проверки работоспособности сервера
"""
import sys
import json
import argparse
import requests
from datetime import datetime

def check_endpoint(url, name):
    """Проверка доступности эндпоинта"""
    try:
        start_time = datetime.now()
        response = requests.get(url, timeout=5)
        duration = (datetime.now() - start_time).total_seconds()
        
        status_code = response.status_code
        
        if status_code == 200:
            print(f"✅ {name}: OK (статус {status_code}, время {duration:.2f}с)")
            try:
                return response.json()
            except:
                print(f"⚠️ Ответ не является JSON: {response.text[:100]}")
                return None
        else:
            print(f"❌ {name}: ОШИБКА (статус {status_code}, время {duration:.2f}с)")
            print(f"  Ответ: {response.text[:100]}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ {name}: НЕДОСТУПЕН ({str(e)})")
        return None

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description="Проверка работоспособности сервера")
    parser.add_argument("--host", default="81.177.6.93", help="Хост для проверки")
    parser.add_argument("--port", type=int, default=8080, help="Порт для проверки")
    parser.add_argument("--local", action="store_true", help="Проверять локальный сервер (127.0.0.1)")
    args = parser.parse_args()
    
    host = "127.0.0.1" if args.local else args.host
    port = args.port
    base_url = f"http://{host}:{port}"
    
    print(f"🔍 Проверка сервера на {base_url}\n")
    
    # Проверка health эндпоинта
    health_data = check_endpoint(f"{base_url}/health", "Health Check")
    
    if health_data:
        print(f"  Статус: {health_data.get('status', 'не указан')}")
        print(f"  Версия: {health_data.get('version', 'не указана')}")
    
    # Проверка текущего календаря
    calendar_data = check_endpoint(f"{base_url}/api/v1/moon-calendar/current", "Moon Calendar")
    
    # Проверка API astro_bot для free пользователей
    astro_free_data = check_endpoint(f"{base_url}/api/v1/astro_bot/moon_day?user_type=free", "Astro Bot (free)")
    
    if astro_free_data:
        success = astro_free_data.get('success', False)
        cached = astro_free_data.get('cached', False)
        model = astro_free_data.get('model', 'не указана')
        error = astro_free_data.get('error', None)
        
        print(f"  Успех: {'✅' if success else '❌'}")
        print(f"  Кэширование: {'✅' if cached else '❌'}")
        print(f"  Модель: {model}")
        
        if error:
            print(f"  Ошибка: {error}")
        elif 'data' in astro_free_data:
            data_length = len(astro_free_data.get('data', ''))
            print(f"  Длина данных: {data_length} символов")
            print(f"  Превью: {astro_free_data.get('data', '')[:100]}...")
    
    print("\n✨ Проверка завершена!")

if __name__ == "__main__":
    main() 