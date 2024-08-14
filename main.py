import discord
import asyncio
from discord.ext import commands
import os
from dotenv import load_dotenv


from assets.commands import CommandTree





load_dotenv()

activity = discord.Activity(type=discord.ActivityType.listening, name="Hutao AI")
bot = commands.Bot(command_prefix='!', activity=activity, intents=discord.Intents.all(), status=discord.Status.dnd, appliction_id=1223314662863671326)



command_tree = CommandTree(bot)
command_tree.add_commands()
asyncio.run(command_tree.sync_commands())

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')

if __name__ == '__main__':
    token = os.getenv('DISCORD_HUTAO_AI_TOKEN')
    try:
        bot.run(token)
    except Exception as e:
        print(f"ERROR: {e}")