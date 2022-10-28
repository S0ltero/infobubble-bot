# InfoBubble Bot

**ENG:** This project implements a bot that allows users to filter their news feed based on their preferences using filters and a channel subscription system.This project represent functional of bThis project implements a bot that allows users to filter their news feed based on their preferences using filters and a channel subscription system.

---

**RUS:** Данный проект реализует бота который позволяет пользователям фильтровать их новостную ленту на основе их предпочтений с помощью фильтров и системы подписки на каналыДанный проект реализует бота который позволяет пользователям фильтровать их новостную ленту на основе их предпочтений с помощью фильтров и системы подписки на каналы

##### Bot Service:

- Initialize new users
- Process subscribe user to channels
- Process select users filters
- Process select user filter-words
- Handle forwarded from `grabber` service messages and save `file_id` of media unique for current bot to `backend` service
- Process sending news to users by them filters
- Process sending news to users by them subscribed channels

##### Grabber Service:

- Collect messages from telegram channels
- Forward collected messages to `shared channel` for handling by `bot` service

# Environments

Create file `.env`

Provide in file this values:

```
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_USERNAME=
TELEGRAM_TOKEN=
TELEGRAM_SHARED_CHANNEL_ID=    # Id channel used for forward collected messages by grabber service

GRABBER_API_ID=
GRABBER_API_HASH=

DJANGO_SECRET_KEY=
DJANGO_HOST=
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=

DB_NAME=
DB_USER=
DB_PASSWORD=
DB_PORT=
DB_HOST=        # For use local database, set `host.docker.internal`   
```

# Local Development

Start the bot service for authenticate in Telegram API

```
docker-compose run --rm grabber
```

Start the dev server for local development:

```bash
docker-compose up
```

> If you have problem with start this project, try to start service in this order
>
> 1. web
> 2. grabber
> 3. bot

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
