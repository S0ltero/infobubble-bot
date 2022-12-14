import os

from aiogram import Bot, Dispatcher
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import aiohttp
from loguru import logger

API_TOKEN = os.getenv("TELEGRAM_TOKEN")
URL = os.getenv("DJANGO_HOST")

bot = Bot(token=API_TOKEN)

# States
class FilterWordsForm(StatesGroup):
    add_words = State()
    remove_words = State()


async def filter_words(call: types.CallbackQuery):
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
        types.InlineKeyboardButton(
            "Добавить слова-фильтры", callback_data="add_filter_words"
        ),
        types.InlineKeyboardButton(
            "Удалить слова-фильтры", callback_data="remove_filter_words"
        ),
    )

    text = (
        "Фильтрация. Слова-фильтры позволяют исключать новости, содержащие те ключевые слова, которые Вы укажете. \n\n"
        "Выберите действие"
    )

    await bot.send_message(chat_id, text, reply_markup=markup)


async def add_filter_words(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    async with aiohttp.ClientSession() as session:
        async with session.get(url=f"{URL}/api/users/{user_id}/") as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())

    await FilterWordsForm.add_words.set()

    if not user.get("filter_words"):
        text = (
            "Укажите слова-фильтры, которые нужно добавить, через запятую с пробелом (прим.: реклама, инвестиции). \n\n"
            "Текущие слова фильтры: отсутствуют"
        )
    else:
        text = (
            "Укажите слова-фильтры, которые нужно добавить, через запятую с пробелом (прим.: реклама, инвестиции). \n\n"
            "Текущие слова фильтры: " + ", ".join(user["filter_words"])
        )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Помощь", callback_data="help"))

    await bot.delete_message(chat_id, message_id)
    message = await bot.send_message(chat_id, text=text, reply_markup=markup)

    async with state.proxy() as data:
        data["message"] = message


async def remove_filter_words(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    async with aiohttp.ClientSession() as session:
        async with session.get(url=f"{URL}/api/users/{user_id}/") as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())

    await FilterWordsForm.remove_words.set()

    if not user.get("filter_words"):
        text = (
            "Укажите через запятую с пробелом слова-фильтры, которые нужно удалить (прим.: реклама, инвестиции). \n\n"
            "Текущие слова фильтры: отсутствуют"
        )
    else:
        text = (
            "Укажите через запятую с пробелом слова-фильтры, которые нужно удалить (прим.: реклама, инвестиции). \n\n"
            "Текущие слова фильтры: " + ", ".join(user["filter_words"])
        )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Помощь", callback_data="help"))

    await bot.delete_message(chat_id, message_id)
    message = await bot.send_message(chat_id, text=text, reply_markup=markup)

    async with state.proxy() as data:
        data["message"] = message


async def process_add_filter_words(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    async with state.proxy() as data:
        prev_message: types.Message = data["message"]
        await prev_message.delete()

        if data.get("help_message"):
            help_message: types.Message = data["help_message"]
            await help_message.delete()

    await message.delete()

    async with aiohttp.ClientSession() as session:
        async with session.get(url=f"{URL}/api/users/{user_id}/") as response:
            if response.status == 200:
                user = await response.json()
            else:
                await state.finish()
                return logger.error(await response.text())

    add_words = set(map(lambda x: x.strip(), message.text.lower().split(",")))
    if user.get("filter_words"):
        add_words = add_words.update(user["filter_words"])

    if add_words:
        async with aiohttp.ClientSession() as session:
            data = {"id": user_id, "filter_words": add_words}
            async with session.patch(url=f"{URL}/api/users/{user_id}/", json=data) as response:
                if response.status == 200:
                    user = await response.json()
                else:
                    await state.finish()
                    return logger.error(await response.text())

    await state.finish()
    await bot.send_message(message.chat.id, text="Слова фильтры успешно изменены!")


async def process_remove_filter_words(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    async with state.proxy() as data:
        prev_message: types.Message = data["message"]
        await prev_message.delete()

        if data.get("help_message"):
            help_message: types.Message = data["help_message"]
            await help_message.delete()

    await message.delete()

    async with aiohttp.ClientSession() as session:
        async with session.get(url=f"{URL}/api/users/{user_id}/") as response:
            if response.status == 200:
                user = await response.json()
            else:
                await state.finish()
                return logger.error(await response.text())

    remove_words = list(map(lambda x: x.strip(), message.text.lower().split(",")))
    words = [word for word in user["filter_words"] if word not in remove_words]

    data = {"id": user_id, "filter_words": words}

    async with aiohttp.ClientSession() as session:
        async with session.patch(url=f"{URL}/api/users/{user_id}/", json=data) as response:
            if response.status == 200:
                user = await response.json()
            else:
                await state.finish()
                return logger.error(await response.text())

    await state.finish()
    await bot.send_message(message.chat.id, text="Слова фильтры успешно изменены!")


def setup(dp: Dispatcher):
    # Message handlers
    dp.register_message_handler(
        filter_words,
        commands=["filterwords"]
    )
    dp.register_message_handler(
        process_add_filter_words,
        state=FilterWordsForm.add_words
    )
    dp.register_message_handler(
        process_remove_filter_words,
        state=FilterWordsForm.remove_words
    )

    # Query handlers
    dp.register_callback_query_handler(
        filter_words,
        lambda call: call.data == "filterwords"
    )
    dp.register_callback_query_handler(
        add_filter_words,
        lambda call: call.data == "add_filter_words",
        state="*"
    )
    dp.register_callback_query_handler(
        remove_filter_words,
        lambda call: call.data == "remove_filter_words",
        state="*"
    )
