import json
import asyncio
import random
import re
import os
from pathlib import Path
from datetime import datetime

import aiohttp
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import ChatNotFound, BadRequest
from loguru import logger

URL = os.getenv('DJANGO_HOST')
API_TOKEN = os.getenv('TELEGRAM_TOKEN')

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

news_filters = ['ИТ', 'Дизайн', 'Бизнес', 'Игры', 'Новости', "Блоги", "Продажи", "Музыка","Позновательное", "Цитаты"]
user_filters = {}
user_history = {}


async def get_channel(text: str):
    pattern = r'https:\/\/t\.me\/(.+)'
    if text.startswith('@'):
        channel = text
        return channel
    elif re.match(pattern, text):
        result = re.match(pattern, text)
        channel = f"@{result.group(1)}"
        return channel
    else:
        return None


# States
class SubscribeForm(StatesGroup):
    channel = State()


class UnsubscribeForm(StatesGroup):
    channel = State()


class AddFilterWords(StatesGroup):
    words = State()


class RemoveFilterWords(StatesGroup):
    words = State()


@dp.message_handler(commands=['start'])
async def start(message):
    '''Инициируем добавление нового пользователя'''
    user_id = message.from_user.id

    # Проверяем проходил ли пользователь настройку
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{URL}/api/user/{user_id}') as response:
            if response.status == 200:
                user = await response.json()
                text = ('Вы уже проходили настройку!\nДля изменения категорий воспользуйтесь командой: /changefilters')
                await bot.send_message(message.chat.id, text)
                return await send_news(user)

    # Инициализируем настройку
    markup = types.InlineKeyboardMarkup()
    buttons = []
    i = 0
    num_pages = len(news_filters) % 8

    for _filter in news_filters[:8]:
        i+=1
        buttons.append(types.InlineKeyboardButton(text=_filter, callback_data=_filter))
        if i == 2:
            i = 0
            markup.row(*buttons)
            buttons = []
    markup.row(
        types.InlineKeyboardButton('Назад', callback_data='previous_filters'),
        types.InlineKeyboardButton(f'1/{num_pages}', callback_data='page_count'),
        types.InlineKeyboardButton('Далее', callback_data='next_filters')
    )
    markup.add(types.InlineKeyboardButton('Сохранить', callback_data='complete'))
    text = (
        'Привет! Слишком много каналов в Telegram? Сложно это всё читать, понимаю. '
        'Я тут, кстати как раз для того чтобы помочь тебе в этом. Давай определимся с твоими вкусами. '
        'Выбирай, что тебе нравится (как определишься, нажми «Сохранить»):'
    )
    await bot.send_message(message.chat.id, text, reply_markup=markup)


@dp.message_handler(commands=['help'])
async def help(message):
    text = (
        'Ты можешь написать мне: /changefilters — чтобы вернуться к информационным фильтрам и поправить их. '
        'Как столько ты ставишь ❤ или 👎🏻 последнему посту, я отправляю тебе новый.'
    )
    await bot.send_message(message.chat.id, text)


@dp.callback_query_handler(lambda call: call.data in news_filters)
async def filter_click_inline(call):
    '''Собираем фильтры пользователя'''
    choosen_filter = call.data
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    try:
        existing_filters = user_filters[user_id]
    except KeyError:
        event_type = 'append'
        user_filters[user_id] = [choosen_filter]
    else:
        if choosen_filter in existing_filters:
            event_type = 'remove'
            existing_filters.remove(choosen_filter)
        else:
            event_type = 'append'
            existing_filters.append(choosen_filter)
        user_filters[user_id] = existing_filters

    markup = call.message.reply_markup
    for i, row in enumerate(markup.inline_keyboard):
        try:
            filter_button = next(btn for btn in row if btn.callback_data == choosen_filter)
            btn_index = row.index(filter_button)
        except StopIteration:
            continue
        else:
            if event_type == 'append':
                filter_button.text = f'{choosen_filter} ✅'
            elif event_type == 'remove':
                filter_button.text = choosen_filter
            row[btn_index] = filter_button
            markup.inline_keyboard[i] = row
            break

    await bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup
    )


