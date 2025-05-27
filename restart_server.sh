#!/bin/bash
# Скрипт для перезагрузки сервера и обновления кода

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}===============================================${NC}"
echo -e "${BLUE}      ПЕРЕЗАГРУЗКА СЕРВЕРА И ОБНОВЛЕНИЕ КОДА      ${NC}"
echo -e "${BLUE}===============================================${NC}"

# Остановка текущего процесса
echo -e "\n${YELLOW}[1/5] Остановка текущих процессов...${NC}"
pkill -f "python run.py" || echo -e "${RED}Не найдены процессы для остановки${NC}"
pkill -f "uvicorn main:app" || echo -e "${RED}Не найдены процессы uvicorn для остановки${NC}"
echo -e "${GREEN}Процессы остановлены${NC}"

# Очистка кэшей и временных файлов
echo -e "\n${YELLOW}[2/5] Очистка кэшей и временных файлов...${NC}"
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name "*.pyc" -delete
echo -e "${GREEN}Кэши очищены${NC}"

# Проверка наличия изменений в git
echo -e "\n${YELLOW}[3/5] Проверка изменений в git...${NC}"
git_status=$(git status --porcelain)
if [ -n "$git_status" ]; then
    echo -e "${RED}Найдены локальные изменения:${NC}"
    git status --short
    echo -e "\n${YELLOW}Сбрасываем локальные изменения...${NC}"
    git reset --hard HEAD
    echo -e "${GREEN}Локальные изменения сброшены${NC}"
else
    echo -e "${GREEN}Локальных изменений не обнаружено${NC}"
fi

# Обновление кода из репозитория
echo -e "\n${YELLOW}[4/5] Обновление кода из репозитория...${NC}"
git pull
if [ $? -ne 0 ]; then
    echo -e "${RED}Ошибка при обновлении кода${NC}"
    exit 1
fi
echo -e "${GREEN}Код успешно обновлен${NC}"

# Запуск приложения в фоне
echo -e "\n${YELLOW}[5/5] Запуск сервера...${NC}"
nohup python run.py --port 8081 > server.log 2>&1 &
echo $! > server.pid
echo -e "${GREEN}Сервер запущен с PID $(cat server.pid)${NC}"

# Проверка работоспособности API
echo -e "\n${YELLOW}Проверка работоспособности API...${NC}"
sleep 5 # Даем серверу время на запуск
curl -s http://127.0.0.1:8081/health > /dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}API работает!${NC}"
    
    # Проверка API ключей
    echo -e "\n${YELLOW}Проверка API ключей...${NC}"
    python check_api_keys.py
else
    echo -e "${RED}API не отвечает!${NC}"
    echo -e "${YELLOW}Проверьте логи в server.log${NC}"
fi

echo -e "\n${BLUE}===============================================${NC}"
echo -e "${BLUE}      ПЕРЕЗАГРУЗКА ЗАВЕРШЕНА      ${NC}"
echo -e "${BLUE}===============================================${NC}"

echo -e "${YELLOW}Для просмотра логов в реальном времени:${NC}"
echo -e "  tail -f server.log"
echo -e "${YELLOW}Для остановки сервера:${NC}"
echo -e "  kill \$(cat server.pid)" 