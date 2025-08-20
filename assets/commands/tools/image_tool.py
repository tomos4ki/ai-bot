# --- assets/commands/tools/image_tool.py ---
import requests
import os
import json
import logging
from datetime import datetime
import discord # Used for type hinting

logger = logging.getLogger("discord.bot.tools.image")

# This is the API for image generation, separate from the chat API
IMAGE_API_URL = "https://chutes-hidream.chutes.ai/generate"

def create_and_save_image(
    prompt: str,
    api_token: str,
    user: discord.User,
    interaction: discord.Interaction
) -> tuple[str | None, str | None]:
    """
    Generates an image, saves it and its metadata, and returns the file path.
    Returns (image_file_path, error_message)
    """
    logger.info(f"Executing image generation tool for User:{user.id} with prompt: '{prompt}'")
    
    headers = {
        "Authorization": "Bearer " + api_token,
        "Content-Type": "application/json"
    }
    body = {
        "prompt": prompt,
        "resolution": "1024x1024",
        "guidance_scale": 5,
        "num_inference_steps": 25
        # The API does not seem to return a seed, so we cannot specify it for retries yet.
    }

    try:
        response = requests.post(IMAGE_API_URL, headers=headers, json=body)
        response.raise_for_status()
        image_bytes = response.content
        logger.info(f"Successfully received image data from API for User:{user.id}")

        # --- File Saving Logic ---
        # Get the path of the main command file to build relative paths
        command_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        base_folder = os.path.join(command_dir, "images")
        images_subfolder = os.path.join(base_folder, "images")
        json_subfolder = os.path.join(base_folder, "json")

        os.makedirs(images_subfolder, exist_ok=True)
        os.makedirs(json_subfolder, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename_prefix = f"{user.id}_{timestamp}"
        
        image_filepath = os.path.join(images_subfolder, f"{filename_prefix}.png")
        json_filepath = os.path.join(json_subfolder, f"{filename_prefix}.json")

        # Save the image
        with open(image_filepath, "wb") as f:
            f.write(image_bytes)

        # Create and save detailed metadata
        metadata = {
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "user_id": user.id,
            "username": str(user),
            "guild_id": interaction.guild.id if interaction.guild else None,
            "guild_name": interaction.guild.name if interaction.guild else "DM",
            "channel_id": interaction.channel_id,
            "ai_prompt": prompt,
            "api_settings": {
                "model": "chutes-hidream",
                "resolution": body["resolution"],
                "guidance_scale": body["guidance_scale"],
                "num_inference_steps": body["num_inference_steps"],
                "seed": "Not Provided by API"
            },
            "saved_image_path": image_filepath
        }
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4)
            
        logger.info(f"Saved image to {image_filepath} and metadata to {json_filepath}")
        return image_filepath, None

    except requests.exceptions.HTTPError as http_err:
        error_message = f"API Error: {http_err.response.status_code} - {http_err.response.text}"
        logger.error(f"Image generation failed for User:{user.id}: {error_message}")
        return None, error_message
    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logger.error(f"Image generation failed for User:{user.id}: {error_message}", exc_info=True)
        return None, error_message