@dp.callback_query_handler(lambda call: call.data == 'complete')
async def complete_click_inline(call):
    '''Сохраняем пользователя и его фильтры в базу данных'''
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if not user_filters.get(user_id):
        return await bot.answer_callback_query(call.id, 'Вам необходима выбрать хотя бы одну категорию!')

    data = {
        'id': user_id,
        'filters': user_filters[user_id]
    }

    async with aiohttp.ClientSession() as session:
        response = await session.post(url=f'{URL}/api/user/', json=data)
    if response.status == 201:
        await bot.answer_callback_query(call.id, 'Настройка завершена!')
        await bot.delete_message(chat_id, message_id)
        text = (
            'Отлично, информационные фильтры заданы! Так я буду лучше понимать тебя. '
            'Теперь, я буду присылать тебе посты, а ты их оценивать, я присылать, а ты оценивать, я присылать... и так далее. '
            'Если возникнут проблемы, ты всегда можешь заручиться моей поддержкой, написав /help'
        )
        await bot.send_message(call.from_user.id, text)
        user = await response.json()
        await send_news(user)


@dp.callback_query_handler(lambda call: call.data.startswith('like'))
async def on_like(call):
    user_id = call.from_user.id
    message_id = call.message.message_id
    channel_id = call.data.split('_')[1]
    data = {
        'user_id': user_id,
        'message_id':message_id,
        'channel_id': channel_id,
        'rate': True
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url=f'{URL}/api/rate/', json=data) as response:
            if response.status != 201:
                return logger.error(await response.text())
        async with session.get(url=f'{URL}/api/user/{user_id}') as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())
    
    await send_news(user)


@dp.callback_query_handler(lambda call: call.data.startswith('nolike'))
async def on_nolike(call):
    user_id = call.from_user.id
    message_id = call.message.message_id
    channel_id = call.data.split('_')[1]
    data = {
        'user_id': user_id,
        'message_id':message_id,
        'channel_id': channel_id,
        'rate': False
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url=f'{URL}/api/rate/', json=data) as response:
            if response.status != 201:
                return logger.error(await response.text())
        async with session.get(url=f'{URL}/api/user/{user_id}') as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())
    
    await send_news(user)


@dp.callback_query_handler(lambda call: call.data == 'next')
async def next_news(call):
    user_id = call.from_user.id
    async with aiohttp.ClientSession() as session:
        async with session.get(url=f'{URL}/api/user/{user_id}') as response:
            if response.status == 200:
                user = await response.json()
    await send_news(user)


@dp.message_handler(commands=['news'])
async def send_new(message):
    user_id = message.from_user.id
    async with aiohttp.ClientSession() as session:
        async with session.get(url=f'{URL}/api/user/{user_id}') as response:
            if response.status == 200:
                user = await response.json()
    await send_news(user)


@dp.message_handler(commands=['changefilters'])
async def change_filters(message):
    '''Редактируем фильтры пользователя'''
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Получаем фильтры пользователя
    try:
        existing_filters = user_filters[user_id]
    except KeyError:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=f'{URL}/api/user/{user_id}') as response:
                if response.status == 200:
                    existing_filters = (await response.json())['filters']
                    user_filters[user_id] = existing_filters
                elif response.status == 404:
                    return await bot.send_message(
                        chat_id=chat_id, 
                        text='Вы ещё не проходили настройку! Воспользуйтесь командой /start'
                    )
                else:
                    return logger.error(await response.text())

    markup = types.InlineKeyboardMarkup()
    buttons = []
    i = 0
    num_pages = len(news_filters) % 8

    for _filter in news_filters[:8]:
        if _filter in existing_filters:
            i+=1
            buttons.append(types.InlineKeyboardButton(text=f'{_filter} ✅', callback_data=_filter))
        else:
            i+=1
            buttons.append(types.InlineKeyboardButton(text=_filter, callback_data=_filter))
        if i == 2:
            i = 0
            markup.row(*buttons)
            buttons = []
    markup.row(
        types.InlineKeyboardButton('Назад', callback_data='previous_filters'),
        types.InlineKeyboardButton(f'1/{num_pages}', callback_data='page_count'),
        types.InlineKeyboardButton('Далее', callback_data='next_filters')
    )
    markup.add(types.InlineKeyboardButton('Сохранить', callback_data='changefilters'))

    await bot.send_message(chat_id, 'Измените категории', reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data in ('previous_filters', 'next_filters'))
