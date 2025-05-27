#!/bin/bash
set -e  # Прерывать выполнение при ошибках

# Логирование
LOGFILE="/var/log/rambler_api/update.log"
echo "$(date): Начало обновления" >> $LOGFILE

# Переход в директорию проекта
cd /home/username/apps/Rambler_api_coroscope

# Активация виртуального окружения
source venv/bin/activate

# Обновление кода с подтверждением
read -p "Подтвердите обновление кода (y/n): " confirm
if [ "$confirm" = "y" ]; then
    git pull >> $LOGFILE 2>&1
else
    echo "Обновление отменено" >> $LOGFILE
    exit 1
fi

# Перезапуск сервиса
sudo supervisorctl restart rambler_api

echo "$(date): Обновление завершено успешно" >> $LOGFILE