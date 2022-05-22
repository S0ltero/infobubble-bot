import asyncio
import re
import os
from pathlib import Path
from datetime import datetime
from itertools import zip_longest

import aiohttp

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.types import ParseMode
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils.exceptions import ChatNotFound, BadRequest, BotBlocked, UserDeactivated, CantParseEntities

from loguru import logger

from handlers import filter_words
from handlers import filters
from handlers import subscriptions

URL = os.getenv("DJANGO_HOST")
API_TOKEN = os.getenv("TELEGRAM_TOKEN")

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
user_subscribe_news = {}
user_news = {}


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


class FiltersForm(StatesGroup):
    filters = State()


@dp.message_handler(commands=["start"])
async def start(message):
    """Инициируем добавление нового пользователя"""
    user_id = message.from_user.id

    # Проверяем проходил ли пользователь настройку
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{URL}/api/users/{user_id}/") as response:
            if response.status == 200:
                user = await response.json()
                text = (
                    "Вы уже проходили настройку! Если Вам нужно изменить подписки, "
                    "слова-фильтры или категории, воспользуйтесь командой /help"
                )
                await bot.send_message(message.chat.id, text)
                return await get_news(user)

    # Инициализируем настройку
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Подписаться на канал", callback_data="start_subscribe"))
    text = (
        "Приветствуем Вас в нашем совершенном боте Infobubble! "
        "Здесь Вы можете добавлять каналы и фильтровать новости по своим интересам, а также "
        "получать наиболее актуальную информацию с интересующих Вас источников в одном месте. "
        "Давайте для начала подпишимся на один из интересных Вам каналов! "
        "Как будете готовы, нажимайте кнопку «Подписаться на канал»"
    )

    await bot.send_message(message.chat.id, text, reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data == "start_subscribe")
