import configparser
import requests
import pprint

from telebot import TeleBot
from telebot import types
import json
from random import randint
from os import path

config = configparser.ConfigParser()
config.read(path.join(path.dirname(path.abspath(__file__)), 'config.ini'))
URL = config['Django']['url']
API_TOKEN = config['Telegram']['token']

bot = TeleBot(API_TOKEN)

news_filters = ['ИТ', 'Дизайн', 'Бизнес', 'Игры', 'Новости', "Блоги", "Продажи", "Музыка","Позновательное", "Цитаты"]
user_filters = {}
markup_button = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
itembtn1 = types.KeyboardButton('Изменить фильтры')
itembtn2 = types.KeyboardButton('Получить новости')
markup_button.add(itembtn1,itembtn2 )


@bot.message_handler(commands=['start'])
def start(message):
    '''Инициируем добавление нового пользователя'''
    user_id = message.from_user.id

    # Проверяем проходил ли пользователь настройку
    data = {
        'token': API_TOKEN,
        'user_id': user_id
    }
    print("SDDSSD")
    responce = requests.post(url=f'{URL}/api/users/', json=data)
    print(responce)
    if responce.status_code == 200:
        text = ('Вы уже проходили настройку!\nДля изменения категорий воспользуйтесь командой: /changefilters')
        bot.send_message(message.chat.id, text)
        send_news(message)

    # Инициализируем настройку
    markup = types.InlineKeyboardMarkup(row_width=3)
    for _filter in news_filters:
        markup.add(types.InlineKeyboardButton(_filter, callback_data=_filter))
    markup.add(types.InlineKeyboardButton('Сохранить', callback_data='complete'))
    text = (
        'Привет! Слишком много каналов в Telegram? Сложно это всё читать, понимаю. '
        'Я тут, кстати как раз для того чтобы помочь тебе в этом. Давай определимся с твоими вкусами. '
        'Выбирай, что тебе нравится (как определишься, нажми «Сохранить»):'
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)


@bot.message_handler(commands=['help'])
def help(message):
    text = (
        'Ты можешь написать мне: /changefilters — чтобы вернуться к информационным фильтрам и поправить их. '
        'Как столько ты ставишь ❤ или 👎🏻 последнему посту, я отправляю тебе новый.'
    )
    bot.send_message(message.chat.id, text)


@bot.callback_query_handler(func=lambda call: call.data in news_filters)
def filter_click_inline(call):
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
        print(row)
        print(i)
        l = 0
        try:
            filter_button = next(btn for btn in row if btn.callback_data == choosen_filter)
        except StopIteration:
            continue
        else:
            for btn in row:
                
                if btn.callback_data == choosen_filter:                   
                    if event_type == 'append':
                        filter_button.text = f'{choosen_filter} ✅'
                    elif event_type == 'remove':
                        filter_button.text = f'{choosen_filter} ❎'
                    row[l]=filter_button
                l+=1
            print(markup.keyboard[i])
            markup.keyboard[i] = row
            break


    bot.edit_message_reply_markup(
        chat_id=chat_id,
        message_id=message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == 'complete')
def complete_click_inline(call):
    '''Сохраняем пользователя и его фильтры в базу данных'''
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.id

    if not user_filters.get(user_id):
        bot.answer_callback_query(call.id, 'Вам необходима выбрать хотя бы одну категорию!')
        return

    data = {
        'token': API_TOKEN,
        'user_id': user_id,
        'filters': user_filters[user_id]
    }
    responce = requests.post(url=f'{URL}/api/users/', json=data)

    bot.answer_callback_query(call.id, 'Настройка завершена!')
    bot.delete_message(chat_id, message_id)
    text = '''Отлично, информационные фильтры заданы! Так я буду лучше понимать тебя. Теперь, я буду присылать тебе посты, а ты их оценивать, я присылать, а ты оценивать, я присылать... и так далее. Если возникнут проблемы, ты всегда можешь заручиться моей поддержкой, написав /help'''
    bot.send_message(call.from_user.id, text)
    send_news(call)


def send_news(message):
    user_id = message.from_user.id

    # Получаем фильтры пользователя
    data = {
        'token': API_TOKEN,
        'user_id': user_id
    }
    responce = requests.post(url=f'{URL}/api/users/', json=data)
    tags = responce.json()['filters']
    print(tags)
    # Получаем id каналов
    data = {
        'token': API_TOKEN,
        'tags': tags
    }
    responce = requests.post(url=f'{URL}/api/channels/', json=data)
    print(responce.text)
    if responce.status_code == 204:
        return print(f'Каналы с следующими фильтрами не найдены: {", ".join(tags)}')
    channels = responce.json()['channels_ids']
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton('❤️', callback_data='like'))
    markup.add(types.InlineKeyboardButton('👎', callback_data='nolike'))
    markup.add(types.InlineKeyboardButton('Далее', callback_data='next'))
    try:
        with open(path.join(path.dirname(path.abspath(__file__)),channels[randint(0,len(channels))]+str(randint(0,4))+'.json'), 'r', encoding='utf-8') as fh: #открываем файл на чтение
            data = json.load(fh)
            print(data)
            if data["filename"] == "None":
                bot.send_message(user_id, data['text'], reply_markup=markup)
            else:
                print( data['filename'])
                print(path.join(path.dirname(path.abspath(__file__)), data['filename']))
                if path.join(path.dirname(path.abspath(__file__)), data['filename'])[-4:] == ".mp4":
                    bot.send_video(user_id,open(path.join(path.dirname(path.abspath(__file__)), data['filename']), 'rb'), caption=data['text'], reply_markup=markup)           
                else:
                    bot.send_photo(user_id,open(path.join(path.dirname(path.abspath(__file__)), data['filename']), 'rb'), caption=data['text'],reply_markup=markup)
    except:
        send_news(message)

