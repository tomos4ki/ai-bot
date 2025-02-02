import discord
from discord.ext import commands
from discord.utils import get
import requests
from assets.dms_history import dm_history
from assets.log import log_message


import google.generativeai as genai




# db = MessageDatabase("messages.db")



def genetate_ai_message(message, user_id, user_name, user_username):
    genai.configure(api_key="AIzaSyD8Pq-pGies5M5M3wmQy55Jsufp_tPDTW4")
    model = genai.GenerativeModel("gemini-1.5-flash")
# previous model = gemini-2.0-flash-exp

    responce = model.generate_content(message)
    #db.add_message(user_id, message, responce)
    if 'result' in responce and 'response' in responce['result']:
        responce = responce['result']['response']
    else:
        responce =" Error: unable to retreve responce from the ai"
    print(f"Receved DM from {user_name}:({user_username})with ID ({user_id})")
    print(f"message is : {message}")
    print(f"output is {responce}")
    return responce

async def handle_dm(message):
    user_id = message.author.id
    user_name = message.author.name
    user_username = message.author.display_name
    if message.author == message.channel.me:
        return
    async with message.channel.typing():
        responce = genetate_ai_message(message.content, user_id, user_name, user_username)
        await message.channel.send(responce)