async def on_nav_filters_click_inline(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    save_btn = call.message.reply_markup.inline_keyboard[-1][0]
    nav_buttons = call.message.reply_markup.inline_keyboard[-2]
    num_pages_btn = nav_buttons[1]
    current_page, count_pages = map(int, num_pages_btn.text.split('/'))

    if current_page == count_pages and call.data == 'next_filters':
        return
    elif current_page == 1 and call.data == 'previous_filters':
        return

    if call.data == 'previous_filters':
        next_page = current_page - 1
    else:
        next_page = current_page + 1
    num_pages_btn.text = f'{next_page}/{count_pages}'
    nav_buttons[1] = num_pages_btn

    # Получаем фильтры пользователя
    try:
        existing_filters = user_filters[user_id]
    except KeyError:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=f'{URL}/api/user/{user_id}') as response:
                if response.status == 200:
                    existing_filters = (await response.json())['filters']
                else:
                    return logger.error(await response.text())

    markup = types.InlineKeyboardMarkup()
    buttons = []
    i = 0
    start_index = current_page * 8
    if next_page == 1:
        start_index = 0
    stop_index = next_page * 8

    for _filter in news_filters[start_index:stop_index]:
        if _filter in existing_filters:
            i+=1
            buttons.append(types.InlineKeyboardButton(text=f'{_filter} ✅', callback_data=_filter))
        else:
            i+=1
            buttons.append(types.InlineKeyboardButton(text=_filter, callback_data=_filter))
        if i == 2:
            i = 0
            markup.row(*buttons)
            buttons = []
    markup.row(*nav_buttons)
    markup.add(save_btn)

    await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data == 'changefilters')
async def change_filters_click_inline(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    if not user_filters.get(user_id):
        return await bot.answer_callback_query(call.id, 'Вам необходимо выбрать хотя бы одну категорию!')

    data = {
        'id': user_id,
        'filters': user_filters[user_id]
    }

    async with aiohttp.ClientSession() as session:
        async with session.put(url=f'{URL}/api/user/', json=data) as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())

    await bot.answer_callback_query(call.id, text='Категории успешно изменены!')
    await bot.delete_message(chat_id, message_id)

    await send_news(user)


@dp.message_handler(commands=['filterwords'])
async def filter_words(message):
    user_id = message.from_user.id

    # Проверяем проходил ли пользователь настройку
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{URL}/api/user/{user_id}') as response:
            if response.status != 200:
                text = "Вы ещё не проходили настройку.\nВоспользуйтесь командой: /start"
                return await bot.send_message(message.chat.id, text)


    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton('Добавить слова-фильтры', callback_data='add_filter_words'),
        types.InlineKeyboardButton('Удалить слова-фильтры', callback_data='remove_filter_words')
    )

    text = ('Фильтрация. Слова-фильтры позволяют исключать новости, содержащие те ключевые слова, которые Вы укажете. \n\n'
            'Выберите действие')

    await bot.send_message(message.chat.id, text, reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data == 'add_filter_words')
async def add_filter_words(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    async with aiohttp.ClientSession() as session:
        async with session.get(url=f'{URL}/api/user/{user_id}') as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())

    await AddFilterWords.words.set()

    if not user.get('filter_words'):
        text = ('Укажите слова-фильтры, которые нужно добавить, через запятую с пробелом (прим.: реклама, инвестиции). \n\n'
                'Текущие слова фильтры: отсутствуют')
    else:
        text = ('Укажите слова-фильтры, которые нужно добавить, через запятую с пробелом (прим.: реклама, инвестиции). \n\n'
                'Текущие слова фильтры: ' + ', '.join(user['filter_words']))

    await bot.send_message(chat_id, text)
    await bot.delete_message(chat_id, message_id)


