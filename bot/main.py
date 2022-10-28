import asyncio
import re
import os
from pathlib import Path
from itertools import zip_longest

import aiohttp

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import ChatNotFound

from loguru import logger

from handlers import filter_words
from handlers import filters
from handlers import subscriptions
from news import get_news, subscribe_news, day_news

URL = os.getenv("DJANGO_HOST")
API_TOKEN = os.getenv("TELEGRAM_TOKEN")
SHARED_CHANNEL_ID = os.getenv("TELEGRAM_SHARED_CHANNEL_ID")

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

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


# States
class StartForm(StatesGroup):
    channel = State()
    filters = State()


@dp.channel_post_handler(
    lambda message: message.chat.id == int(SHARED_CHANNEL_ID),
    content_types=types.ContentType.all()
)
async def shared_message_handler(message: types.Message):
    """
        Handler for forwarded messages from `grabber` service in `Shared Channel`

        Get `file_id` from media of forwarded messages, and send to `backend` service
    """
    if not message.is_forward():
        return

    forward_from_chat_id = message.forward_from_chat.id
    forward_from_message_id = message.forward_from_message_id

    media = []
    media_group_id = message.media_group_id

    async def _parse_media(media_type: str, item):
        """Iterate by media items of message and format data for sending by API"""
        media.append(
            {
                "file_id": item.file_id,
                "file_type": media_type,
                "media_group_id": media_group_id
            }
        )

    if message.photo:
        await _parse_media(media_type="PHOTO", item=message.photo[0])
    elif message.video:
        await _parse_media(media_type="VIDEO", item=message.video)
    elif message.video_note:
        await _parse_media(media_type="VIDEO_NOTE", item=message.video_note)
    elif message.document:
        await _parse_media(media_type="DOCUMENT", item=message.document)
    elif message.voice:
        await _parse_media(media_type="VOICE", item=message.voice)

    if media_group_id:
        api_url = f"{URL}/api/messages/media/{media_group_id}/"
    else:
        api_url = f"{URL}/api/messages/{forward_from_chat_id}/{forward_from_message_id}/media/"

    async with aiohttp.ClientSession() as session:
        status = None
        while status != 201:
            async with session.post(url=api_url, json=media) as response:
                status = response.status
                if status == 400:
                    return logger.error(await response.json())


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    """Handle call `start` command and start initialize of new user"""
    user_id = message.from_user.id

    # Проверяем проходил ли пользователь настройку
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{URL}/api/users/{user_id}/") as response:
            if response.status == 200:
                user = await response.json()
                text = (
                    "Вы уже проходили настройку! Если Вам нужно изменить подписки, "
                    "слова-фильтры или категории, воспользуйтесь командой /menu"
                )
                await bot.send_message(message.chat.id, text)
                return await get_news(user)

    # Инициализируем настройку
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Подписаться на канал", callback_data="start_subscribe"))
    text = (
        "Приветствуем Вас в нашем совершенном боте Infobubble! "
        "Здесь Вы можете добавлять каналы и фильтровать новости по своим интересам, "
        "а также получать наиболее актуальную информацию из интересующих Вас источников в одном месте!\n\n"
        "Для начала давайте подпишемся на один из интересных Вам каналов! "
        "Как будете готовы, нажимайте кнопку «Подписаться на канал»."
    )

    await bot.send_message(message.chat.id, text, reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data == "help", state="*")
async def help(call: types.CallbackQuery, state: FSMContext):
    """
        Handler for inline `help` button. Send help video by current user `state`
    """
    current_state = await state.get_state()

    subscribe_form = subscriptions.SubscribeForm
    filter_words_form = filter_words.FilterWordsForm

    media_path = Path.cwd() / "static"/ "video"
    media_help = types.InputFile(f"{media_path}/menu_remove_filter_word.mp4")

    if current_state in subscribe_form.states_names:
        if current_state == subscribe_form.add_channel.state:
            media_path = media_path / "menu_add_subscribe.mp4"
        elif current_state == subscribe_form.remove_channel.state:
            media_path = media_path / "menu_remove_subscribe.mp4"
    elif current_state in filter_words_form.states_names:
        if current_state == filter_words_form.add_words.state:
            media_path = media_path / "menu_add_filter_word.mp4"
        elif current_state == filter_words_form.remove_words.state:
            media_path = media_path / "menu_remove_filter_word.mp4"
    elif current_state == filters.FiltersForm.filters.state:
        media_path = media_path / "menu_filters.mp4"

    media_help = types.InputFile(media_path)
    help_message = await bot.send_video(
        chat_id=call.message.chat.id,
        video=media_help
    )
    await bot.answer_callback_query(call.id)

    async with state.proxy() as data:
        data["help_message"] = help_message


