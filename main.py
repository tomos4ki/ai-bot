"""
hmmm...
"""

import json
import logging
import os
import platform
import sys
import discord
import asyncio
from discord.ext import commands, tasks
from discord.ext.commands import Context
from dotenv import load_dotenv
from assets.log import log_message
import random


from assets.commands import CommandTree
# from assets.dms import handle_dm


load_dotenv()

#from assets.google_gemini import handle_dm

#from assets.log import log



"""	
Setup bot intents (events restrictions)
For more information about intents, please go to the following websites:
https://discordpy.readthedocs.io/en/latest/intents.html
https://discordpy.readthedocs.io/en/latest/intents.html#privileged-intents


Default Intents:
intents.bans = True
intents.dm_messages = True
intents.dm_reactions = True
intents.dm_typing = True
intents.emojis = True
intents.emojis_and_stickers = True
intents.guild_messages = True
intents.guild_reactions = True
intents.guild_scheduled_events = True
intents.guild_typing = True
intents.guilds = True
intents.integrations = True
intents.invites = True
intents.messages = True # `message_content` is required to get the content of the messages
intents.reactions = True
intents.typing = True
intents.voice_states = True
intents.webhooks = True

Privileged Intents (Needs to be enabled on developer portal of Discord), please use them only if you need them:
intents.members = True
intents.message_content = True
intents.presences = True
"""
intents = discord.Intents.default()
intents.message_content = True#reads the messages for a possible command
intents.typing = False
intents.presences = False




class LggingFormat(logging.Formatter):
    #colors
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    # Styles
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: red + bold,
    }

    def format(self, record):
        log_color = self.COLORS[record.levelno]
        format = "(black){asctime}(rest)(levelcolor){levelname:<8}(reset) (green){name}(reset) (message)"
        format = format.replace("(black)", self.black + self.bold)
        format = format.replace("(rest)", self.reset)
        format = format.replace("(levelcolor)", log_color)
        format = format.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


logger = logging.getLogger("discord-ai-initial")
logger.setLevel(logging.INFO)


