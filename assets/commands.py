import discord
from discord.ext import commands

class CommandTree:
    def __init__(self, bot):
        self.bot = bot
        self.tree = bot.tree

    def add_commands(self):
        @self.tree.command(name = "test", description = "Replies with Pong!")
        async def ping(interaction: discord.Interaction):
            await interaction.response.send_message("test yea!")

        

        @self.tree.command(name = "winter_ark", description = "opens winter ark app in your dm")
        async def ping(interaction: discord.Interaction):
            await interaction.response.send_message("opening winter ark app in your dm")
        

        @self.tree.command(name= "ttm", description="converts text to image(currently under testing)")
        async def ping(interaction: discord.Interaction):
            await interaction.response.send_message("currently under maintenence")
    
    # def add_commands_winter_ark(self):
    #     @self.tree.command(name = "winter_ark", description = "opens winter ark app in your dm")
    #     async def ping(interaction: discord.Interaction):
    #         await interaction.response.send_message("opening winter ark app in your dm")





        




    async def sync_commands(self):
        await self.tree.sync()