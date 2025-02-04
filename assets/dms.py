import discord
from discord.ext import commands
from discord.utils import get
import requests
from assets.dms_history import dm_history
from assets.log import log_message
import os
from dotenv import load_dotenv


load_dotenv()


token = os.getenv('CLOWDFLARE_TOEKN')


api_url = os.getenv('CLOWDFLARE_API_URL')
headers = {"Authorization": f"Bearer {token}"}


def run(model, inputs):
    input = { "messages": inputs }
    response = requests.post(f"{api_url}{model}", headers=headers, json=input)
    return response.json()

def get_response(message, user_id, user_name, user_username):
    inputs = [
        { "role": "system", "content": 
         "#you are an anime girl called hutao and she talks like a huan femmale but don't talk too much." },
         #you are an anime girl called hutao and she talks like a huan femmale but don't talk too much.
         #you are an assistent who will get the text sent to you and change it to a clear prompt for a text to image ai
        { "role": "user", "content": message },
    ];
    #output = @hf/thebloke/neural-chat-7b-v3-1-awq
    #output = @cf/meta/llama-3-8b-instruct
    output = run("@hf/thebloke/neural-chat-7b-v3-1-awq", inputs)
    
    if 'result' in output and 'response' in output['result']:
                                   #)> 0 and 'message' in output['result'][0] and 'content' in output['result'][0]['message']:
        responce = output['result']['response']
    else:
        responce =" Error: unable to retreve responce from the ai"
    print(f"Receved DM from {user_name}({user_username})with ID ({user_id})")
    print(f"message is : {message}")
    print(f"output is {output}")

    #for now it will only do the history thing
    #history_saved = dm_history(user_id, message,responce)#future adding the ai model for multiple ai models, exemple ( user_id, message, ai_id, responce)
    # if history_saved != 1:
    #     log_message("message coulden't be saved in file, error in database", 2)# 1 bot, 2 error, 3 notification, 4 reply, else unknown
    # else:
    #     print("history saved i guess!")
    return responce



async def handle_dm(message):
    user_id = message.author.id
    user_name = message.author.name
    user_username = message.author.display_name
    
    #cooldown = 5
    if message.author == message.channel.me:
        return
    # async for last_message in message.channel.history(limit=1):
    #     print(last_message)
    #     print(message.channel.history)
    #     if last_message.author == message.author and (message.created_at - last_message.created_at).total_seconds() < cooldown:
    #         return

    async with message.channel.typing():
        response = get_response(message.content, user_id, user_name, user_username)
        await message.channel.send(response)
