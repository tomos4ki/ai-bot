'''
    this command did not been seen through so i need to see it and understand how it works.
    This is a Discord bot command for generating images using the Together AI API.
    It allows users to request image generation by providing a prompt.

    i will need to make some changes to add settings for the image settings 
    and number of images etc through the discord so i don't have to change them everytime
    and restart the bot for that.

    also some other changes so i can make more then the scpected number from the api, like a function calling
    and a for loops for that thing etc...

    note that this modes is sfw and don't allow nsfw sometimes, although it generated some nsfw (partially naked from the top)
    so that need some testing for it. 

    i need to make something to let the bot access it when needing functions on the dms ai so it can generate an image from this model
    in together ai api and send it when asked in the dms without a slash command.

    that's what i have for now
'''
'''
    needed features:
    1- make the receved image in an embed and in the settings when the user wants more then 1 picture it will be in the embed.
    2- make the picture in the embed low quality if that will make sending it faster and when clicked on it it will send the original picture to the user.
    3- make some buttons likr retry with this image that will maybe retry the image with the same context but the seed will be fixed this time
    so generating the seed should ether be in the program or got from the api
    4- if i can make a more quality picture or enhansing it i would like to add this feature.
    5- a button in the main embed that says generate again and will regenerate the image(s) if the user didn't get a good image and the seed should not be the same
    6- etc etc...
'''

# --- START OF assets/commands/image_generation_command.py ---
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import json
import time
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import base64
import io
import aiohttp # +++ Add aiohttp for downloading +++

from together import Together
try:
    from together import APIError, RateLimitError, AuthenticationError, BadRequestError
    BASE_TOGETHER_ERROR = APIError
except ImportError:
    class APIError(Exception): pass
    class RateLimitError(APIError): pass
    class AuthenticationError(APIError): pass
    class BadRequestError(APIError): pass
    BASE_TOGETHER_ERROR = APIError # Use APIError as the more likely base if specific ones fail

load_dotenv()

TOGETHER_AI_API_KEY = os.getenv("TOGETHER_AI_API_KEY")
DEFAULT_IMAGE_MODEL = os.getenv("IMAGE_GEN_MODEL_NAME", "black-forest-labs/FLUX.1-schnell-Free")
# +++ Define base path for SAVED images +++
SAVED_IMAGES_BASE_PATH = os.path.join(os.path.dirname(__file__), "..", "json", "image_gen_logs") # Keeps logs and images separate by session/user