@bot.callback_query_handler(func=lambda call: call.data == 'like')
def ozenka(call):
    user_id = call.from_user.id
    message_id = call.message.id
    channel_id = "nexta_live"
    data = {
        'token': API_TOKEN,
        'user_id': user_id,
        'message_id':message_id,
        'channel_id': channel_id,
        'rate': True
    }
    responce = requests.post(url=f'{URL}/api/rate/', json=data)
    send_news(call)

@bot.callback_query_handler(func=lambda call: call.data == 'nolike')
def ozenka_nolike(call):
    user_id = call.from_user.id
    message_id = call.message.id
    channel_id = "nexta_live"
    data = {
        'token': API_TOKEN,
        'user_id': user_id,
        'message_id':message_id,
        'channel_id': channel_id,
        'rate': False
    }
    responce = requests.post(url=f'{URL}/api/rate/', json=data)
    send_news(call)

@bot.callback_query_handler(func=lambda call: call.data == 'next')
def next_news(call):
    send_news(call)

@bot.message_handler(commands=['news'])
def send_new(message):
    send_news(message)


@bot.message_handler(commands=['changefilters'])
def change_filters(message):
    '''Редактируем фильтры пользователя'''
    user_id = message.from_user.id
    chat_id = message.chat.id

    # Получаем фильтры пользователя
    data = {
        'token': API_TOKEN,
        'user_id': user_id
    }
    responce = requests.post(url=f'{URL}/api/users/', json=data)
    if responce.status_code == 204:
        bot.send_message(chat_id=chat_id, text='Вы ещё не проходили настройку! Воспользуйтесь командой /start')
        return

    existing_filters = responce.json()['filters']
    user_filters[user_id] = existing_filters

    markup = types.InlineKeyboardMarkup()
    i = 0
    btn = []
    for _filter in news_filters:
        if _filter in existing_filters:
            i+=1
            btn.append(types.InlineKeyboardButton(text=f'{_filter} ✅', callback_data=_filter))
        else:
            i+=1
            btn.append(types.InlineKeyboardButton(text=_filter, callback_data=_filter))
        if i == 2:
            i = 0
            markup.row(btn[0], btn[1])
            btn =[]
    markup.add(types.InlineKeyboardButton(text='Сохранить', callback_data='changefilters'))

    bot.send_message(chat_id, 'Измените категории', reply_markup=markup)

def day_send_news(user_id):
    data = {
        'token': API_TOKEN,
        'user_id': user_id
    }
    responce = requests.post(url=f'{URL}/api/users/', json=data)
    tags = responce.json()['filters']
    print(tags)
    # Получаем id каналов
    data = {
        'token': API_TOKEN,
        'tags': tags
    }
    responce = requests.post(url=f'{URL}/api/channels/', json=data)
    print(responce.text)
    if responce.status_code == 204:
        return print(f'Каналы с следующими фильтрами не найдены: {", ".join(tags)}')
    channels = responce.json()['channels_ids']
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton('❤️', callback_data='like'))
    markup.add(types.InlineKeyboardButton('👎', callback_data='nolike'))
    markup.add(types.InlineKeyboardButton('Далее', callback_data='next'))
    try:
        with open(path.join(path.dirname(path.abspath(__file__)),channels[randint(0,len(channels))]+str(randint(0,4))+'.json'), 'r', encoding='utf-8') as fh: #открываем файл на чтение
            data = json.load(fh)
            print(data)
            if data["filename"] == "None":
                bot.send_message(user_id, data['text'], reply_markup=markup)
            else:
                print( data['filename'])
                print(path.join(path.dirname(path.abspath(__file__)), data['filename']))
                if path.join(path.dirname(path.abspath(__file__)), data['filename'])[-4:] == ".mp4":
                    bot.send_video(user_id,open(path.join(path.dirname(path.abspath(__file__)), data['filename']), 'rb'), caption=data['text'], reply_markup=markup)           
                else:
                    bot.send_photo(user_id,open(path.join(path.dirname(path.abspath(__file__)), data['filename']), 'rb'), caption=data['text'],reply_markup=markup)
    except:
        day_send_news(user_id)
    

def day_news():
    response = requests.get(url=f'{URL}/api/users/')
    users = response.json()
    for user in users:
        day_send_news(user['user_id'])


@bot.callback_query_handler(func=lambda call: call.data == 'changefilters')
def change_filters_click_inline(call):
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.id

    if not user_filters.get(user_id):
        bot.answer_callback_query(call.id, 'Вам необходима выбрать хотя бы одну категорию!')
        return

    data = {
        'token': API_TOKEN,
        'user_id': user_id,
        'filters': user_filters[user_id]
    }
    responce = requests.post(url=f'{URL}/api/users/', json=data)

    bot.answer_callback_query(call.id, text='Категории успешно изменены!')
    bot.delete_message(chat_id, message_id)
    
    send_news(call)

@bot.message_handler(content_types=["text"])
def change_filters_click_inline(message):
    if message.text == "Изменить фильтры":
        change_filters(message)
    if message.text == "Получить новости":
        send_new(message)
    user_id = message.from_user.id
    if message.text != "Получить новости" and message.text != "Изменить фильтры":
        bot.send_message(user_id,"Сейчас я отправляю новости, а возможно завтра захватываю мир :)",reply_markup=markup_button)

day_news()
bot.polling()