@dp.callback_query_handler(lambda call: call.data == 'remove_filter_words')
async def remove_filter_words(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id

    async with aiohttp.ClientSession() as session:
        async with session.get(url=f'{URL}/api/user/{user_id}') as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())

    await RemoveFilterWords.words.set()

    if not user.get('filter_words'):
        text = ('Укажите через запятую с пробелом слова-фильтры, которые нужно удалить (прим.: реклама, инвестиции). \n\n'
                'Текущие слова фильтры: отсутствуют')
    else:
        text = ('Укажите через запятую с пробелом слова-фильтры, которые нужно удалить (прим.: реклама, инвестиции). \n\n'
                'Текущие слова фильтры: ' + ', '.join(user['filter_words']))

    await bot.send_message(chat_id, text)
    await bot.delete_message(chat_id, message_id)


@dp.message_handler(state=AddFilterWords.words)
async def process_add_filter_words(message, state):
    user_id = message.from_user.id

    async with aiohttp.ClientSession() as session:
        async with session.get(url=f'{URL}/api/user/{user_id}') as response:
            if response.status == 200:
                user = await response.json()
            else:
                await state.finish()
                return logger.error(await response.text())
    
    add_words = list(map(lambda x: x.strip(), message.text.split(',')))
    add_words = list(map(lambda x: x.lower(), add_words))
    if user.get('filter_words'):
        words = [*user['filter_words'], *add_words]
    else:
        words = add_words

    words = list(set(words))

    data = {
        'id': user_id,
        'filter_words': words
    }

    async with aiohttp.ClientSession() as session:
        async with session.put(url=f'{URL}/api/user/', json=data) as response:
            if response.status == 200:
                user = await response.json()
            else:
                await state.finish()
                return logger.error(await response.text())

    await state.finish()
    await bot.send_message(message.chat.id, text='Слова фильтры успешно изменены!')


@dp.message_handler(state=RemoveFilterWords.words)
async def process_remove_filter_words(message, state):
    user_id = message.from_user.id

    async with aiohttp.ClientSession() as session:
        async with session.get(url=f'{URL}/api/user/{user_id}') as response:
            if response.status == 200:
                user = await response.json()
            else:
                await state.finish()
                return logger.error(await response.text())
    
    remove_words = list(map(lambda x: x.strip(), message.text.split(',')))
    remove_words = list(map(lambda x: x.lower(), remove_words))
    words = [word for word in user['filter_words'] if word not in remove_words]

    data = {
        'id': user_id,
        'filter_words': words
    }

    async with aiohttp.ClientSession() as session:
        async with session.put(url=f'{URL}/api/user/', json=data) as response:
            if response.status == 200:
                user = await response.json()
            else:
                await state.finish()
                return logger.error(await response.text())

    await state.finish()
    await bot.send_message(message.chat.id, text='Слова фильтры успешно изменены!')


@dp.message_handler(commands=['subscribes'])
async def subscribes(message):
    user_id = message.from_user.id

    # Проверяем проходил ли пользователь настройку
    async with aiohttp.ClientSession() as session:
        async with session.get(f'{URL}/api/user/{user_id}') as response:
            if response.status != 200:
                text = "Вы ещё не проходили настройку.\nВоспользуйтесь командой: /start"
                return await bot.send_message(message.chat.id, text)
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton('Добавить канал', callback_data='subscribe'),
        types.InlineKeyboardButton('Удалить канал', callback_data='unsubscribe')
    )

    await bot.send_message(message.chat.id, 'Вы можете добавить каналы, с которых Вам будут приходить новости. Данные новости обновляются с публикацией их на каланах подписки, а не в стандартной логике.', reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data == 'subscribe')
