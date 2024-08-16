import discord
from discord.ext import commands
from discord.utils import get
import requests


API_BASE_URL = "https://api.cloudflare.com/client/v4/accounts/db5d0abbbab31174a76149945ff13959/ai/run/"
headers = {"Authorization": "Bearer blAvZjZolf3Cq7Vs8sSVOiRV6Xz4WlucT-cSBpMD"}


def run(model, inputs):
    input = { "messages": inputs }
    response = requests.post(f"{API_BASE_URL}{model}", headers=headers, json=input)
    return response.json()

def get_response(message):
    inputs = [
        { "role": "system", "content": 
         "you are an anime girl called hutao and she talks like a huan femmale but don't talk too much." },
        { "role": "user", "content": message },
    ];
    #output = @hf/thebloke/neural-chat-7b-v3-1-awq
    #output = @cf/meta/llama-3-8b-instruct
    output = run("@hf/thebloke/neural-chat-7b-v3-1-awq", inputs)
    print(output)
    if 'result' in output and 'response' in output['result']:
                                   #)> 0 and 'message' in output['result'][0] and 'content' in output['result'][0]['message']:
        responce = output['result']['response']
    else:
        responce =" Error: unable to retreve responce from the ai"
    
    print(f"resoponce is {responce}")
    return responce













async def handle_dm(message):
    cooldown = 5
    if message.author == message.channel.me:
        return
    # async for last_message in message.channel.history(limit=1):
    #     print(last_message)
    #     print(message.channel.history)
    #     if last_message.author == message.author and (message.created_at - last_message.created_at).total_seconds() < cooldown:
    #         return

    response = get_response(message.content)

    await message.channel.send(response)