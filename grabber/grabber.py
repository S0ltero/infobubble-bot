
import os
import shutil

import aiohttp
from aiohttp import FormData

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from pyrogram import Client
from pyrogram.errors import ChannelInvalid, PeerIdInvalid

api_id   = os.getenv("GRABBER_API_ID")
api_hash = os.getenv("GRABBER_API_HASH")
URL = os.getenv("DJANGO_HOST")

app = Client("my_account", api_id, api_hash)


async def form_data(
    message_id,
    message_text,
    channel_id,
    channel_name,
    file_path=None,
    file_type=None
    ):
    if not message_text:
        message_text = ""

    if not message_text and not file_path:
        return

    data = FormData()
    data.add_field("message_id", str(message_id))
    data.add_field("channel", str(channel_id))
    data.add_field("text", message_text)

    if file_path:
        data.add_field("file", open(file_path, "rb"))
        data.add_field("file_type", file_type)

    async with aiohttp.ClientSession() as session:
        async with session.post(url=f"{URL}/api/messages/", data=data) as response:
            pass

    if file_path:
        try:
            os.remove(file_path)
        except OSError:
            pass


async def check_channels():
    async with aiohttp.ClientSession() as session:
        async with session.get(url=f'{URL}/api/channels/') as response:
            channels = await response.json()

    for channel in channels:

        channel_url, channel_id = channel

        free_space = shutil.disk_usage(__file__)[2] // (1024**3)
        if free_space < 5:
            return

        if not channel_id:
            try:
                await app.join_chat(channel_url)
            except ChannelInvalid:
                pass
            channel_id = (await app.get_chat(channel_url))["id"]
            data = {"channel_id": channel_id}
            async with aiohttp.ClientSession() as session:
                async with session.patch(f"{URL}/api/channels/{channel_url}/", data=data) as response:
                    pass

        channel_id = int(channel_id)
        channel = await app.join_chat(channel_id)

        try:
            async for message in app.iter_history(channel_id, limit=5):
                chat = message.chat if message.chat else (message.get_chat())
                if message.media in ("photo", "video"):
                    path = await message.download(block=True)
                    await form_data(
                        message_id=message.message_id,
                        message_text=message.text,
                        channel_id=chat.id,
                        channel_name=chat.username,
                        file_path=path,
                        file_type=message.media
                    )
                elif not message.media and message.text:
                    await form_data(
                        message_id=message.message_id,
                        message_text=message.text,
                        channel_id=chat.id,
                        channel_name=chat.username,
                    )
        except PeerIdInvalid:
            print(f"У канала {channel_url} указан некорректный ID")


@app.on_message()
async def on_message(client, message):
    chat = message.chat

    free_space = shutil.disk_usage(__file__)[2] // (1024**3)
    if free_space < 5:
        return

    if message.media in ("photo", "video"):
        path = await message.download(block=True)

        await form_data(
            message_id=message.message_id,
            message_text=message.caption,
            channel_id=chat.id,
            channel_name=chat.username,
            file_path=path,
            file_type=message.media
        )
    elif not message.media and message.text:
        await form_data(
            message_id=message.message_id,
            message_text=message.text,
            channel_id=chat.id,
            channel_name=chat.username
        )

sheduler = AsyncIOScheduler()
sheduler.add_job(check_channels, "interval", seconds=10)

sheduler.start()
app.run()