@dp.callback_query_handler(lambda call: call.data == "start_subscribe")
async def start_subscribe(call: types.CallbackQuery):
    # Set state
    await StartForm.channel.set()

    text = "Чтобы добавить канал, отправьте @упоминание или ссылку на канал, с которого Вы хотите получать новости."

    await bot.delete_message(call.message.chat.id, call.message.message_id)
    await bot.send_message(call.message.chat.id, text)


@dp.message_handler(state=StartForm.channel)
async def process_start_channel(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    channel = await get_channel(message.text)
    if not channel:
        return await bot.send_message(
            chat_id=message.chat.id,
            text="Указанное значение не является @упоминанием или ссылкой на канал. Пожалуйста, попробуйте ввести другое значение.",
        )

    try:
        channel = await bot.get_chat(channel)
    except ChatNotFound:
        return await bot.send_message(
            chat_id=message.chat.id, text="К сожалению, указанный канал не найден. Пожалуйста, попробуйте указать другой канал."
        )

    async with state.proxy() as data:
        data["channel"] = channel

    await StartForm.next()

    markup = types.InlineKeyboardMarkup()
    num_pages = len(news_filters) % 8

    for filter_1, filter_2 in zip_longest(news_filters[0:8:2], news_filters[1:8:2]):
        markup.row(
            types.InlineKeyboardButton(text=filter_1, callback_data=filter_1),
            types.InlineKeyboardButton(text=filter_2, callback_data=filter_2)
        )

    markup.row(
        types.InlineKeyboardButton("Назад", callback_data="previous_filters"),
        types.InlineKeyboardButton(f"1/{num_pages}", callback_data="page_count"),
        types.InlineKeyboardButton("Далее", callback_data="next_filters"),
    )
    markup.add(types.InlineKeyboardButton("Сохранить", callback_data="complete"))
    markup.add(types.InlineKeyboardButton("Помощь", callback_data="help"))

    text = (
        f"Отлично! Вы успешно подписались на канал {channel.mention}. "
        "Теперь Вам нужно определиться с фильтрами, от которых будет зависеть характер получаемых Вами новостей.\n\n"
        "Когда выберете все необходимые категории, нажмите «СОХРАНИТЬ»."
    )

    await bot.send_message(chat_id=user_id, text=text, reply_markup=markup)


@dp.message_handler(commands=["menu"], state="*")
async def menu(message: types.Message, state: FSMContext):
    """Handle call command `menu` and send message with inline menu"""
    text = (
        "Infobubble выполняет две основных функции: дает возможность собрать новостную ленту "
        "из интересующих Вас каналов и ленту с новостями по выбранным Вами фильтрам с источников, отобранных ИИ."
        "Подробнее об этих о остальных функциях Вы можете прочитать ниже:\n\n"

        "❗️ Подписки позволяют Вам подписываться на каналы, из которых Вы хотите получать новости, "
        "и читать их в одном месте, формируя собственную уникальную ленту. "
        "Если же Вы не определились с нужными каналами, доверьтесь нашему ИИ: "
        "бот будет присылать Вам наиболее релевантные новости из более чем 5000 каналов по заданным фильтрам. "
        "Все, что нужно сделать в таком случае, это перейти в раздел «ФИЛЬТРЫ» и выбрать интересующие Вас категории.\n\n"

        "❗️ Фильтры позволяют настроить интересующие пользователя категории, на основе которых ему будут присылаться новости. "
        "При этом новости по какой-либо другой тематике видны не будут.\n\n"

        "Также фильтры не действуют на новости с выбранных вами каналов.\n\n"

        "❗️ Стоп-слова позволяют исключать из новостей сообщения, содержащие в своём тексте указанное Вами слово или слова: "
        "Вы добавляете стоп-слово и больше не получаете новостные статьи, в которых оно присутствует.\n\n"

        "❗️ Старт. Этот раздел позволяет получить очередное новостное сообщение по заданным Вами параметрам."
    )

    if await state.get_state():
        await state.finish()

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("Подписки", callback_data="subscribes"),
        types.InlineKeyboardButton("Фильтры", callback_data="filters")
    )
    markup.row(
        types.InlineKeyboardButton("Стоп-слова", callback_data="filterwords"),
        types.InlineKeyboardButton("Старт", callback_data="news")
    )

    await bot.send_message(message.chat.id, text, reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data == "complete", state="*")