async def subscribe_click_inline(call):
    # Set state
    await SubscribeForm.channel.set()

    text = 'Чтобы добавить канал, отправьте @упоминание или ссылку на канал, с которого (Вы) хотите получать новости.'

    await bot.delete_message(call.message.chat.id, call.message.message_id)
    await bot.send_message(call.message.chat.id, text)


@dp.callback_query_handler(lambda call: call.data == 'unsubscribe')
async def unsubscribe_click_inline(call):
    # Set state
    await UnsubscribeForm.channel.set()

    text = 'Чтобы удалить канал, отправьте @упоминание или ссылку на него.'

    await bot.delete_message(call.message.chat.id, call.message.message_id)
    await bot.send_message(call.message.chat.id, text)


@dp.message_handler(state=SubscribeForm.channel)
async def process_subscribe_channel(message, state):
    user_id = message.from_user.id
    channel = await get_channel(message.text)
    if not channel:
        await state.finish()
        await bot.send_message(
            chat_id=message.chat.id,
            text='Указанное значение не является @упоминанием или ссылкой на канал. Пожалуйста, попробуйте ввести другое значение.'
        )

    try:
        channel = await bot.get_chat(channel)
    except ChatNotFound:
        await state.finish()
        await bot.send_message(
            chat_id=message.chat.id,
            text='К сожалению, указанный канал не найден.'
        )

    async with aiohttp.ClientSession() as session:
        response = await session.get(f'{URL}/api/channel/{channel.id}')
        if response.status == 404:
            data = {"channel_id": channel.id, "channel_url": "test", "title": channel.title, "tags": []}
            response = await session.post(f'{URL}/api/channel/', json=data)
            if response != 201:
                await state.finish()
                return logger.error(await response.text())

        response = await session.get(f'{URL}/api/subscribe/{channel.id}/{user_id}')
        if response.status == 200:
            await state.finish()
            await bot.send_message(
                chat_id=message.chat.id,
                text=f'Вы уже подписаны на канал @{channel.username}'
            )
            return
        data = {"channel_id": channel.id, "user_id": user_id}
        response = await session.post(f'{URL}/api/subscribe/', json=data)
        if response.status != 201:
            await state.finish()
            return logger.error(await response.text())

    await bot.send_message(
            chat_id=message.chat.id,
            text=f"Вы успешно подписались на канал @{channel.username}"
        )
    await state.finish()


@dp.message_handler(state=UnsubscribeForm.channel)
async def process_unsubscribe_channel(message, state):
    user_id = message.from_user.id
    channel = await get_channel(message.text)
    if not channel:
        await state.finish()
        await bot.send_message(
            chat_id=message.chat.id,
            text='Указанное значение не является ссылкой на канал или @упоминанием'
        )
    try:
        channel = await bot.get_chat(channel)
    except ChatNotFound:
        await state.finish()
        await bot.send_message(
            chat_id=message.chat.id,
            text='Указанный канал не найден'
        )
        return
    
    async with aiohttp.ClientSession() as session:
        response = await session.delete(f'{URL}/api/subscribe/{channel.id}/{user_id}')
        if response.status == 404:
            await state.finish()
            await bot.send_message(
                chat_id=message.chat.id,
                text=f"Вы не подписаны на канал @{channel.username}"
            )
            return
        elif response.status != 204:
            await state.finish()
            return logger.error(await response.text())
    
    await bot.send_message(
            chat_id=message.chat.id,
            text=f"Вы успешно отписались от канала @{channel.username}"
        )
    await state.finish()


