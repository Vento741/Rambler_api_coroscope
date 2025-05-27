#!/usr/bin/env python3
"""
Скрипт для проверки API ключей и соединения с OpenRouter
"""
import os
import json
import asyncio
import logging
import argparse
from typing import Dict, Any

import aiohttp
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_api_key(api_key: str, model: str) -> Dict[str, Any]:
    """Тестирование API ключа для конкретной модели"""
    logger.info(f"Тестирование ключа для модели {model}...")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://puzzlebot.top",
        "X-Title": "PuzzleBot API Key Test"
    }
    
    # Простой запрос для тестирования
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Ты - помощник для тестирования API."},
            {"role": "user", "content": "Ответь одним словом: Привет!"}
        ],
        "max_tokens": 10,
        "temperature": 0.5
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=10
            ) as response:
                status = response.status
                try:
                    result = await response.json()
                except:
                    result = {"error": await response.text()}
                
                logger.info(f"Статус: {status}")
                if status == 200:
                    if "choices" in result and result["choices"]:
                        content = result["choices"][0].get("message", {}).get("content", "")
                        logger.info(f"Ответ: {content}")
                        return {
                            "status": "success",
                            "model": model,
                            "content": content
                        }
                    else:
                        logger.error(f"Некорректный формат ответа: {json.dumps(result)}")
                        return {
                            "status": "error",
                            "error": "Некорректный формат ответа",
                            "response": result
                        }
                else:
                    logger.error(f"Ошибка запроса: {json.dumps(result)}")
                    return {
                        "status": "error",
                        "error": f"Статус {status}",
                        "response": result
                    }
    except Exception as e:
        logger.error(f"Ошибка при запросе: {e}")
        return {
            "status": "error",
            "error": str(e)
        }

async def check_env_file():
    """Проверка .env файла на наличие API ключей"""
    load_dotenv()
    
    # Проверяемые модели и их ключи
    models = {
        "google/gemini-2.0-flash-exp:free": "API_for_Gemini_2.0_Flash_Exp_free",
        "google/gemini-2.0-flash-001": "API_for_Gemini_2.0_Flash",
        "qwen/qwen2.5-vl-72b-instruct:free": "Qwen2.5_VL_72B_Instruct_free",
        "deepseek/deepseek-prover-v2:free": "DeepSeek_Prover_V2_free"
    }
    
    results = {}
    missing_keys = []
    
    # Проверка наличия ключей
    for model, env_var in models.items():
        api_key = os.getenv(env_var)
        if not api_key:
            logger.warning(f"🔴 Отсутствует ключ для {model} (переменная {env_var})")
            missing_keys.append(env_var)
            results[model] = {"status": "missing"}
        else:
            logger.info(f"🟢 Найден ключ для {model} (переменная {env_var})")
            # Тестирование ключа
            if args.test:
                result = await test_api_key(api_key, model)
                results[model] = result
            else:
                results[model] = {"status": "found"}
    
    return {
        "results": results,
        "missing_keys": missing_keys
    }

async def main():
    """Основная функция"""
    logger.info("Проверка API ключей OpenRouter...")
    
    results = await check_env_file()
    
    # Печать результатов
    print("\n" + "="*50)
    print("📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ API КЛЮЧЕЙ")
    print("="*50)
    
    for model, result in results["results"].items():
        status = result["status"]
        if status == "missing":
            print(f"🔴 {model}: Ключ отсутствует")
        elif status == "found":
            print(f"🟡 {model}: Ключ найден (без тестирования)")
        elif status == "success":
            print(f"🟢 {model}: Ключ работает, ответ: {result.get('content', '')}")
        else:
            print(f"🔴 {model}: Ошибка - {result.get('error', 'Неизвестная ошибка')}")
    
    # Проверка OpenRouter URL
    url = os.getenv("URL_LINK_OPENROUTER")
    if url:
        print(f"\n🔵 URL OpenRouter: {url}")
    else:
        print("\n🔴 URL OpenRouter не найден в .env файле")
    
    # Рекомендации
    if results["missing_keys"]:
        print("\n⚠️ РЕКОМЕНДАЦИИ:")
        print("Добавьте следующие ключи в .env файл:")
        for key in results["missing_keys"]:
            print(f"  {key}=sk-or-v1-...")
    
    print("\n🎉 Проверка завершена!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Проверка API ключей OpenRouter")
    parser.add_argument("--test", action="store_true", help="Тестировать ключи с реальными запросами")
    args = parser.parse_args()
    
    asyncio.run(main()) 