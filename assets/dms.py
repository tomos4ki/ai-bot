import discord
from discord.ext import commands
from discord.utils import get
import requests
#from dms_history import dm_history


API_BASE_URL = "https://api.cloudflare.com/client/v4/accounts/db5d0abbbab31174a76149945ff13959/ai/run/"
headers = {"Authorization": "Bearer blAvZjZolf3Cq7Vs8sSVOiRV6Xz4WlucT-cSBpMD"}


def run(model, inputs):
    input = { "messages": inputs }
    response = requests.post(f"{API_BASE_URL}{model}", headers=headers, json=input)
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
    print(f"Receved DM from {user_name}({user_username})with ID ({user_id})")
    print(f"message is : {message}")
    print(f"output is {output}")
    if 'result' in output and 'response' in output['result']:
                                   #)> 0 and 'message' in output['result'][0] and 'content' in output['result'][0]['message']:
        responce = output['result']['response']
    else:
        responce =" Error: unable to retreve responce from the ai"
    
    
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