#console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(LggingFormat())
#file handler
file_handler = logging.FileHandler(filename="discord-ai.log", encoding="utf-8", mode="w")
file_handler_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name} : {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(file_handler_formatter)

#adding the handler
logger.addHandler(console_handler)
logger.addHandler(file_handler)






class DiscordAiBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix = commands.when_mentioned_or(os.getenv("DISCORD_AI_PREFIX")),
            intents = intents,
            help_command = None,
        )
        """
        This creates custom bot variables so that we can access these variables in cogs more easily.

        For example, The logger is available using the following code:
        - self.logger # In this class
        - bot.logger # In this file
        - self.bot.logger # In cogs
        """
        self.logger = logger
        self.database = None
        self.bot_prefix = os.getenv("DISCORD_AI_PREFIX")
        self.invite_link = os.getenv("DISCORD_AI_INVITE_LINK")


    #the initial database function is not set yet for now, but it will be set in the future.


    async def load_cogs(self) -> None:
        """
        The code in this function is executed whenever the bot will start.
        """
        #loading the dms from assets.dms.py
        try:
            await self.load_extension("assets.dms")
            self.logger.info("loaded extention 'dms' successfully")
        except Exception as e:
            exception = f"{type(e).__name__}: {e}"
            self.logger.error(f"Failed to load extention 'dms'/n {exception}")
        # Load all cogs in the assets/commands directory.
        commands_path = os.path.realpath(os.path.join(os.path.dirname(__file__),"assets/commands")) #"assets","commands"
        for filename in os.listdir(commands_path):
            if filename.endswith(".py"):
                extention = filename[:-3]
                try:
                    # Load the cog
                    await self.load_extension(f"assets.commands.{extention}")
                    self.logger.info(f"Loaded extention 'assets.commands.{filename}'")
                except Exception as e:
                    exception = f"{type(e).__name__}: {e}"
                    self.logger.error(
                        f"Failed to load extention {extention}/n {exception}"
                    )

        #if you want cooldown for all command maybe this code will help, it will not work if you just uncomment it but it can be put in a way that it will do work so it's a little help if you want that
        #@commands.cooldown(1, 60, commands.BucketType.user)  # 1 command per 60 seconds per user
            #async def my_command(ctx):
            #Command code here
    @tasks.loop(seconds=60)
    async def statues_update_task(self) -> None:
        """
        This function is used to update the bot's status every 60 seconds.
        Setup the activity status task of the bot.
        """

        playingStatus = ["Playing a game of uptime", "Playing hide and seek with commands", "Playing around with server settings", "Playing the role of your virtual assistant",
                         "Playing with the server's emojis", "Playing a game of trivia", "Playing with the server's settings", "Playing with the server's members", "Playing with the server's channels",
                         "Playing with the server's roles", "Playing with the server's permissions", "Playing with the server's integrations", "Playing with the server's webhooks", "Playing with the server's stickers",
                         "Playing with the server's invites", "Playing with the server's events", "Playing with the server's audit logs", "Playing with the server's voice channels", "Playing with the server's text channels",
                         "Playing with the server's categories", "Playing with the server's emojis and stickers", "Playing a game of chess", "Playing a game of poker", "Playing a game of cards against humanity", "Playing a game of trivia crack",
                        "Playing a game of monopoly", "Playing a game of scrabble", "Playing a game of chess.com"]
        # [Playing a game of hide and seek, Playing a game of trivia, Playing a game of chess, Playing a game of poker, Playing a game of cards against humanity, Playing a game of monopoly, Playing a game of scrabble, Playing a game of chess.com, Playing a game of checkers,
        # Playing a game of connect four, Playing a game of tic tac toe, Playing a game of hangman, Playing a game of battleship, Playing a game of uno, Playing a game of jenga, Playing a game of pictionary,
        #commented streaming because it will not work without a link
        # streamingStatus = [
        #     "Streaming on Twitch!", "Streaming on YouTube!", "Streaming on Facebook!", "Streaming on Trovo!", "Streaming on Dlive!", "Streaming on NimoTV!", "Streaming on Caffeine!", "Streaming on Mixer!", "Streaming on Smashcast!", "Streaming on Picarto!",
        #     "Streaming on Own3d!", "Streaming on Streamcraft!", "Streaming on AfreecaTV!", "Streaming on Huya!", "Streaming on Douyu!", "Streaming on Bigo Live!", "Streaming on VK Live!", "Streaming on Niconico!", "Streaming on Twitch Sings!"
        #     ]
        listeningStatus = [
            "Listening to your requests", "Listening to your commands", "Listening to your feedback", "Listening to your suggestions", "Listening to your ideas", "Listening to your thoughts", "Listening to your opinions", "Listening to your concerns",
            "Listening to your questions", "Listening to your answers", "Listening to your problems", "Listening to your solutions", "Listening to your stories", "Listening to your experiences", "Listening to your adventures", "Listening to your journeys",
            "Listening to your travels", "Listening to your dreams", "Listening to your goals", "Listening to your aspirations", "Listening to your ambitions", "Listening to your desires", "Listening to your wishes", "Listening to your hopes",
            "Listening to your fears", "Listening to your worries", "Listening to your doubts", "Listening to your regrets", "Listening to your mistakes", "Listening to your failures", "Listening to your successes", "Listening to your achievements",
            "Listening to your victories", "Listening to your losses", "Listening to your challenges", "Listening to your struggles", "Listening to your triumphs", "Listening to your defeats", "Listening to your battles", "Listening to your wars",
            "Listening to your conflicts", "Listening to your disputes", "Listening to your arguments", "Listening to your disagreements", "Listening to your discussions", "Listening to your conversations", "Listening to your dialogues", "Listening to your debates",
        ]
        watchingStatus = [
            "Watching over the server", "Watching over the members", "Watching over the channels", "Watching over the roles", "Watching over the permissions", "Watching over the integrations", "Watching over the webhooks", "Watching over the stickers",
            "Watching over the invites", "Watching over the events", "Watching over the audit logs", "Watching over the voice channels", "Watching over the text channels", "Watching over the categories", "Watching over the emojis and stickers", "Watching over the server's settings",
            "Watching over the server's members", "Watching over the server's channels", "Watching over the server's roles", "Watching over the server's permissions", "Watching over the server's integrations", "Watching over the server's webhooks",
            "Watching over the server's stickers", "Watching over the server's invites", "Watching over the server's events", "Watching over the server's audit logs", "Watching over the server's voice channels", "Watching over the server's text channels",
            "Watching over the server's categories", "Watching over the server's emojis and stickers", "Watching over the server's members and channels", "Watching over the server's members and roles", "Watching over the server's members and permissions",
            "Watching over the server's members and integrations", "Watching over the server's members and webhooks", "Watching over the server's members and stickers", "Watching over the server's members and invites", "Watching over the server's members and events",
            "Watching over the server's members and audit logs", "Watching over the server's members and voice channels", "Watching over the server's members and text channels", "Watching over the server's members and categories", "Watching over the server's members and emojis and stickers",
            "Watching over the server's channels and roles", "Watching over the server's channels and permissions", "Watching over the server's channels and integrations", "Watching over the server's channels and webhooks", "Watching over the server's channels and stickers",
        ]

        activities = [
            (discord.ActivityType.playing, random.choice(playingStatus)),
            #(discord.ActivityType.streaming, random.choice(streamingStatus)),
            (discord.ActivityType.listening, random.choice(listeningStatus)),
            (discord.ActivityType.watching, random.choice(watchingStatus)),
        ]
    
        activity_type, activity_name, *url = random.choice(activities)
    
        if activity_type == discord.ActivityType.streaming:
            if url:
                activity = discord.Streaming(name=activity_name, url=url[0])
            else:
                activity = discord.Streaming(name=activity_name)
        else:
            activity = discord.Activity(type=activity_type, name=activity_name)

        
        discordStatus = [discord.Status.dnd, discord.Status.idle, discord.Status.online, discord.Status.invisible]
        #discordStatus = [discord.Status.invisible]
        
        new_status = random.choice(discordStatus)
    
        await self.change_presence(activity=activity, status=new_status)

        # Create a message that describes the change.
        log_msg = (f"Status changed: Activity type set to {activity.type.name}, "
               f"name set to '{activity.name}', presence set to {new_status.name}.")
    
        # Print to the terminal.
        print(log_msg)
    
        # Log the change using the logger.
        self.logger.info(log_msg)




    @statues_update_task.before_loop
    async def before_status_task(self) -> None:
        """
        Before starting the status changing task, we make sure the bot is ready
        """
        await self.wait_until_ready()

    async def setup_hook(self) -> None:
        """
        This will just be executed when the bot starts the first time.
        """

        await asyncio.sleep(1)
        self.logger.info(f"Logged in as {self.user.name}")
        await asyncio.sleep(1)
        self.logger.info(f"Discord.py version: {discord.__version__}")
        await asyncio.sleep(1)
        self.logger.info(f"Python version: {platform.python_version()}")
        await asyncio.sleep(1)
        self.logger.info(
            f"Running om: {platform.system()} {platform.release()}({os.name})"
        )
        await asyncio.sleep(1)
        self.logger.info("Starting the bot...")
        await asyncio.sleep(1)
        self.logger.info("Loading cogs...")
        await asyncio.sleep(1)
        await self.load_cogs()
        await asyncio.sleep(1)
        self.statues_update_task.start()
    


    # async def on_message(self, message: discord.Message) -> None:
    #     """
    #     The code in this event is executed every time someone sends a message, with or without the prefix

    #     :param message: The message that was sent.
    #     """
    #     if message.author == self.user or message.author.bot:
    #         return
    #         # you can change this when you can send messages through the bot directly,
    #         # this will make you able to talk to other bots in other ways
    #     if message.channel.type == discord.ChannelType.private:
    #         await handle_dm(message)
    #     else:
    #         await self.process_commands(message)

    async def on_command_completion(self, context: Context) -> None:
        """
        The code in this event is executed every time a normal command has been *successfully* executed.

        :param context: The context of the command that has been executed.
        """
        full_command_name = context.command.qualified_name
        split = full_command_name.split(" ")
        executed_command = str(split[0])
        if context.guild is not None:
            self.logger.info(
                f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})"
            )
        else:
            self.logger.info(
                f"Executed {executed_command} command in DM by {context.author} (ID: {context.author.id})"
            )


    async def on_command_error(self, context: Context, error):
        """
        The code in this event is executed every time a normal valid command catches an error.

        :param context: The context of the normal command that failed executing.
        :param error: The error that has been faced.
        """
        if isinstance(error, commands.CommandOnCooldown):
            #this will send the user ether in their DMs or in the server with a message if he have a cooldown in one or all of his commands :)
            minutes, seconds = divmod(error.retry_after, 60)
            hours, minutes = divmod(minutes, 60)
            hours = hours % 24
            embed = discord.Embed(
                title="Command on cooldown",
                description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)

        elif isinstance(error, commands.NotOwner):
            embed = discord.Embed(
                title="Not the owner",
                description="** You are not the owner of this Bot! ** - You can't use this command.", color=0xE02B2B
            )
            await context.send(embed=embed)
            if context.guild:
                self.logger.warning(
                    f"{context.author}(ID: {context.author.id}) tried to use a command that is only available for the owner of the bot in {context.guild.name} (ID: {context.guild.id}), but the user is not an owner of the bot or in the allowed list."
                )
            else:
                self.logger.warning(
                    f"{context.author}(ID: {context.author.id}) tried to use a command that is only available for the owner of the bot in DM, but the user is not an owner of the bot or in the allowed list."
                )
        elif isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="Missing permission(s)",
                description="You are missing the premission(s)`"
                +",".join(error.missing_premissions)
                +"` to execute this command.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.BotMissingPermissions):
            embed = discord.Embed(
                title="Missing permission(s)",
                description="I am missing the premission(s)`"
                +",".join(error.missing_premissions)
                +"` to execute this command.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
        elif isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                title="Missing required argument",
                # We need to capitalize because the command arguments have no capital letter in the code and they are the first word in the error message.
                description=str(error).capitalize(),
                color=0xE02B2B,
                #maybe working i need to test when i have time for the below code :)
                # description="You are missing the required argument `"
                # + error.param.name
                # + "` to execute this command.",
                # color=0xE02B2B,
            )
            await context.send(embed=embed)
        else:
            raise error

    