async def complete_click_inline(call: types.CallbackQuery, state: FSMContext):
    """
    Handle click to `complete` button of first initialization

    Then save user and him filters to DB
    """
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
                    "информационные ресурсы или фильтры, воспользуйтесь командой /menu"
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


@dp.callback_query_handler(lambda call: call.data.startswith("like"))
async def on_like(call: types.CallbackQuery):
    """Handle query of click to like button"""
    user_id = call.from_user.id

    if call.message.reply_to_message:
        message_id = call.message.reply_to_message.message_id
    else:
        message_id = call.message.message_id
    channel_id = call.data.split("_")[1]
    data = {
        "user_id": user_id,
        "message_id": message_id,
        "channel_id": channel_id,
        "rate": True,
    }

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Далее", callback_data="next")
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(url=f"{URL}/api/rate/", json=data) as response:
            if response.status != 201:
                return logger.error(await response.text())
        async with session.get(url=f"{URL}/api/users/{user_id}/") as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())

    await call.message.edit_reply_markup(markup)
    await bot.answer_callback_query(call.id)
    await get_news(user)


@dp.callback_query_handler(lambda call: call.data.startswith("nolike"))
async def on_nolike(call: types.CallbackQuery):
    """Handle query of click to dislike button"""
    user_id = call.from_user.id

    if call.message.reply_to_message:
        message_id = call.message.reply_to_message.message_id
    else:
        message_id = call.message.message_id
    channel_id = call.data.split("_")[1]
    data = {
        "user_id": user_id,
        "message_id": message_id,
        "channel_id": channel_id,
        "rate": False,
    }

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("Далее", callback_data="next")
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(url=f"{URL}/api/rate/", json=data) as response:
            if response.status != 201:
                return logger.error(await response.text())
        async with session.get(url=f"{URL}/api/users/{user_id}/") as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())

    await call.message.edit_reply_markup(markup)
    await bot.answer_callback_query(call.id)
    await get_news(user)


@dp.callback_query_handler(lambda call: call.data == "next")
async def next_news(call: types.CallbackQuery):
    """Handle query for sending next new"""
    user_id = call.from_user.id
    async with aiohttp.ClientSession() as session:
        async with session.get(url=f"{URL}/api/users/{user_id}/") as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())
    await bot.answer_callback_query(call.id)
    await get_news(user)


@dp.callback_query_handler(lambda call: call.data == "news")
@dp.message_handler(commands=["news"])
async def send_new_handler(call: types.CallbackQuery):
    """Handle user command or message with `news` text for getting news"""
    user_id = call.from_user.id
    if isinstance(call, types.CallbackQuery):
        await bot.answer_callback_query(call.id)

    async with aiohttp.ClientSession() as session:
        async with session.get(url=f"{URL}/api/users/{user_id}/") as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())
    await get_news(user)


if __name__ == "__main__":
    subscriptions.setup(dp)
    filter_words.setup(dp)
    filters.setup(dp)
    loop = asyncio.get_event_loop()
    loop.create_task(subscribe_news())
    loop.create_task(day_news())
    executor.start_polling(dp, loop=loop)
