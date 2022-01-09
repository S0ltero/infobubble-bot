import configparser
import json
import asyncio
import random
import os
from os import path

import aiohttp
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from loguru import logger

config = configparser.ConfigParser()
config.read(path.join(path.dirname(path.abspath(__file__)), 'config.ini'))
URL = config['Django']['url']
API_TOKEN = config['Telegram']['token']

bot = AsyncTeleBot(API_TOKEN)

news_filters = ['ИТ', 'Дизайн', 'Бизнес', 'Игры', 'Новости', "Блоги", "Продажи", "Музыка","Позновательное", "Цитаты"]
user_filters = {}
markup_button = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
itembtn1 = types.KeyboardButton('Изменить фильтры')
itembtn2 = types.KeyboardButton('Получить новости')
markup_button.add(itembtn1, itembtn2)


@bot.message_handler(commands=['start'])
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
    markup = types.InlineKeyboardMarkup(row_width=3)
    num_pages = len(news_filters) % 8

    for _filter in news_filters:
        markup.row(types.InlineKeyboardButton(_filter, callback_data=_filter))

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


@bot.message_handler(commands=['help'])
async def help(message):
    text = (
        'Ты можешь написать мне: /changefilters — чтобы вернуться к информационным фильтрам и поправить их. '
        'Как столько ты ставишь ❤ или 👎🏻 последнему посту, я отправляю тебе новый.'
    )
    await bot.send_message(message.chat.id, text)


@bot.callback_query_handler(func=lambda call: call.data in news_filters)
async def filter_click_inline(call):
    '''Собираем фильтры пользователя'''
    choosen_filter = call.data
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.id

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
    for i, row in enumerate(markup.keyboard):
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
            markup.keyboard[i] = row
            break

    await bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == 'complete')
async def complete_click_inline(call):
    '''Сохраняем пользователя и его фильтры в базу данных'''
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.id

    if not user_filters.get(user_id):
        return await bot.answer_callback_query(call.id, 'Вам необходима выбрать хотя бы одну категорию!')

    data = {
        'id': user_id,
        'filters': user_filters[user_id]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url=f'{URL}/api/user/', json=data) as response:
            if response.status == 201:
                await bot.answer_callback_query(call.id, 'Настройка завершена!')
                await bot.delete_message(chat_id, message_id)
                text = (
                    'Отлично, информационные фильтры заданы! Так я буду лучше понимать тебя. '
                    'Теперь, я буду присылать тебе посты, а ты их оценивать, я присылать, а ты оценивать, я присылать... и так далее. '
                    'Если возникнут проблемы, ты всегда можешь заручиться моей поддержкой, написав /help'
                )
                await bot.send_message(call.from_user.id, text)
                await send_news(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('like'))
async def on_like(call):
    user_id = call.from_user.id
    message_id = call.message.id
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


@bot.callback_query_handler(func=lambda call: call.data.startswith('nolike'))
async def on_nolike(call):
    user_id = call.from_user.id
    message_id = call.message.id
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


@bot.callback_query_handler(func=lambda call: call.data == 'next')
async def next_news(call):
    user_id = call.from_user.id
    async with aiohttp.ClientSession() as session:
        async with session.get(url=f'{URL}/api/user/{user_id}') as response:
            if response.status == 200:
                user = await response.json()
    await send_news(user)


@bot.message_handler(commands=['news'])
async def send_new(message):
    user_id = message.from_user.id
    async with aiohttp.ClientSession() as session:
        async with session.get(url=f'{URL}/api/user/{user_id}') as response:
            if response.status == 200:
                user = await response.json()
    await send_news(user)


@bot.message_handler(commands=['changefilters'])
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


