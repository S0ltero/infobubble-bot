import os
import asyncio
from pathlib import Path
from datetime import datetime

from aiogram import Bot
from aiogram import types
from aiogram.utils import exceptions

import aiohttp
from loguru import logger

API_TOKEN = os.getenv("TELEGRAM_TOKEN")
URL = os.getenv("DJANGO_HOST")

bot = Bot(token=API_TOKEN)

user_subscribe_news = {}
user_news = {}


async def send_new(user, message):
    user_id = user["id"]
    channel_id = message["channel"]

    # Добавляем inline кнопки
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("❤️", callback_data=f"like_{channel_id}"))
    markup.add(types.InlineKeyboardButton("👎", callback_data=f"nolike_{channel_id}"))
    markup.add(types.InlineKeyboardButton("Далее", callback_data="next"))

    if message["file"]:
        has_file = True
        filename = message["file"].split("/")[2]
        file_path = Path().cwd() / "media" / filename
    else:
        has_file = False

    try:
        if not has_file:
            await bot.send_message(
                user_id,
                message["text"],
                reply_markup=markup,
                parse_mode=types.ParseMode.HTML
            )
        elif message["file_type"] == "video":
            await bot.send_video(
                user_id,
                file_path.open("rb"),
                caption=message["text"],
                reply_markup=markup,
                parse_mode=types.ParseMode.HTML
            )
        elif message["file_type"] == "photo":
            await bot.send_photo(
                user_id,
                file_path.open("rb"),
                caption=message["text"],
                reply_markup=markup,
                parse_mode=types.ParseMode.HTML
            )
    except (
        FileNotFoundError,
        exceptions.BotBlocked,
        exceptions.UserDeactivated,
        exceptions.CantParseEntities
    ) as e:
        async with aiohttp.ClientSession() as session:
            if isinstance(e, (FileNotFoundError, exceptions.CantParseEntities)):
                async with session.delete(url=f"{URL}/api/messages/{message['id']}") as response:
                    pass
            if isinstance(e, exceptions.UserDeactivated):
                async with session.delete(url=f"{URL}/api/users/{user_id}") as response:
                    pass
        await get_news(user)
        return logger.error(e)

    # Сохраняем новость в базу данных
    history_data = {
        "user": user_id,
        "message": message["id"]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url=f"{URL}/api/history/", json=history_data) as response:
            if response.status != 201:
                return logger.error(await response.text())


async def get_news(user, is_subscribe=False):
    user_id = user["id"]

    if is_subscribe:
        url = f'{URL}/api/users/{user_id}/news-subscribe/'

        if not user_subscribe_news.get(user_id):
            async with aiohttp.ClientSession() as session:
                async with session.get(url=url) as response:
                    if response.status == 200:
                        user_subscribe_news[user_id] = await response.json()
                    else:
                        return logger.error(await response.text())

        try:
            message = user_subscribe_news[user_id].pop()
        except IndexError:
            return

    else:
        url = f'{URL}/api/users/{user_id}/news/'

        if not user_news.get(user_id):
            async with aiohttp.ClientSession() as session:
                async with session.get(url=url) as response:
                    if response.status == 200:
                        user_news[user_id] = await response.json()
                    else:
                        return logger.error(await response.text())

        try:
            message = user_news[user_id].pop()
        except IndexError:
            await bot.send_message(
                user_id, "На данный момент новостей нет, повторите попытку позже."
            )
            return

    await send_new(user, message)


async def day_news():
    while True:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url=f"{URL}/api/config/") as response:
                    dt_last_sent = (await response.json())["last_sent"]
                    dt_last_sent = datetime.strptime(dt_last_sent, "%Y-%m-%d")
            except aiohttp.ClientConnectionError:
                continue

            dt_now = datetime.now()

            if dt_now.day == dt_last_sent.day:
                logger.info("Await next day to send everyday news")
                await asyncio.sleep(86400)
                continue

            async with session.get(url=f"{URL}/api/users/") as response:
                if response.status == 200:
                    users = await response.json()
                elif response.status == 404:
                    logger.error("Пользователи не найдены")
                else:
                    logger.error(await response.text())

            for user in users:
                asyncio.ensure_future(get_news(user))

            data = {"last_sent": str(dt_now.date())}
            response = await session.patch(url=f"{URL}/api/config/", json=data)

            await asyncio.sleep(86400)


async def subscribe_news():
    while True:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url=f"{URL}/api/users/") as response:
                    if response.status == 200:
                        users = await response.json()
                    elif response.status == 404:
                        logger.error("Пользователи не найдены")
                    else:
                        logger.error(await response.text())
                        continue
            except aiohttp.ClientConnectionError:
                continue

        for user in users:
            asyncio.ensure_future(get_news(user, is_subscribe=True))

        await asyncio.sleep(5)
