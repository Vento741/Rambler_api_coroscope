# Руководство по деплою FastAPI приложения на VPS Джино

## 1. Подготовка сервера

### Подключение к серверу

```bash
ssh username@your_jino_server_ip
```

### Обновление системы

```bash
sudo apt update
sudo apt upgrade -y
```

### Установка необходимых пакетов

```bash
sudo apt install -y python3 python3-pip python3-venv nginx supervisor git
```

## 2. Клонирование репозитория

```bash
mkdir -p /home/username/apps
cd /home/username/apps
git clone https://github.com/your-username/Rambler_api.git
cd Rambler_api
```

## 3. Настройка виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r req.txt
pip install gunicorn
```

## 4. Настройка Supervisor

Создайте конфигурационный файл для Supervisor:

```bash
sudo nano /etc/supervisor/conf.d/rambler_api.conf
```

Содержимое файла:

```ini
[program:rambler_api]
directory=/home/username/apps/Rambler_api
command=/home/username/apps/Rambler_api/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 127.0.0.1:8000
user=username
autostart=true
autorestart=true
stopasgroup=true
killasgroup=true
stderr_logfile=/var/log/rambler_api/err.log
stdout_logfile=/var/log/rambler_api/out.log
```

Создайте директорию для логов:

```bash
sudo mkdir -p /var/log/rambler_api
sudo chown -R username:username /var/log/rambler_api
```

Перезапустите Supervisor:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start rambler_api
```

## 5. Настройка Nginx

Создайте конфигурационный файл для Nginx:

```bash
sudo nano /etc/nginx/sites-available/rambler_api
```

Содержимое файла:

```nginx
server {
    listen 80;
    server_name your_domain.com www.your_domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /home/username/apps/Rambler_api/static;
    }
}
```

Активируйте конфигурацию и перезапустите Nginx:

```bash
sudo ln -s /etc/nginx/sites-available/rambler_api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 6. Настройка SSL с Let's Encrypt (опционально)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your_domain.com -d www.your_domain.com
```

## 7. Настройка файрвола (опционально)

```bash
sudo apt install -y ufw
sudo ufw allow 'Nginx Full'
sudo ufw allow 'OpenSSH'
sudo ufw enable
```

## 8. Автоматическое обновление из Git (опционально)

Создайте скрипт для обновления:

```bash
nano /home/username/apps/Rambler_api/update.sh
```

Содержимое скрипта:

```bash
#!/bin/bash
cd /home/username/apps/Rambler_api
git pull
source venv/bin/activate
pip install -r req.txt
sudo supervisorctl restart rambler_api
```

Сделайте скрипт исполняемым:

```bash
chmod +x /home/username/apps/Rambler_api/update.sh
```

## 9. Проверка работоспособности

Проверьте статус сервиса:

```bash
sudo supervisorctl status rambler_api
```

Проверьте доступность API:

```bash
curl http://your_domain.com/health
curl http://your_domain.com/api/v1/moon-calendar/current
```

## 10. Мониторинг и логи

Просмотр логов приложения:

```bash
tail -f /var/log/rambler_api/out.log
tail -f /var/log/rambler_api/err.log
```

Просмотр логов Nginx:

```bash
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

## Дополнительные рекомендации

1. **Настройка бэкапов**: Регулярно делайте резервные копии вашего приложения и базы данных.

2. **Мониторинг**: Настройте мониторинг сервера с помощью инструментов, таких как Prometheus + Grafana или Netdata.

3. **Автоматические обновления безопасности**: Настройте автоматические обновления безопасности для вашего сервера.

4. **Ротация логов**: Настройте logrotate для предотвращения заполнения диска логами.

```bash
sudo nano /etc/logrotate.d/rambler_api
```

Содержимое файла:

```
/var/log/rambler_api/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 username username
    sharedscripts
    postrotate
        supervisorctl restart rambler_api > /dev/null
    endscript
}
```

5. **Настройка резервного копирования**: Настройте автоматическое резервное копирование вашего приложения и данных.

## Решение проблем

### Приложение не запускается

Проверьте логи:

```bash
tail -f /var/log/rambler_api/err.log
```

### Проблемы с Nginx

Проверьте конфигурацию Nginx:

```bash
sudo nginx -t
```

### Проблемы с доступом к файлам

Убедитесь, что пользователь имеет правильные разрешения:

```bash
sudo chown -R username:username /home/username/apps/Rambler_api
``` 