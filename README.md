# InfoBubble Bot

Архитектура:
1. Django
2. GrabberBot
3. TelegramBot

Django - для обработки данных и её записей

GrabberBot - для парсинга новостей

TelegramBot - для работы с пользователем


GrabberBot находится по адресу

    bot\grabber_bot2.py - последняя версия
    bot\grabber_bot1.py - версия с обновлением данных по новым новостям (некорректно работает)
    
TelegramBot находится по адресу

    bot\bot.py - последняя версия    

Процесс установки идентичный основным проектам с запуском сразу бота и бекенда

# Environments

Create file `.env`

Provide in file this values:

```
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_USERNAME=
TELEGRAM_TOKEN=

DJANGO_SECRET_KEY=
DJANGO_HOST=

DB_NAME=
DB_USER=
DB_PASSWORD=
DB_PORT=
DB_HOST=        # For use local database, set `host.docker.internal`     
```

# Local Development

Start the dev server for local development:
```bash
docker-compose up
```

Run a command inside the docker container:

```bash
docker-compose run --rm web [command]
```

Create migrations for Django:

```bash
docker-compose run --rm web python manage.py makemigrations
```

Apply migrations for Django:

```bash
docker-compose run --rm web python manage.py migrate
```

Create superuser

```bash
docker-compose run --rm web python manage.py createsuperuser
```