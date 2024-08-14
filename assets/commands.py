import discord
from discord.ext import commands

class CommandTree:
    def __init__(self, bot):
        self.bot = bot
        self.tree = bot.tree

    def add_commands(self):
        @self.tree.command(name = "ping", description = "Replies with Pong!")
        async def ping(interaction: discord.Interaction):
            await interaction.response.send_message("Pong!")





        @self.tree.command(name = "hello", description = "Says hello!")
        async def hello(interaction: discord.Interaction):
            await interaction.response.send_message("Hello!")
    async def sync_commands(self):
        await self.tree.sync()