class ImageGeneration(commands.Cog, name="Image Generation"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = bot.logger
        self.together_api_key = TOGETHER_AI_API_KEY
        self.image_model_name = DEFAULT_IMAGE_MODEL
        self.http_session: Optional[aiohttp.ClientSession] = None # For downloading images

        if not self.together_api_key:
            self.logger.critical("TOGETHER_AI_API_KEY not found! Image Generation will not function.")
            self.together_client = None
        else:
            try:
                self.together_client = Together(api_key=self.together_api_key)
                self.logger.info(f"Together AI client initialized for Image Gen. Model: {self.image_model_name}")
            except Exception as e:
                self.logger.critical(f"Failed to initialize Together AI client: {e}", exc_info=True)
                self.together_client = None
        
        # Logging path setup remains the same
        self.image_gen_log_path = os.path.join(os.path.dirname(__file__), "..", "json", "image_gen_cmd_logs") # Path for JSON logs
        os.makedirs(self.image_gen_log_path, exist_ok=True)
        os.makedirs(SAVED_IMAGES_BASE_PATH, exist_ok=True) # Ensure base image save path exists
        self.logger.info("ImageGeneration Cog loaded.")

    async def cog_load(self): # Called when cog is loaded
        self.http_session = aiohttp.ClientSession()
        self.logger.info("aiohttp.ClientSession created for ImageGeneration cog.")

    async def cog_unload(self): # Called when cog is unloaded
        if self.http_session:
            await self.http_session.close()
            self.logger.info("aiohttp.ClientSession closed for ImageGeneration cog.")

    async def _log_image_request(self, interaction: discord.Interaction, prompt: str, success: bool, saved_image_path: Optional[str] = None, details: Optional[str] = None, error: Optional[str] = None, image_count: int = 0):
        # Log folder now for JSON logs only
        log_folder = os.path.join(self.image_gen_log_path, str(interaction.guild_id) if interaction.guild_id else "dm_user_" + str(interaction.user.id))
        os.makedirs(log_folder, exist_ok=True)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file_path = os.path.join(log_folder, f"{timestamp_str}_{interaction.user.id}_{interaction.id}_imagereq.json")
        log_entry = {
            "timestamp": datetime.now().isoformat(), "user_id": interaction.user.id,
            "username": str(interaction.user), "guild_id": interaction.guild_id,
            "channel_id": interaction.channel_id, "prompt": prompt, "model": self.image_model_name,
            "success": success, "generated_image_count": image_count, 
            "saved_image_path": saved_image_path, # Log path to saved image
            "details": details, "error": error,
        }
        try:
            with open(log_file_path, 'w', encoding='utf-8') as f: json.dump(log_entry, f, indent=2)
        except Exception as e: self.logger.error(f"Failed to write image gen log to {log_file_path}: {e}", exc_info=True)


    @app_commands.command(name="image", description="Generates an image based on your description.")
    @app_commands.describe(prompt="Describe the image you want to create.")
    async def generate_image(self, interaction: discord.Interaction, prompt: str):
        if not self.together_client:
            await interaction.response.send_message("❌ Image Generation service unavailable. Contact owner.", ephemeral=True); return
        if not self.http_session: # Ensure http_session is available
            await interaction.response.send_message("❌ Image downloader not ready. Please try again shortly.", ephemeral=True); return
        if not prompt or len(prompt.strip()) < 3:
            await interaction.response.send_message("🤔 Please provide a more detailed description!", ephemeral=True); return

        await interaction.response.defer(ephemeral=False, thinking=True)
        self.logger.info(f"Image gen task started by U:{interaction.user.id} G:{interaction.guild_id if interaction.guild else 'DM'} P:'{prompt}'")
        try:
            await interaction.edit_original_response(content=f"🎨 Working on your image for \"{prompt[:100]}{'...' if len(prompt) > 100 else ''}\". This might take a moment, {interaction.user.mention}!")
        except discord.NotFound:
            await self._log_image_request(interaction, prompt, success=False, error="Original interaction for 'working on it' msg not found.")
            return # Cannot proceed
        except Exception as e: self.logger.error(f"Error editing 'working on it' msg for U:{interaction.user.id}: {e}", exc_info=True)

        saved_image_local_path: Optional[str] = None
        try:
            start_time = time.time()
            api_response = await asyncio.to_thread( # Use asyncio.to_thread for blocking SDK calls
                self.together_client.images.generate,
                prompt=prompt, model=self.image_model_name,
                steps=4, n=1
            )
            end_time = time.time()
            duration = round(end_time - start_time, 2)
            self.logger.info(f"Image API call for U:{interaction.user.id} completed in {duration}s.")

            image_url_from_api: Optional[str] = None # Check if API response provides a URL
            image_b64_from_api: Optional[str] = None

            if api_response and api_response.data and len(api_response.data) > 0:
                image_data_obj = api_response.data[0]
                self.logger.debug(f"Image object from API: {image_data_obj}") # Log the object to inspect its fields
                
                if hasattr(image_data_obj, 'url') and image_data_obj.url:
                    image_url_from_api = image_data_obj.url
                if hasattr(image_data_obj, 'b64_json') and image_data_obj.b64_json:
                    image_b64_from_api = image_data_obj.b64_json

                image_bytes: Optional[bytes] = None

                if image_url_from_api:
                    self.logger.info(f"Attempting to download image from URL: {image_url_from_api} for U:{interaction.user.id}")
                    try:
                        async with self.http_session.get(image_url_from_api) as resp:
                            if resp.status == 200:
                                image_bytes = await resp.read()
                                self.logger.info(f"Successfully downloaded image from URL for U:{interaction.user.id}")
                            else:
                                self.logger.error(f"Failed to download image from URL: {image_url_from_api}, status: {resp.status}")
                                await self._log_image_request(interaction, prompt, success=False, error=f"Download failed, status {resp.status}")
                    except Exception as e:
                        self.logger.error(f"Error downloading image from URL {image_url_from_api}: {e}", exc_info=True)
                        await self._log_image_request(interaction, prompt, success=False, error=f"Download exception: {str(e)}")
                
                elif image_b64_from_api:
                    self.logger.info(f"Decoding b64_json image for U:{interaction.user.id}")
                    try:
                        image_bytes = base64.b64decode(image_b64_from_api)
                    except Exception as e:
                        self.logger.error(f"Error decoding b64_json for U:{interaction.user.id}: {e}", exc_info=True)
                        await self._log_image_request(interaction, prompt, success=False, error=f"b64 decode error: {str(e)}")
                
                if image_bytes:
                    # --- Save the image locally ---
                    image_save_folder = os.path.join(SAVED_IMAGES_BASE_PATH, str(interaction.guild_id) if interaction.guild else "dm_user_" + str(interaction.user.id), "pictures")
                    os.makedirs(image_save_folder, exist_ok=True)
                    
                    # Filename: userid-YYYY_MM_DD_HH_MM_SS.png
                    img_timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
                    saved_image_filename = f"{interaction.user.id}-{img_timestamp}.png"
                    saved_image_local_path = os.path.join(image_save_folder, saved_image_filename)

                    try:
                        with open(saved_image_local_path, "wb") as f_img:
                            f_img.write(image_bytes)
                        self.logger.info(f"Saved image for U:{interaction.user.id} to: {saved_image_local_path}")
                        
                        # --- Send the locally saved file ---
                        discord_file = discord.File(saved_image_local_path)
                        msg_content = f"{interaction.user.mention}, here's your image for \"{prompt[:1000]}{'...' if len(prompt) > 1000 else ''}\"!"
                        await interaction.edit_original_response(content=msg_content, attachments=[discord_file], view=None)
                        self.logger.info(f"Sent saved image to U:{interaction.user.id} for P:'{prompt}'")
                        await self._log_image_request(interaction, prompt, success=True, details=f"Generated in {duration}s", image_count=1, saved_image_path=saved_image_local_path)
                    
                    except Exception as e:
                        self.logger.error(f"Error saving or sending local image for U:{interaction.user.id}: {e}", exc_info=True)
                        await interaction.edit_original_response(content=f"Sorry {interaction.user.mention}, I generated the image but had trouble processing/sending it.", attachments=[], view=None)
                        await self._log_image_request(interaction, prompt, success=False, error=f"Failed to save/send local: {str(e)}", saved_image_path=saved_image_local_path if 'saved_image_local_path' in locals() else None)
                else:
                    self.logger.warning(f"No image bytes obtained (from URL or b64) for U:{interaction.user.id}.")
                    await interaction.edit_original_response(content=f"Sorry {interaction.user.mention}, I couldn't retrieve the image data. Please try again.", attachments=[], view=None)
                    await self._log_image_request(interaction, prompt, success=False, error="No image bytes from API after attempting download/decode.")
            else: # No api_response.data or it's empty
                self.logger.warning(f"Image gen for U:{interaction.user.id} did not return any image data in list. Resp: {api_response}")
                await interaction.edit_original_response(content=f"Sorry {interaction.user.mention}, I couldn't generate an image for that. Try rephrasing.", attachments=[], view=None)
                await self._log_image_request(interaction, prompt, success=False, error="No data list in API response or list empty.")

        # --- Exception Handling (keep from previous correct version) ---
        except RateLimitError as e:
            self.logger.error(f"Together AI RateLimitError for U:{interaction.user.id}: {e}", exc_info=True)
            msg = f"🐢 API is busy! Please try again in a few moments, {interaction.user.mention}."
            await interaction.edit_original_response(content=msg, attachments=[], view=None)
            await self._log_image_request(interaction, prompt, success=False, error=f"RateLimitError: {str(e)}", saved_image_path=saved_image_local_path)
        except AuthenticationError as e:
            self.logger.critical(f"Together AI AuthenticationError: {e}", exc_info=True)
            msg = f"🔑 API Authentication Failed. Bot owner must check API key."
            await interaction.edit_original_response(content=msg, attachments=[], view=None)
            await self._log_image_request(interaction, prompt, success=False, error=f"AuthenticationError: {str(e)}", saved_image_path=saved_image_local_path)
        except BadRequestError as e:
            self.logger.error(f"Together AI BadRequestError for U:{interaction.user.id} (Prompt:'{prompt}'): {e}", exc_info=True)
            msg = f"🤔 AI didn't like that request. Details: `{str(e)[:500]}`. Try rephrasing?"
            await interaction.edit_original_response(content=msg, attachments=[], view=None)
            await self._log_image_request(interaction, prompt, success=False, error=f"BadRequestError: {str(e)}", saved_image_path=saved_image_local_path)
        except APIError as e: 
            self.logger.error(f"Together AI APIError ({type(e).__name__}) for U:{interaction.user.id}: {e}", exc_info=True)
            msg = f"Sorry {interaction.user.mention}, an API error ({type(e).__name__}) occurred: `{str(e)[:500]}`."
            await interaction.edit_original_response(content=msg, attachments=[], view=None)
            await self._log_image_request(interaction, prompt, success=False, error=f"{type(e).__name__}: {str(e)}", saved_image_path=saved_image_local_path)
        except discord.NotFound:
            self.logger.warning(f"ImageGen: Original deferred interaction for U:{interaction.user.id} P:'{prompt}' not found.")
            await self._log_image_request(interaction, prompt, success=False, error="Original interaction message not found for edit.", saved_image_path=saved_image_local_path)
        except Exception as e: 
            self.logger.error(f"Overall error in generate_image cmd for U:{interaction.user.id} P:'{prompt}': {e}", exc_info=True)
            msg = f"Oops! Something went very wrong, {interaction.user.mention}. The bot owner has been alerted."
            try: await interaction.edit_original_response(content=msg, attachments=[], view=None)
            except discord.NotFound: self.logger.warning(f"ImageGen: Original deferred interaction not found for generic error.")
            except Exception as followup_e: self.logger.error(f"Further error trying to send error followup: {followup_e}")
            await self._log_image_request(interaction, prompt, success=False, error=f"Outer catch: {str(e)}", saved_image_path=saved_image_local_path)


async def setup(bot: commands.Bot):
    # (Keep the setup function from the previous response, it's good)
    if not hasattr(bot, 'logger'): 
        bot.logger = logging.getLogger('discord.bot.imagegen_cog_fallback')
        if not bot.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
            bot.logger.addHandler(handler)
            bot.logger.setLevel(logging.INFO)
        bot.logger.warning("ImageGeneration cog using fallback logger.")
        
    await bot.add_cog(ImageGeneration(bot))
    cog_instance = bot.get_cog("Image Generation")
    if cog_instance and hasattr(cog_instance, 'logger'):
        cog_instance.logger.info("ImageGeneration cog loaded and added to bot successfully.")
    elif hasattr(bot, 'logger'):
        bot.logger.info("ImageGeneration cog loaded and added to bot successfully (using bot.logger).")
    else:
        print("ImageGeneration cog loaded and added to bot (fallback logger).")

# --- END OF assets/commands/image_generation_command.py ---