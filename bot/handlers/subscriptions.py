import os
import re

from aiogram import Bot, Dispatcher
from aiogram import types
from aiogram.utils import exceptions
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import aiohttp
from loguru import logger

API_TOKEN = os.getenv("TELEGRAM_TOKEN")
URL = os.getenv("DJANGO_HOST")

bot = Bot(token=API_TOKEN)

# States
class SubscribeForm(StatesGroup):
    channel = State()


class UnsubscribeForm(StatesGroup):
    channel = State()


async def get_channel(text: str):
    pattern = r"https:\/\/t\.me\/(.+)"
    if text.startswith("@"):
        channel = text
        return channel
    elif re.match(pattern, text):
        result = re.match(pattern, text)
        channel = f"@{result.group(1)}"
        return channel
    else:
        return None


async def subscribes(call: types.CallbackQuery):
    user_id = call.from_user.id
    if isinstance(call, types.CallbackQuery):
        await bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
    else:
        chat_id = call.chat.id

    # Проверяем проходил ли пользователь настройку
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{URL}/api/users/{user_id}/") as response:
            if response.status != 200:
                text = "Вы ещё не проходили настройку.\nВоспользуйтесь командой: /start"
                return await bot.send_message(chat_id, text)

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("Добавить канал", callback_data="subscribe"),
        types.InlineKeyboardButton("Удалить канал", callback_data="unsubscribe"),
    )

    await bot.send_message(
        chat_id,
        "Вы можете добавить каналы, с которых Вам будут приходить новости. Данные новости обновляются с публикацией их на каналах подписки, а не в стандартной логике.",
        reply_markup=markup,
    )


async def subscribe_click_inline(call: types.CallbackQuery):
    # Set state
    await SubscribeForm.channel.set()

    text = "Чтобы добавить канал, отправьте @упоминание или ссылку на канал, с которого (Вы) хотите получать новости."

    await bot.delete_message(call.message.chat.id, call.message.message_id)
    await bot.send_message(call.message.chat.id, text)


async def unsubscribe_click_inline(call: types.CallbackQuery):
    # Set state
    await UnsubscribeForm.channel.set()

    text = "Чтобы удалить канал, отправьте @упоминание или ссылку на него."

    await bot.delete_message(call.message.chat.id, call.message.message_id)
    await bot.send_message(call.message.chat.id, text)


async def process_subscribe_channel(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    channel = await get_channel(message.text)
    if not channel:
        await state.finish()
        await bot.send_message(
            chat_id=message.chat.id,
            text="Указанное значение не является @упоминанием или ссылкой на канал. Пожалуйста, попробуйте ввести другое значение.",
        )

    try:
        channel = await bot.get_chat(channel)
    except exceptions.ChatNotFound:
        await state.finish()
        await bot.send_message(
            chat_id=message.chat.id, text="К сожалению, указанный канал не найден."
        )

    async with aiohttp.ClientSession() as session:
        data = {
            "channel_id": channel.id,
            "channel_url": channel.mention,
            "title": channel.title,
            "tags": [],
        }
        async with session.post(f"{URL}/api/channels/", json=data) as response:
            if response.status not in [201, 400]:
                await state.finish()
                return logger.error(await response.text())

        async with session.get(f"{URL}/api/subscribe/{channel.id}/{user_id}") as response:
            if response.status == 200:
                await state.finish()
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=f"Вы уже подписаны на канал {channel.mention}",
                )
                return
        data = {"channel": channel.id, "user": user_id}
        async with session.post(f"{URL}/api/subscribe/", json=data) as response:
            if response.status != 201:
                await state.finish()
                return logger.error(await response.text())

    await bot.send_message(
        chat_id=message.chat.id,
        text=f"Вы успешно подписались на канал {channel.mention}",
    )
    await state.finish()


async def process_unsubscribe_channel(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    channel = await get_channel(message.text)
    if not channel:
        await state.finish()
        await bot.send_message(
            chat_id=message.chat.id,
            text="Указанное значение не является ссылкой на канал или @упоминанием",
        )
    try:
        channel = await bot.get_chat(channel)
    except exceptions.ChatNotFound:
        await state.finish()
        await bot.send_message(
            chat_id=message.chat.id, text="Указанный канал не найден"
        )
        return

    async with aiohttp.ClientSession() as session:
        response = await session.delete(f"{URL}/api/subscribe/{channel.id}/{user_id}")
        if response.status == 404:
            await state.finish()
            await bot.send_message(
                chat_id=message.chat.id,
                text=f"Вы не подписаны на канал {channel.mention}",
            )
            return
        elif response.status != 204:
            await state.finish()
            return logger.error(await response.text())

    await bot.send_message(
        chat_id=message.chat.id,
        text=f"Вы успешно отписались от канала {channel.mention}",
    )
    await state.finish()


def setup(dp: Dispatcher):
    # Message handlers
    dp.register_message_handler(
        subscribes,
        commands=["subscribes"]
    )
    dp.register_message_handler(
        process_subscribe_channel,
        state=SubscribeForm.channel
    )
    dp.register_message_handler(
        process_unsubscribe_channel,
        state=UnsubscribeForm.channel
    )

    # Query handlers
    dp.register_callback_query_handler(
        subscribes,
        lambda call: call.data == "subscribes"
    )
    dp.register_callback_query_handler(
        subscribe_click_inline,
        lambda call: call.data == "subscribe"
    )
    dp.register_callback_query_handler(
        unsubscribe_click_inline,
        lambda call: call.data == "unsubscribes"
    )
