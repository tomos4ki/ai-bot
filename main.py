import discord
import asyncio
from discord.ext import commands
import os
from dotenv import load_dotenv
from assets.log import log_message

#i'm back baby

from assets.commands import CommandTree
from assets.dms import handle_dm

#from assets.log import log

intents = discord.Intents.default()
intents.typing = False
intents.presences = False



load_dotenv()

activity = discord.Activity(type=discord.ActivityType.listening, name="tomo's commands")
client = commands.Bot(
    command_prefix='!', 
    activity=activity, 
    intents= intents, 
    status=discord.Status.dnd, 
    appliction_id=1223314662863671326)







command_tree = CommandTree(client)
command_tree.add_commands()

@client.event
async def on_ready():
    print(f'{client.user.name} has connected to Discord on {log_message("connected",1)}')
    await command_tree.sync_commands()

@client.event
async def on_message(message):
    if message.channel.type == discord.ChannelType.private:
        await handle_dm(message)
    else:
        await client.process_commands(message)






if __name__ == '__main__':
    token = os.getenv('DISCORD_HUTAO_AI_TOKEN')
    try:
        client.run(token)
    except Exception as e:
        print(f"{log_message("ERROR :",2)}{e}")
        #log_message  1 bot, 2 error, 3 notification, 4 reply, else unknown