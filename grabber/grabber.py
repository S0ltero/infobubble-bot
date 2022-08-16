
import os
import shutil
import requests

import aiohttp
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from pyrogram import Client, types
from pyrogram.errors import ChannelInvalid, PeerIdInvalid, ChannelPrivate

API_ID   = os.getenv("GRABBER_API_ID")
API_HASH = os.getenv("GRABBER_API_HASH")
BASE_URL = os.getenv("DJANGO_HOST")
SHARED_CHANNEL_ID = os.getenv("TELEGRAM_SHARED_CHANNEL_ID")

app = Client("my_account", API_ID, API_HASH)
media_group_ids = set()

response = requests.get(f"{BASE_URL}/api/channels/ids")
channels_ids = response.json()

async def send_data(
    message_id,
    message_text,
    channel_id,
    media_group_id=None
    ):

    data = {
        "message_id": message_id,
        "channel": channel_id,
        "text": message_text,
        "media_group_id": media_group_id
    }

    async with aiohttp.ClientSession() as session:
        status = None
        while status != 201:
            async with session.post(url=f"{BASE_URL}/api/messages/", json=data) as response:
                status = response.status
                if status == 400:
                    return logger.error(await response.json())


async def get_channels():
    global channels_ids
    async with aiohttp.ClientSession() as session:
        async with session.get(url=f"{BASE_URL}/api/channels/ids") as response:
            channels_ids = await response.json()


async def check_channels():
    async with aiohttp.ClientSession() as session:
        async with session.get(url=f'{BASE_URL}/api/channels/') as response:
            channels = await response.json()

    for channel in channels:

        channel_url, channel_id = channel

        free_space = shutil.disk_usage(__file__)[2] // (1024**3)
        if free_space < 5:
            return

        try:
            channel = await app.join_chat(channel_url)
        except (ChannelInvalid, ChannelPrivate, PeerIdInvalid) as e:
            return logger.error(e)

        if not channel_id:
            data = {"channel_id": channel.id}
            async with aiohttp.ClientSession() as session:
                async with session.patch(f"{BASE_URL}/api/channels/{channel_url}/", data=data) as response:
                    pass

        # For now not working collecting last messages
        # because problem with duplicate messages

        return

        message_ids = [message.id async for message in app.get_chat_history(channel.id, limit=5)]
        forward_messages = await app.forward_messages(
            chat_id=SHARED_CHANNEL_ID, from_chat_id=channel.id, message_ids=message_ids
        )
        for message in forward_messages:
            message: types.Message
            text = message.text.html if message.text else ""
            await send_data(
                message_id=message.forward_from_message_id,
                message_text=text,
                channel_id=channel.id,
            )


@app.on_message(lambda client, message: str(message.chat.id) in channels_ids)
async def on_message(client: Client, message: types.Message):
    chat = message.chat

    free_space = shutil.disk_usage(__file__)[2] // (1024**3)
    if free_space < 5:
        return

    forward_message_ids = []
    forward_media_group_id = None

    if message.media_group_id:
        # Check if message with that media_group_id already sended to DB
        if message.media_group_id in media_group_ids:
            return
        media_group_ids.add(message.media_group_id)

        # Get all messages by media_group_id for forwarding to Shared Channel
        messages = await app.get_media_group(chat_id=chat.id, message_id=message.id)
        forward_message_ids = [message.id for message in messages]
    else:
        forward_message_ids.append(message.id)

    # Forward message to Shared Channel
    forward_messages = await app.forward_messages(
        chat_id=SHARED_CHANNEL_ID, from_chat_id=chat.id, message_ids=forward_message_ids
    )

    # Get new media_group_id from forwarded message
    if message.media_group_id:
        forward_media_group_id = forward_messages[0].media_group_id

    if message.media:
        text = message.caption.html if message.caption else ""
    else:
        text = message.text.html if message.text else ""

    await send_data(
        message_id=message.id,
        message_text=text,
        channel_id=chat.id,
        media_group_id=forward_media_group_id
    )


sheduler = AsyncIOScheduler()
sheduler.add_job(check_channels, "interval", minutes=5)
sheduler.add_job(get_channels, "interval", minutes=2)
sheduler.start()

app.run()