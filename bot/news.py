import os
import asyncio
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


async def create_media_list(media_items: list):
    """Convert list of dicts from DB to aiogram input media types list"""
    media_list = []

    for item in media_items:
        file_id = item["file_id"]
        file_type = item["file_type"]

        if file_type == "PHOTO":
            media_list.append(types.InputMediaPhoto(media=file_id))
        elif file_type in ["VIDEO", "VIDEO_NOTE"]:
            media_list.append(types.InputMediaVideo(media=file_id))
        elif file_type == "ANIMATION":
            media_list.append(types.InputMediaAnimation(media=file_id))
        elif file_type == "DOCUMENT":
            media_list.append(types.InputMediaDocument(media=file_id))
        elif file_type == "VOICE":
            media_list.append(types.InputMediaAudio(media=file_id))

    return media_list


async def send_new(user, message):
    user_id = user["id"]
    channel_id = message["channel"]

    # Добавляем inline кнопки
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        types.InlineKeyboardButton("❤️", callback_data=f"like_{channel_id}"),
        types.InlineKeyboardButton("👎", callback_data=f"nolike_{channel_id}")
    )
    markup.row(types.InlineKeyboardButton("Далее", callback_data="next"))

    try:
        data = {
            "chat_id": user_id,
            "reply_markup": markup,
            "parse_mode": types.ParseMode.HTML
        }
        if message.get("media"):
            if len(message["media"]) > 1:
                media_list = await create_media_list(message["media"])
                media_list[0].caption = message["text"]
                media_list[0].parse_mode = types.ParseMode.HTML
                media_list[0].reply_markup = markup

                media_message = await bot.send_media_group(
                    chat_id=user_id,
                    media=media_list,
                )
                await bot.send_message(
                    **data,
                    text="Оцените новость",
                    reply_to_message_id=media_message[0].message_id,
                )
            else:
                data["caption"] = message["text"]
                media = message["media"][0]
                if media["file_type"] == "PHOTO":
                    data["photo"] = media["file_id"]
                    await bot.send_photo(**data)
                elif media["file_type"] in ["VIDEO", "VIDEO_NOTE"]:
                    data["video"] = media["file_id"]
                    await bot.send_video(**data)
                elif media["file_type"] == "ANIMATION":
                    data["animation"] = media["file_id"]
                    await bot.send_animation(**data)
                elif media["file_type"] == "DOCUMENT":
                    data["document"] = media["file_id"]
                    await bot.send_document(**data)
                elif media["file_type"] == "AUDIO":
                    data["audio"] = media["file_id"]
                    await bot.send_audio(**data)
        else:
            data["text"] = message["text"]
            await bot.send_message(**data)
    except exceptions.CantParseEntities as e:
        logger.error(e)
    except exceptions.BotBlocked:
        return logger.error(f"Target [ID:{user_id}]: invalid user ID")
    except exceptions.RetryAfter as e:
        logger.error(f"Target [ID:{user_id}]: Flood limit is exceeded. Sleep {e.timeout} seconds.")
        await asyncio.sleep(e.timeout)
        return await send_new(user, message)  # Recursive call
    except exceptions.UserDeactivated:
        return logger.error(f"Targe [ID:{user_id}]: user is deactivated")
    except exceptions.TelegramAPIError:
        logger.error(f"Target [ID:{user_id}]: failed")
    else:
        # Save sended new to DB
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
            try:
                await bot.send_message(
                    user_id, "На данный момент новостей нет, повторите попытку позже."
                )
                return
            except exceptions.BotBlocked as e:
                return logger.error(e)

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

        await asyncio.sleep(180)
