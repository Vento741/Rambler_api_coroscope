#!/usr/bin/env python3
"""
Тестовый клиент для Moon Calendar API
"""
import asyncio
import aiohttp
import json
from datetime import date, datetime

class MoonCalendarClient:
    """Клиент для тестирования API"""
    
    def __init__(self, base_url: str = "http://81.177.6.93:8080"):
        self.base_url = base_url
    
    async def test_health(self):
        """Тест health check"""
        print("🏥 Testing health endpoint...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/health") as response:
                data = await response.json()
                print(f"Status: {response.status}")
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return response.status == 200
    
    async def test_current_calendar(self):
        """Тест получения текущего календаря"""
        print("🌙 Testing current calendar endpoint...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/v1/moon-calendar/current") as response:
                data = await response.json()
                print(f"Status: {response.status}")
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return response.status == 200
    
    async def test_specific_date(self, test_date: str = "2025-05-24"):
        """Тест получения календаря на конкретную дату"""
        print(f"📅 Testing calendar for date {test_date}...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/v1/moon-calendar/{test_date}") as response:
                data = await response.json()
                print(f"Status: {response.status}")
                print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return response.status == 200
    
    async def test_astro_bot_free(self):
        """Тест API astro_bot для бесплатных пользователей"""
        print("🔮 Testing astro_bot API for free users...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/v1/astro_bot/moon_day?user_type=free") as response:
                data = await response.json()
                print(f"Status: {response.status}")
                print(f"Success: {data.get('success', False)}")
                print(f"Cached: {data.get('cached', False)}")
                print(f"Model: {data.get('model', 'Not specified')}")
                print(f"Error: {data.get('error', 'No error')}")
                if data.get('data'):
                    print(f"Data length: {len(data.get('data', ''))}")
                    print(f"Data preview: {data.get('data', '')[:100]}...")
                return response.status == 200 and data.get('success', False)
    
    async def test_astro_bot_premium(self):
        """Тест API astro_bot для премиум пользователей"""
        print("💎 Testing astro_bot API for premium users...")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/v1/astro_bot/moon_day?user_type=premium") as response:
                data = await response.json()
                print(f"Status: {response.status}")
                print(f"Success: {data.get('success', False)}")
                print(f"Cached: {data.get('cached', False)}")
                print(f"Model: {data.get('model', 'Not specified')}")
                print(f"Error: {data.get('error', 'No error')}")
                if data.get('data'):
                    print(f"Data length: {len(data.get('data', ''))}")
                    print(f"Data preview: {data.get('data', '')[:100]}...")
                return response.status == 200 and data.get('success', False)
    
    async def test_cache_performance(self):
        """Тест кэширования"""
        print("⚡ Testing cache performance...")
        
        test_date = "2025-05-24"
        
        # Первый запрос (должен парсить)
        start_time = datetime.now()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/v1/moon-calendar/{test_date}") as response:
                data1 = await response.json()
        first_request_time = (datetime.now() - start_time).total_seconds()
        
        print(f"First request time: {first_request_time:.2f}s (cached: {data1.get('cached', False)})")
        
        # Второй запрос (должен брать из кэша)
        start_time = datetime.now()
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}/api/v1/moon-calendar/{test_date}") as response:
                data2 = await response.json()
        second_request_time = (datetime.now() - start_time).total_seconds()
        
        print(f"Second request time: {second_request_time:.2f}s (cached: {data2.get('cached', False)})")
        
        cache_working = data2.get('cached', False)
        
        if cache_working:
            print("✅ Cache is working!")
            print(f"⚡ Speed improvement: {(first_request_time / second_request_time):.1f}x faster")
        else:
            print("❌ Cache is not working")
            
        return cache_working
    
    async def test_concurrent_requests(self, count: int = 5):
        """Тест конкурентных запросов"""
        print(f"🚀 Testing {count} concurrent requests...")
        
        async def make_request(session, i):
            async with session.get(f"{self.base_url}/api/v1/moon-calendar/current") as response:
                data = await response.json()
                return i, response.status, data.get('cached', False)
        
        start_time = datetime.now()
        
        async with aiohttp.ClientSession() as session:
            tasks = [make_request(session, i) for i in range(count)]
            results = await asyncio.gather(*tasks)
        
        total_time = (datetime.now() - start_time).total_seconds()
        
        print(f"All {count} requests completed in {total_time:.2f}s")
        
        success_count = sum(1 for _, status, _ in results if status == 200)
        cached_count = sum(1 for _, _, cached in results if cached)
        
        print(f"✅ Successful: {success_count}/{count}")
        print(f"⚡ From cache: {cached_count}/{count}")
        print(f"🎯 Average time per request: {(total_time / count):.2f}s")
        
        # Тест считается успешным, если все запросы успешны
        return success_count == count
    
    async def run_all_tests(self):
        """Запуск всех тестов"""
        print("🧪 Starting Moon Calendar API Tests\n")
        
        tests = [
            ("Health Check", self.test_health()),
            ("Current Calendar", self.test_current_calendar()),
            ("Specific Date", self.test_specific_date()),
            ("Astro Bot API (Free)", self.test_astro_bot_free()),
            ("Astro Bot API (Premium)", self.test_astro_bot_premium()),
            ("Cache Performance", self.test_cache_performance()),
            ("Concurrent Requests", self.test_concurrent_requests()),
        ]
        
        results = []
        
        for test_name, test_coro in tests:
            print(f"\n{'='*50}")
            print(f"🔍 {test_name}")
            print('='*50)
            
            try:
                result = await test_coro
                results.append((test_name, "✅ PASSED" if result else "❌ FAILED"))
            except Exception as e:
                print(f"❌ ERROR: {e}")
                results.append((test_name, f"❌ ERROR: {str(e)}"))
        
        print(f"\n{'='*50}")
        print("📊 TEST RESULTS")
        print('='*50)
        
        for test_name, result in results:
            print(f"{result} - {test_name}")
        
        print("\n🎉 Testing completed!")

async def main():
    """Основная функция"""
    client = MoonCalendarClient()
    await client.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())