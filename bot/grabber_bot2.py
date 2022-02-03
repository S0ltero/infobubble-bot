from pyrogram.types.messages_and_media import message
from pyrogram import Client
from telethon import TelegramClient, events
import asyncio
import configparser
import requests
import telebot
import json
import os.path
import io
from os import path

from telethon.tl.functions.channels import JoinChannelRequest


config = configparser.ConfigParser()
config.read(path.join(path.dirname(path.abspath(__file__)), 'config.ini'))

api_id   = config['Telegram']['api_id']
api_hash = config['Telegram']['api_hash']
username = config['Telegram']['username']
URL = config['Django']['url']
API_TOKEN = config['Telegram']['token']
my_channel_id = "pskovhacktest_1"
data = {
        'token': API_TOKEN
    }
try:
    responce = requests.get(url=f'{URL}/api/channels/', json=data)
    print("SDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    print(responce.json())
    channels = responce.json()['channels_ids']
except:
    responce = requests.get(url=f'{URL}/api/channels/', json=data)
    print("SDAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    print(responce.json())
    channels = responce.json()['channels_ids']
#channels.append("pskovhacktest_1")
print(channels)
# channels = ["hghtest6","pskovhacktest2", "testphtest", "pskovhacktest_1"]
 
# client = TelegramClient('myGrab', api_id, api_hash)

bot = telebot.TeleBot("1920577876:AAGM__h6FFON7huV4IPVFBjKdv4K7_vSti8", parse_mode=None)
print("GRAB - Started")




def form_data(filename,message_id, message_text, channel):
    if message_text == None:
        message_text = ""
    data = {
        'message_id': message_id,
        'filename': filename,
        'text': message_text + " \n  Оригинал можно посмотреть на канале @" + channel
    }
    print(data)
    channel = str(path.join(path.dirname(path.abspath(__file__)),"downloads",str(channel)))
    if (os.path.exists(channel+"0"+".json")):
        if (os.path.exists(channel+"1"+".json")):
            if(os.path.exists(channel+"2"+".json")):
                if(os.path.exists(channel+"3"+".json")):
                    if(os.path.exists(channel+"4"+".json")):
                        if(os.path.exists(channel+"5"+".json")):
                            with open(channel+"0"+".json", "r") as read_file:
                                data1 = json.load(read_file)
                                if data1["filename"]!= "None":
                                    try:
                                        os.remove(data1["filename"])
                                    except:
                                        print("error")
                            os.remove(channel+"0"+".json")
                            with open(channel+"1"+".json", "r") as read_file:
                                data1 = json.load(read_file)
                                if data1["filename"]!= "None":
                                    try:
                                        os.remove(data1["filename"])
                                    except:
                                        print("error")
                            os.remove(channel+"1"+".json")
                            with open(channel+"2"+".json", "r") as read_file:
                                data1 = json.load(read_file)
                                if data1["filename"] != "None":
                                    try:
                                        os.remove(data1["filename"])
                                    except:
                                        print("error")
                            os.remove(channel+"2"+".json")
                            with open(channel+"3"+".json", "r") as read_file:
                                data1 = json.load(read_file)
                                if data1["filename"]!= "None":
                                    try:
                                        os.remove(data1["filename"])
                                    except:
                                        print("error")
                            os.remove(channel+"3"+".json")
                            with open(channel+"4"+".json", "r") as read_file:
                                data1 = json.load(read_file)
                                if data1["filename"]!= "None":
                                    try:
                                        os.remove(data1["filename"])
                                    except:
                                        print("error")
                            os.remove(channel+"4"+".json")
                            with open(channel+"5"+".json", "r") as read_file:
                                data1 = json.load(read_file)
                                if data1["filename"]!= "None":
                                    try:
                                        os.remove(data1["filename"])
                                    except:
                                        print("error")
                            os.remove(channel+"5"+".json")
                            with open(channel+"0"+".json", "w") as write_file:
                                json.dump(data, write_file)
                        else:
                            with open(channel+"5"+".json", "w") as write_file:
                                json.dump(data, write_file)
                    else:
                        with open(channel+"4"+".json", "w") as write_file:
                            json.dump(data, write_file)
                else:
                    with open(channel+"3"+".json", "w") as write_file:
                        json.dump(data, write_file)
            else:
                with open(channel+"2"+".json", "w") as write_file:
                    json.dump(data, write_file)
        else:
            with open(channel+"1"+".json", "w") as write_file:
                json.dump(data, write_file)
    else:
        with open(channel+"0"+".json", "w") as write_file:
            json.dump(data, write_file)
def progress(current, total):
    print(f"{current * 100 / total:.1f}%")

def bot_news():
    bottest = Client("my_account", api_id, api_hash)
    with bottest:
        for channel in channels:
                print(channel)
                i = 0
                for message in bottest.iter_history(channel, limit=5): 
                    print(message)
                    if message.media:
                       
                        try:
                            chat_from = message.chat if message.chat else (message.get_chat())
                            puth = message.download(progress=progress, block=True)
                            print(puth)
                            form_data(puth[26:],message.message_id, message.caption, chat_from.username)
                        except:
                            chat_from = message.chat if message.chat else (message.get_chat())
                            print(chat_from.username)
                            form_data(None,message.message_id, message.text, chat_from.username)

                        print(message.media)
                                           
                    else:
                        chat_from = message.chat if message.chat else (message.get_chat())
                        print(chat_from.username)
                        form_data(None, message.message_id,message.text, chat_from.username)
                    i+=1
                    if i>=4:
                        break

# @client.on(events.NewMessage(chats=channels))
async def my_event_handler(event):
    
    message = event.message
    print(message)
    if message.media:
	
        chat_from = event.chat if event.chat else (await event.get_chat())
        
        try:   
           filiname = message.file.name
           puth = await message.download_media(file=path.join(path.dirname(path.abspath(__file__)), 'downloads'))
           await form_data(puth, message.text, chat_from.username)
        except:
           await form_data(None,message.text, chat_from.username)
    else:
        chat_from = event.chat if event.chat else (await event.get_chat())
        print(chat_from.username)
        await form_data(None,message.text, chat_from.username)
    
    # await my_channels()

    # await client(JoinChannelRequest(channels[1]))
    # if event.message:
    #     await client.send_message(my_channel_id, event.message)
async def my_channels():
    for i in channels:
        print(i)
        await client(JoinChannelRequest(i))
#client = TelegramClient('myGrab', api_id, api_hash)
#client.start()
#asyncio.run(my_channels())
bot_news()

# client.start()

# client.run_until_disconnected()