async def send_news(user, is_subscribe = False):
    user_id = user['id']

    while True:
        await asyncio.sleep(0)
        if is_subscribe and user.get("subscribe_ids"):
            channel = random.choice(user["subscribe_ids"])
        elif not is_subscribe and user.get("channel_ids"):
            channel = random.choice(user["channel_ids"])
        else:
            continue

        try:
            channel = await bot.get_chat(channel)
        except ChatNotFound:
            async with aiohttp.ClientSession() as session:
                response = await session.get(url=f'{URL}/api/channel/{channel}')
                channel = (await response.json())['channel_url']
                channel = await bot.get_chat(channel)

        channels_dir = Path(__file__).parent / "downloads"
        channel_file = f"{channel.username}{random.randint(0, 4)}.json"
        channel_file = channels_dir / channel_file

        if not channel_file.exists():
            continue

        with open(channel_file) as fh:
            data = json.load(fh)

        # Проверяем отправлялась ли новость раньше
        if not user_history.get(user_id):
            user_history[user_id] = []

        if data["message_id"] in user_history[user_id]:
            continue
        else:
            async with aiohttp.ClientSession() as session:
                response = await session.get(url=f'{URL}/api/history/{user_id}/{channel.id}/{data["message_id"]}')
            if response.status == 200:
                user_history[user_id].append(data["message_id"])
                continue

        # Проверяем содержит ли новость фильтруемые слова
        if user.get("filter_words"):
            if any(word for word in user["filter_words"] if word in data["text"].lower()):
                continue

        # Добавляем inline кнопки
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton('❤️', callback_data=f'like_{channel.id}'))
        markup.add(types.InlineKeyboardButton('👎', callback_data=f'nolike_{channel.id}'))
        markup.add(types.InlineKeyboardButton('Далее', callback_data='next'))

        has_file = True if data["filename"] else False
        file_path = channel_file.parent / data["filename"]

        try:
            if not has_file:
                await bot.send_message(
                    user_id,
                    data['text'], 
                    reply_markup=markup
                )
            elif file_path.suffix == '.mp4':
                await bot.send_video(
                    user_id,
                    file_path.open('rb'),
                    caption=data['text'],
                    reply_markup=markup
                )           
            else:
                await bot.send_photo(
                    user_id,
                    file_path.open('rb'),
                    caption=data['text'],
                    reply_markup=markup
                )
        except BadRequest as e:
            return logger.error(e)

        # Сохраняем новость в базу данных
        history_data = {
            'user_id': user_id,
            'message_id': data['message_id'],
            'channel_id': channel.id,
            'text': data['text'],
            'has_file': has_file
        }

        async with aiohttp.ClientSession() as session:
            response = await session.post(url=f'{URL}/api/history/', json=history_data)
            user_history[user_id].append(data['message_id'])
        
        if response.status != 201:
            return logger.error(await response.text())


async def day_news():
    while True:
        async with aiohttp.ClientSession() as session:
            try:
                response = await session.get(url=f'{URL}/api/config/')
            except aiohttp.ClientConnectionError:
                continue

            dt_now = datetime.now()
            dt_last_sent = (await response.json())['last_sent']
            dt_last_sent = datetime.strptime(dt_last_sent, '%Y-%m-%d')

            if dt_now.day == dt_last_sent.day:
                logger.info('Await next day to send everyday news')
                await asyncio.sleep(86400)
                continue

            try:
                response = await session.get(url=f'{URL}/api/users/')
            except aiohttp.ClientConnectionError:
                continue

            if response.status == 200:
                users = await response.json()
            elif response.status == 404:
                logger.error("Пользователи не найдены")
            else:
                logger.error(await response.text())

            for user in users:
                asyncio.ensure_future(send_news(user))

            data = {'last_sent': str(dt_now.date())}
            response = await session.patch(url=f'{URL}/api/config/', json=data)

            await asyncio.sleep(86400)


async def subscribe_news():
    while True:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url=f'{URL}/api/users/') as response:
                    if response.status == 200:
                        users = await response.json()
                    elif response.status == 404:
                        logger.error("Пользователи не найдены")
                    else:
                        logger.error(await response.text())
            except aiohttp.ClientConnectionError:
                continue

        for user in users:
            asyncio.ensure_future(send_news(user, is_subscribe=True))
        
        await asyncio.sleep(10)


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(day_news())
    loop.create_task(subscribe_news())
    executor.start_polling(dp, loop=loop)