@bot.callback_query_handler(func=lambda call: call.data in ('previous_filters', 'next_filters'))
async def on_nav_filters_click_inline(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.id

    save_btn = call.message.reply_markup.keyboard[-1][0]
    nav_buttons = call.message.reply_markup.keyboard[-2]
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


@bot.callback_query_handler(func=lambda call: call.data == 'changefilters')
async def change_filters_click_inline(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.id

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


@bot.message_handler(content_types=["text"])
async def change_filters_click_inline(message):
    if message.text == "Изменить фильтры":
        await change_filters(message)
    if message.text == "Получить новости":
        await send_new(message)
    user_id = message.from_user.id
    if message.text != "Получить новости" and message.text != "Изменить фильтры":
        await bot.send_message(user_id,"Сейчас я отправляю новости, а возможно завтра захватываю мир :)", reply_markup=markup_button)


async def send_news(user, is_subscribe = False):
    user_id = user['id']

    while True:
        if is_subscribe:
            channel = random.choice(user["subscribe_ids"])
        else:
            channel = random.choice(user["channel_ids"])
        channels_dir = path.join(path.dirname(path.abspath(__file__)), "channels_dump")
        channel_file = f"{channel}{random.randint(0, 4)}.json"

        if not os.path.exists(path.join(channels_dir, channel_file)):
            continue

        with open(path.join(channels_dir, channel_file), 'r', encoding='utf-8') as fh:
            data = json.load(fh)

        # Проверяем отправлялась ли новость раньше
        async with aiohttp.ClientSession() as session:
            async with session.get(url=f'{URL}/api/history/{user_id}/{channel}/{data["message_id"]}') as response:
                if response.status == 200:
                    continue

        # Проверяем содержит ли новость фильтруемые слова
        if user.get("filter_words"):
            if any(word for word in user["filter_words"] in data["text"]):
                continue

        # Добавляем inline кнопки
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton('❤️', callback_data=f'like_{channel}'))
        markup.add(types.InlineKeyboardButton('👎', callback_data=f'nolike_{channel}'))
        markup.add(types.InlineKeyboardButton('Далее', callback_data='next'))

        # Проверяем содержит ли новость файлы
        if not data["filename"]:
            await bot.send_message(user_id, data['text'], reply_markup=markup)
        else:
            if path.join(path.dirname(path.abspath(__file__)), data['filename']).endswith('.mp4'):
                await bot.send_video(user_id,open(path.join(path.dirname(path.abspath(__file__)), data['filename']), 'rb'), caption=data['text'], reply_markup=markup)           
            else:
                await bot.send_photo(user_id,open(path.join(path.dirname(path.abspath(__file__)), data['filename']), 'rb'), caption=data['text'], reply_markup=markup)

        # Сохраняем отправленную новость в базу данных
        async with aiohttp.ClientSession() as session:
            has_file = True if data["filename"] else False
            data = {
                'user_id': user_id,
                'message_id': data['message_id'],
                'channel_id': channel,
                'text': data['text'],
                'has_file': has_file
            }
            async with session.post(url=f'{URL}/api/history/', json=data) as response:
                if response.status != 201:
                    return logger.error(await response.text())
                else:
                    return


async def day_news():
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=f'{URL}/api/users/') as response:
                if response.status == 200:
                    users = await response.json()
                elif response.status == 404:
                    return logger.error("Пользователи не найдены")
                else:
                    return logger.error(await response.text())

        for user in users:
            await send_news(user)
    
        await asyncio.sleep(86400)


async def subscribe_news():
    while True:
        async with aiohttp.ClientSession() as session:
            async with session.get(url=f'{URL}/api/users/') as response:
                if response.status == 200:
                    users = await response.json()
                elif response.status == 404:
                    return logger.error("Пользователи не найдены")
                else:
                    return logger.error(await response.text())

        for user in users:
            await send_news(user, is_subscribe=True)
        
        await asyncio.sleep(10)


loop = asyncio.get_event_loop()
asyncio.ensure_future(day_news())
asyncio.ensure_future(subscribe_news())
asyncio.run(bot.polling())