bot=DiscordAiBot()
bot.run(os.getenv("DISCORD_AI_TOKEN"))

        # statues = []
        # # Get the current time
        # current_time = datetime.datetime.now()
        # # Update the bot's status
        # await self.change_presence(
        #     activity=discord.Game(name=f"Current time: {current_time}")
        # )







# activity = discord.Activity(type=discord.ActivityType.playing, name="updating dm's :(")
# client = commands.Bot(
#     command_prefix='!', 
#     activity=activity, 
#     intents= intents, 
#     status=discord.Status.dnd, 
#     appliction_id=1223314662863671326)







# command_tree = CommandTree(client)
# command_tree.add_commands()
# command_tree.sync_commands()

# class Ai_bot(commands.Bot):
#     def __init__(self, command_prefix):
#         super().__init__(command_prefix = command_prefix)
#         self.tree = commands.CommandTree(self)
#         self.commands = CommandTree(self)
# @client.event
# async def on_ready():
#     print(f'{client.user.name} has connected to Discord on {log_message("connected",1)}')
#     await command_tree.sync_commands()





# @client.event
# async def on_message(message):
#     if message.channel.type == discord.ChannelType.private:
#         await handle_dm(message)
#     else:
#         await client.process_commands(message)






# if __name__ == '__main__':
#     token = os.getenv('DISCORD_AI_TOKEN')
#     try:
#         client.run(token)
#     except Exception as e:
#         print({e})
#         #log_message  1 bot, 2 error, 3 notification, 4 reply, else unknown