async def start_subscribe(call):
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
        await bot.send_message(
            chat_id=message.chat.id,
            text="Указанное значение не является @упоминанием или ссылкой на канал. Пожалуйста, попробуйте ввести другое значение.",
        )

    try:
        channel = await bot.get_chat(channel)
    except ChatNotFound:
        await bot.send_message(
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

    text = (
        f"Отлично! Ты успешно подписался на новости канала {channel.mention}! "
        "Теперь давай соберем список фильтров по интересующим тебя новостными темам."
        "Как определишься, нажми кнопку «Сохранить»"
    )

    await bot.send_message(chat_id=user_id, text=text, reply_markup=markup)


@dp.message_handler(commands=["help"])
async def help(message):
    text = (
        "- Подписки позволяют Вам подписываться на каналы, с которых Вы хотите получать новости, "
        "или отписываться от них. С указанных каналов Вы будете получать статьи по мере их появления в этих источниках. "
        "Все, что Вам нужно, это указать предпочитаемые каналы в разделе «ПОДПИСКИ» ниже.\n\n"
        "Если же Вы не определились с нужными каналами, оставьте это нам: "
        "бот будет присылать Вам новости с выбранных нами проверенных и достоверных источников. "
        "Все, что нужно сделать в таком случае, это перейти в раздел «ФИЛЬТРЫ» и выбрать близкие Вам категории.\n\n"

        "- Фильтры позволяют настроить интересующие пользователя категории новостей, на основе которых ему будут присылаться новости. "
        "В Вашем распоряжении будет более 10 фильтров, которые Вы сможете выбрать. " 
        "Например, Вы выбираете категорию «Бизнес» и получаете только новости о бизнесе (с указанных источников).\n\n"
        "Также Вы можете выбрать сразу несколько категорий: например, «Бизнес» и «Музыка». "
        "В данном случае Вам будет приходить информация и по «бизнесу», и по «музыке» в одну ленту по каждому из фильтров. "
        "При этом новости по какой-либо другой тематике видны не будут. Вы можете изменить свои фильтры в любой момент: "
        "просто пропишите команду /changefilters и выберите необходимые категории.\n\n"

        "- Слова-фильтры позволяют исключать из новостей сообщения, содержащие в своём тексте "
        "указанное Вами слово или слова: Вы добавляется слово-фильтр и больше не получаете новостные статьи, "
        "в которых присутствует это слово. Например, Вы не хотите читать новости про политику. "
        "В таком случае Вам нужно зайти в этот раздел и прописать в окне ниже слово «политика». "
        "После этого Вы перестанете получать статьи, содержащие в своем тексте слово «политика». "
        "Если же Вы не хотите видеть новости, содержащие сразу несколько слов, укажите все эти слова. "
        "Тогда Вам не будут приходить новости, в которых есть хотя бы одно из указанных слов.\n\n"
        "Добавить или убрать какое-то из слов Вы можете в любой момент: просто введите команду /help, "
        "нажмите на раздел «Слова-фильтры» и «Добавить слова-фильтры» или «Удалить слова-фильтры». "

        "- Новости. Этот раздел позволяет получить очередное новостное сообщение по заданным Вами параметрам. "
        "В этом разделе учитываются Ваши каналы из раздела «Подписки», а также выбор в разделе «Фильтры» и "
        "указанные слова в разделе «Слова-фильтры».\n\n"
        "Вы можете оценивать качество новостей: ставьте ❤️, если полученная информация Вам подходит. "
        "В таком случае, источник будет считаться проверенным, и Вы продолжите получать с него новости.\n\n"
        "Вы можете поставить 👎🏻, если сведения не соответствуют Вашим ожиданиям. "
        "Тогда в будущем Вы не будете получать новости с этого источника.\n\n"
        "Если же Вы не хотите оценивать новостную статью, просто нажимаете «ДАЛЕЕ» и получаете следующую."
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

    await bot.send_message(message.chat.id, text, reply_markup=markup)


@dp.callback_query_handler(lambda call: call.data in news_filters, state="*")
async def filter_click_inline(call, state: FSMContext):
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


@dp.callback_query_handler(lambda call: call.data == "complete", state="*")
async def complete_click_inline(call, state: FSMContext):
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


@dp.callback_query_handler(lambda call: call.data.startswith("like"))
async def on_like(call):
    user_id = call.from_user.id
    message_id = call.message.message_id
    channel_id = call.data.split("_")[1]
    data = {
        "user_id": user_id,
        "message_id": message_id,
        "channel_id": channel_id,
        "rate": True,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url=f"{URL}/api/rate/", json=data) as response:
            if response.status != 201:
                return logger.error(await response.text())
        async with session.get(url=f"{URL}/api/users/{user_id}/") as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())

    await bot.answer_callback_query(call.id)
    await get_news(user)


@dp.callback_query_handler(lambda call: call.data.startswith("nolike"))
async def on_nolike(call):
    user_id = call.from_user.id
    message_id = call.message.message_id
    channel_id = call.data.split("_")[1]
    data = {
        "user_id": user_id,
        "message_id": message_id,
        "channel_id": channel_id,
        "rate": False,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url=f"{URL}/api/rate/", json=data) as response:
            if response.status != 201:
                return logger.error(await response.text())
        async with session.get(url=f"{URL}/api/users/{user_id}/") as response:
            if response.status == 200:
                user = await response.json()
            else:
                return logger.error(await response.text())

    await bot.answer_callback_query(call.id)
    await get_news(user)


@dp.callback_query_handler(lambda call: call.data == "next")
async def next_news(call):
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
async def send_new_handler(call):
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
            )
        elif message["file_type"] == "video":
            await bot.send_video(
                user_id,
                file_path.open("rb"),
                caption=message["text"],
                reply_markup=markup,
            )
        elif message["file_type"] == "photo":
            await bot.send_photo(
                user_id,
                file_path.open("rb"),
                caption=message["text"],
                reply_markup=markup,
            )
    except (FileNotFoundError, BotBlocked, UserDeactivated, CantParseEntities) as e:
        async with aiohttp.ClientSession() as session:
            if isinstance(e, (FileNotFoundError, CantParseEntities)):
                async with session.delete(url=f"{URL}/api/messages/{message['id']}") as response:
                    pass
            if isinstance(e, UserDeactivated):
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


if __name__ == "__main__":
    subscriptions.setup(dp)
    filter_words.setup(dp)
    filters.setup(dp)
    loop = asyncio.get_event_loop()
    loop.create_task(subscribe_news())
    loop.create_task(day_news())
    executor.start_polling(dp, loop=loop)
