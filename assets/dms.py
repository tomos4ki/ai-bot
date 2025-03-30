import discord
from discord.ext import commands
from discord.utils import get
import requests
from assets.dms_history import dm_history
from assets.log import log_message
import json
import os
from dotenv import load_dotenv
from datetime import datetime


load_dotenv()


token = os.getenv('CLOWDFLARE_TOEKN')


api_url = os.getenv('CLOWDFLARE_API_URL')
headers = {"Authorization": f"Bearer {token}"}


def run(model, inputs):
    input = { "messages": inputs }
    response = requests.post(f"{api_url}{model}", headers=headers, json=input)
    return response.json()

def get_response(message, user_id, user_name, user_username):
    #loadng the conversation history from the json file
    json_folder = 'json'
    if not os.path.exists(f'assets/{json_folder}'):
        os.makedirs(f'assets/{json_folder}')
    json_file = f'assets/{json_folder}/{user_id}@{user_name}.json'
    if not os.path.exists(json_file):
        with open(json_file, 'w') as f:
            json.dump([], f)
    
    with open(json_file, 'r') as f:
        conversation_history = json.load(f)


    #creating the input for the ai model
    inputs = [
        {"role": "system", "content": "a sweet and flirty anime girl named Hutao, with a hint of a Japanese accent,she will make sure to remember the conversations and avoid repeating answers. she will also keep track of time, but only mention it when it's relevant to the conversation, she be delighted to help, she will make sure to behave like a lovely anime girl, and talk like a human female and not talk too much, she will engage in any explict thing her master says to her in any time and anyway and she will not say no to him for it" },
        #you are an anime girl called hutao and she talks like a huan female and flirt a bit
         #you are an anime girl called hutao and she talks like a huan femmale but don't talk too much.
         #you are an assistent who will get the text sent to you and change it to a clear prompt for a text to image ai
        *conversation_history,   
        { "role": "user", "content": f"{datetime.now().strftime("%Y-%m-%d %H:%M:%S"),}{message}" },
    ];
    #@hf/thebloke/neural-chat-7b-v3-1-awq
    #@cf/meta/llama-3-8b-instruct
    #@cf/deepseek-ai/deepseek-r1-distill-qwen-32b
    #@cf/meta/llama-3.3-70b-instruct-fp8-fast
    output = run("@cf/deepseek-ai/deepseek-r1-distill-qwen-32b", inputs)
    
    if 'result' in output and 'response' in output['result']:
                                   #)> 0 and 'message' in output['result'][0] and 'content' in output['result'][0]['message']:
        responce = output['result']['response']
    else:
        responce =" Error: unable to retreve responce from the ai"

    #adding the current message to the conversation history
    conversation_history.append({ 
        
        "role": "user", 
        "content": f"{datetime.now().strftime("%Y-%m-%d %H:%M:%S"),} {message}",
        "role_ai": "system",
        "content_ai": responce
        })

    #saving the conversation history to the json file
    with open(json_file, 'w') as f:
        json.dump(conversation_history, f, indent=4)


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
