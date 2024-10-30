import discord
from discord.ext import commands

class CommandTree:
    def __init__(self, bot):
        self.bot = bot
        self.tree = bot.tree

    def add_commands(self):
        @self.tree.command(name = "test", description = "replies and shows you the ping between you and the bot's server")
        async def ping(interaction: discord.Interaction):
            await interaction.response.send_message("test works")
            # Get the ping between the bot and the Discord server
            server_ping = round(self.bot.latency * 1000)

            #get the ping between the bot and the server
            user_ping = round((discord.utils.utcnow() - interaction.created_at).total_seconds() * 1000)

            #sending the ping result
            await interaction.response.send_message(f"Bot ping: {server_ping}ms\nUser ping: {user_ping}ms")

        

        @self.tree.command(name = "winter_ark", description = "opens winter ark app in your dm")
        async def ping(interaction: discord.Interaction):
            await interaction.response.send_message("opening winter ark app in your dm")
    
    def add_commands_winter_ark(self):
        @self.tree.command(name = "winter_ark", description = "opens winter ark app in your dm")
        async def ping(interaction: discord.Interaction):
            await interaction.response.send_message("opening winter ark app in your dm")





        




    async def sync_commands(self):
        await self.tree.sync()