import os
from itertools import zip_longest

from aiogram import Bot, Dispatcher
from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

import aiohttp
from loguru import logger

API_TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = Bot(token=API_TOKEN)

news_filters = [
    "ИТ",
    "Дизайн",
    "Бизнес",
    "Игры",
    "Новости",
    "Блоги",
    "Продажи",
    "Музыка",
    "Позновательное",
    "Цитаты",
]


# States

class FiltersForm(StatesGroup):
    filters = State()


async def filter_click_inline(call: types.CallbackQuery, state: FSMContext):
    """Собираем фильтры пользователя"""
    choosen_filter = call.data
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    async with state.proxy() as data:
        filters = data.get("filters", [])

        if choosen_filter in filters:
            filters.remove(choosen_filter)
            event_type = "remove"
        else:
            filters.append(choosen_filter)
            event_type = "append"

        data["filters"] = filters

    markup = call.message.reply_markup
    for i, row in enumerate(markup.inline_keyboard):
        try:
            filter_button = next(
                btn for btn in row if btn.callback_data == choosen_filter
            )
            btn_index = row.index(filter_button)
        except StopIteration:
            continue
        else:
            if event_type == "append":
                filter_button.text = f"{choosen_filter} ✅"
            elif event_type == "remove":
                filter_button.text = choosen_filter
            row[btn_index] = filter_button
            markup.inline_keyboard[i] = row
            break

    await bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup
    )


