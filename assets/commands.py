import discord
from discord.ext import commands
import asyncio

class CommandTree:
    def __init__(self, bot):
        self.bot = bot
        self.tree = bot.tree

    def add_commands(self):
        @self.tree.command(name = "test", description = "replies and shows you the ping between you and the bot's server")
        async def ping(interaction: discord.Interaction):
            await interaction.response.defer()
            print(f"interaction to the command test by user")#user cannot be added cuz command tree don't have it, see ticket for info for this

            # Get the ping between the bot and the Discord server
            server_ping = round(self.bot.latency * 1000)

            #get the ping between the bot and the server
            user_ping = round((discord.utils.utcnow() - interaction.created_at).total_seconds() * 1000)

            #sending initial  responce
            await interaction.followup.send("test works")
            # waiting 1 second to make the first responce visible
            await asyncio.sleep(1)
            #sending the ping result
            await interaction.followup.send(f"Bot ping: {server_ping}ms\nUser ping: {user_ping}ms")
            # waiting 3 seconds ffor the next followup
            await asyncio.sleep(1)
            #sending the final message
            await interaction.followup.send("done")

        

        @self.tree.command(name = "winter_ark", description = "opens winter ark app in your dm")
        async def ping(interaction: discord.Interaction):
            await interaction.response.send_message("opening winter ark app in your dm")
        

        @self.tree.command(name= "ttm", description="converts text to image(currently under testing)")
        async def ping(interaction: discord.Interaction):
            await interaction.response.send_message("currently under maintenence")

        @self.tree.command(name= "bot ping", description="ping of the bot to the discord server")
        async def server_ping(interaction: discord.Interaction):
            await interaction.response.send_message(f"Bot ping: {round(self.bot.latency * 1000)}ms")
            await asyncio.sleep(10)
            await interaction.response.send_message("done")
    
   
    async def sync_commands(self):
        await self.tree.sync()