async def complete_click_inline(call: types.CallbackQuery, state: FSMContext):
    """Сохраняем пользователя и его фильтры в базу данных"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    async with state.proxy() as data:
        filters = data.get("filters")
        channel = data.get("channel")

    if not filters:
        return await bot.answer_callback_query(
            call.id, "Вам необходима выбрать хотя бы одну категорию!"
        )

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("Подписки", callback_data="subscribes"),
        types.InlineKeyboardButton("Фильтры", callback_data="filters")
    )
    markup.row(
        types.InlineKeyboardButton("Слова-фильтры", callback_data="filterwords"),
        types.InlineKeyboardButton("Новости", callback_data="news")
    )

    async with aiohttp.ClientSession() as session:

        # Сохраняем пользователя
        data = {"id": user_id, "filters": filters}
        async with session.post(url=f"{URL}/api/users/", json=data) as response:
            if response.status == 201:
                await bot.delete_message(chat_id, message_id)
                text = (
                    "Отлично, информационные ресурсы и фильтры заданы! "
                    "Таким образом, я буду лучше понимать Вас и отсеивать ненужную информацию. "
                    "Теперь я буду присылать Вам посты, а от Вас требуется "
                    "ставить ❤️ или 👎🏻 последней новости, чтобы я отправил Вам новую.\n\n"
                    "Если у Вас появятся какие-либо вопросы, Вы захотите поменять "
                    "информационные ресурсы или фильтры, воспользуйтесь командой /help"
                )
                await bot.send_message(call.from_user.id, text, reply_markup=markup)
                user = await response.json()
                await get_news(user)
            else:
                logger.error(await response.json())

        # Сохраняем канал на который подписался пользователь
        data = {
            "channel_id": channel.id,
            "channel_url": channel.mention,
            "title": channel.title,
            "tags": [],
        }
        async with session.post(f"{URL}/api/channels/", json=data) as response:
            if response != 201:
                logger.error(await response.text())

        # Добавляем канал в подписки пользователя
        data = {"channel": channel.id, "user": user_id}
        async with session.post(f"{URL}/api/subscribe/", json=data) as response:
            if response.status != 201:
                await state.finish()
                return logger.error(await response.text())

    await state.finish()
    await bot.answer_callback_query(call.id, "Настройка завершена!")


async def change_filters(call: types.CallbackQuery, state: FSMContext):
    """Редактируем фильтры пользователя"""
    user_id = call.from_user.id
    if isinstance(call, types.CallbackQuery):
        await bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id
    else:
        chat_id = call.chat.id

    # Получаем фильтры пользователя
    async with aiohttp.ClientSession() as session:
        async with session.get(url=f"{URL}/api/users/{user_id}/") as response:
            if response.status == 200:
                existing_filters = (await response.json())["filters"]
            elif response.status == 404:
                return await bot.send_message(
                    chat_id=chat_id,
                    text="Вы ещё не проходили настройку! Воспользуйтесь командой /start",
                )
            else:
                return logger.error(await response.text())

    await FiltersForm.filters.set()
    state = dp.current_state(chat=chat_id, user=user_id)
    async with state.proxy() as data:
        data["filters"] = existing_filters

    markup = types.InlineKeyboardMarkup()
    num_pages = len(news_filters) % 8

    for filter_1, filter_2 in zip_longest(news_filters[0:8:2], news_filters[1:8:2]):
        if filter_1 in existing_filters:
            button_1 = types.InlineKeyboardButton(text=f"{filter_1} ✅", callback_data=filter_1)
        else:
            button_1 = types.InlineKeyboardButton(text=filter_1, callback_data=filter_1)

        if filter_2 in existing_filters:
            button_2 = types.InlineKeyboardButton(text=f"{filter_2} ✅", callback_data=filter_2)
        else:
            button_2 = types.InlineKeyboardButton(text=filter_2, callback_data=filter_2)
        markup.row(button_1, button_2)

    markup.row(
        types.InlineKeyboardButton("Назад", callback_data="previous_filters"),
        types.InlineKeyboardButton(f"1/{num_pages}", callback_data="page_count"),
        types.InlineKeyboardButton("Далее", callback_data="next_filters"),
    )
    markup.add(types.InlineKeyboardButton("Сохранить", callback_data="changefilters"))

    await bot.send_message(chat_id, "Измените категории", reply_markup=markup)


async def on_nav_filters_click_inline(call: types.CallbackQuery, state: FSMContext):
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    save_btn = call.message.reply_markup.inline_keyboard[-1][0]
    nav_buttons = call.message.reply_markup.inline_keyboard[-2]
    num_pages_btn = nav_buttons[1]
    current_page, count_pages = map(int, num_pages_btn.text.split("/"))

    if current_page == count_pages and call.data == "next_filters":
        return
    elif current_page == 1 and call.data == "previous_filters":
        return

    if call.data == "previous_filters":
        next_page = current_page - 1
    else:
        next_page = current_page + 1
    num_pages_btn.text = f"{next_page}/{count_pages}"
    nav_buttons[1] = num_pages_btn

    async with state.proxy() as data:
        existing_filters = data.get("filters", [])

    markup = types.InlineKeyboardMarkup()
    start_index_1 = current_page * 8
    if next_page == 1:
        start_index_1 = 0
    start_index_2 = start_index_1 + 1
    stop_index = next_page * 8

    for filter_1, filter_2 in zip_longest(news_filters[start_index_1:stop_index:2], news_filters[start_index_2:stop_index:2]):
        if filter_1 in existing_filters:
            button_1 = types.InlineKeyboardButton(text=f"{filter_1} ✅", callback_data=filter_1)
        else:
            button_1 = types.InlineKeyboardButton(text=filter_1, callback_data=filter_1)

        if filter_2 in existing_filters:
            button_2 = types.InlineKeyboardButton(text=f"{filter_2} ✅", callback_data=filter_2)
        else:
            button_2 = types.InlineKeyboardButton(text=filter_2, callback_data=filter_2)
        markup.row(button_1, button_2)

    markup.row(*nav_buttons)
    markup.add(save_btn)

    await bot.edit_message_reply_markup(
        chat_id=chat_id, message_id=message_id, reply_markup=markup
    )


async def change_filters_click_inline(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    async with state.proxy() as data:
        filters = data.get("filters", [])

        if not filters:
            return await bot.answer_callback_query(
                call.id, "Вам необходимо выбрать хотя бы одну категорию!"
            )

    data = {"id": user_id, "filters": filters}

    async with aiohttp.ClientSession() as session:
        async with session.patch(url=f"{URL}/api/users/{user_id}/", json=data) as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())

    await bot.answer_callback_query(call.id, text="Категории успешно изменены!")
    await bot.delete_message(chat_id, message_id)
    await state.finish()
    await get_news(user)


def setup(dp: Dispatcher):
    # Message handlers
    dp.register_message_handler(
        change_filters,
        commands=["changefilters"]
    )

    # Query handlers
    dp.register_callback_query_handler(
        change_filters,
        lambda call: call.data == "filters"
    )
    dp.register_callback_query_handler(
        filter_click_inline,
        lambda call: call.data in news_filters
    )
    dp.register_callback_query_handler(
        complete_click_inline,
        lambda call: call.data == "complete"
    )
    dp.register_callback_query_handler(
        on_nav_filters_click_inline,
        lambda call: call.data in ("previous_filters", "next_filters")
    )
    dp.register_callback_query_handler(
        change_filters_click_inline,
        lambda call: call.data == "changefilters"
    )