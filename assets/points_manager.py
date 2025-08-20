# --- START OF assets/points_manager.py ---
import json
import os
import asyncio
import logging
from typing import Dict, Optional, Tuple, List, Literal

logger = logging.getLogger(__name__) # Logger for this module

class PointsManager:
    """
    Manages user and AI points stored in a JSON file with locking for async safety.
    """
    _DEFAULT_POINTS_FILE_NAME = "points_data.json"
    _DEFAULT_STARTING_POINTS = 10
    _DEFAULT_AI_STARTING_POINTS = 50 # Initial AI points
    # +++ Default for thresholds +++
    _DEFAULT_MESSAGES_PER_POINT_GUILD = 10
    _DEFAULT_MESSAGES_PER_POINT_DM = 100

    def __init__(self,
                 json_dir: str = os.path.join(os.path.dirname(__file__), "json"), # Dir relative to this file
                 points_file_name: str = _DEFAULT_POINTS_FILE_NAME,
                 starting_points: int = _DEFAULT_STARTING_POINTS,
                 ai_starting_points: int = _DEFAULT_AI_STARTING_POINTS,
                 ):
        self.json_folder = json_dir
        self.points_file_path = os.path.join(self.json_folder, points_file_name)
        self.starting_points = starting_points
        self.ai_starting_points = ai_starting_points
        # --- Thresholds loaded from the file ---
        self.messages_per_point_guild = self._DEFAULT_MESSAGES_PER_POINT_GUILD
        self.messages_per_point_dm = self._DEFAULT_MESSAGES_PER_POINT_DM
        self._lock = asyncio.Lock()

        os.makedirs(self.json_folder, exist_ok=True)
        # Initialize file on startup if it doesn't exist or is invalid
        asyncio.create_task(self._initialize_file()) # Run as background task
        logger.info(f"PointsManager initialized. Data file: {self.points_file_path}")

    async def _initialize_file(self):
        """Ensures the points file exists and has a valid base structure."""
        async with self._lock:
            needs_save = False
            data = {}
            default_data = {
                "user_points": {},  # User points data
                "ai_points": self.ai_starting_points,  # AI points
                "cooldowns": {},  # Cooldown data
                # +++ adding thershold to default structure
                "config": {
                    "messages_per_point_guild": self.messages_per_point_guild,
                    "messages_per_point_dm": self.messages_per_point_dm
                }
            }
            try:
                if not os.path.exists(self.points_file_path):
                    logger.info(f"Points file not found. Creating '{self.points_file_path}'.")
                    data = default_data
                    needs_save = True
                else:
                    with open(self.points_file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if not content:
                             logger.warning(f"Points file empty. Initializing.")
                             data = default_data
                             needs_save = True
                        else:
                             data = json.loads(content)
                             # Basic validation
                             if "user_points" not in data or not isinstance(data["user_points"], dict): data["user_points"] = {}; needs_save = True
                             if "ai_points" not in data or not isinstance(data["ai_points"], int): data["ai_points"] = self.ai_starting_points; needs_save = True
                             if "cooldowns" not in data or not isinstance(data["cooldowns"], dict): data["cooldowns"] = {}; needs_save = True
                             # +++ adding config section +++
                             if "config" not in data or not isinstance(data["config"], dict): data["config"] = {}; needs_save = True
                             if "message_per_point_guild" not in data["config"] or not isinstance(data["config"]["message_per_point_guild"], int): data["config"]["message_per_point_guild"] = self._DEFAULT_MESSAGES_PER_POINT_GUILD; needs_save = True
                             if "message_per_point_dm" not in data["config"] or not isinstance(data["config"]["message_per_point_dm"], int): data["config"]["message_per_point_dm"] = self._DEFAULT_MESSAGES_PER_POINT_DM; needs_save = True

            except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
                 logger.error(f"Error reading/initializing points file {self.points_file_path}: {e}. Recreating.", exc_info=True)
                 data = default_data
                 needs_save = True
            
            # +++ loading the threashold to the instance variable +++
            self.messages_per_point_guild = data.get("config", {}).get("messages_per_point_guild", self._DEFAULT_MESSAGES_PER_POINT_GUILD)
            self.messages_per_point_dm = data.get("config", {}).get("messages_per_point_dm", self._DEFAULT_MESSAGES_PER_POINT_DM)
            # --- End loading thresholds ---

            if needs_save:
                try:
                    with open(self.points_file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
                    logger.info(f"Points file initialized/corrected: {self.points_file_path}")
                except Exception as e:
                     logger.error(f"Failed to save initial points data to {self.points_file_path}: {e}", exc_info=True)


    async def _load_points_data(self) -> Dict:
        """Loads points data, ensuring base structure exists."""
        async with self._lock:
            try:
                # Assume _initialize_file ran on startup, file should exist
                with open(self.points_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if not content: # Should ideally not happen after init, but safety check
                        logger.warning(f"Points file '{self.points_file_path}' became empty? Returning default.")
                        return {"user_points": {}, "ai_points": self.ai_starting_points, "cooldowns": {}, "config": {}}
                    data = json.loads(content)
                    # Ensure base keys exist after loading
                    if "user_points" not in data: data["user_points"] = {}
                    if "ai_points" not in data: data["ai_points"] = self.ai_starting_points
                    if "cooldowns" not in data: data["cooldowns"] = {}
                    if "config" not in data: data["config"] = {}
                    return data
            except (json.JSONDecodeError, FileNotFoundError, Exception) as e:
                logger.error(f"Critical error loading points data from {self.points_file_path}: {e}. Returning default.", exc_info=True)
                return {"user_points": {}, "ai_points": self.ai_starting_points, "cooldowns": {}, "config": {}}

    async def _save_points_data(self, data: Dict) -> None:
        """Saves points data."""
        async with self._lock:
            try:
                with open(self.points_file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4)
            except Exception as e:
                logger.error(f"Error saving points data to {self.points_file_path}: {e}", exc_info=True)

    def _get_user_data(self, user_id: int, username: str, data: Dict) -> Dict:
        """Gets/Initializes user data structure within the loaded data dict."""
        user_id_str = str(user_id)
        if user_id_str not in data.get("user_points", {}):
            logger.info(f"Initializing points data structure for user {user_id_str} ({username}).")
            data["user_points"][user_id_str] = {
                "usernames": [username],  # List of usernames for the user
                "points": self.starting_points, 
                "message_count": 0,
                "dm_message_count": 0
            }
        else:
            user_entry = data["user_points"][user_id_str]
            # Ensure all keys exist
            if "points" not in user_entry: user_entry["points"] = self.starting_points
            if "message_count" not in user_entry: user_entry["message_count"] = 0
            if "dm_message_count" not in user_entry: user_entry["dm_message_count"] = 0 # Add DM counter if missing
            if "usernames" not in user_entry or not isinstance(user_entry["usernames"], list):
                user_entry["usernames"] = [username] # Initialize or fix username list
            # --- Update username history if changed ---
            elif username not in user_entry["usernames"]:
                 logger.info(f"Updating username for user {user_id_str}. New: {username}, Previous: {user_entry['usernames'][-1]}")
                 user_entry["usernames"].append(username)
                 # Optional: Limit history size
                 # max_history = 5
                 # if len(user_entry["usernames"]) > max_history:
                 #     user_entry["usernames"] = user_entry["usernames"][-max_history:]
        return data["user_points"][user_id_str]

    # --- Public Interface Methods ---

    async def get_points(self, user_id: int, username: Optional[str] = "Unknown") -> int:
        """Gets the current points for a user."""
        data = await self._load_points_data()
        user_data = self._get_user_data(user_id, username, data)
        return user_data.get("points", self.starting_points)

    async def adjust_points(self, user_id: int, username: str, amount: int) -> int:
        """Adjusts points for a user. Returns the new point total."""
        data = await self._load_points_data()
        user_id_str = str(user_id)
        user_data = self._get_user_data(user_id, username, data) # Ensure user exists

        current_points = user_data.get("points", self.starting_points)
        new_points = current_points + amount
        data["user_points"][user_id_str]["points"] = new_points
        await self._save_points_data(data)
        logger.info(f"Adjusted points for user {user_id_str} by {amount}. New total: {new_points}")
        return new_points

    async def get_ai_points(self) -> int:
        """Gets the AI's current points."""
        data = await self._load_points_data()
        return data.get("ai_points", self.ai_starting_points)

    async def adjust_ai_points(self, amount: int) -> int:
        """Adjusts points for the AI. Returns the new point total."""
        data = await self._load_points_data()
        current_points = data.get("ai_points", self.ai_starting_points)
        new_points = max(0, current_points + amount)
        data["ai_points"] = new_points
        await self._save_points_data(data)
        logger.info(f"Adjusted AI points by {amount}. New total: {new_points}")
        return new_points

    async def increment_message_count(self, user_id: int, username: str) -> bool: # Add username param
        """Increments GUILD message count. Returns True if point added."""
        data = await self._load_points_data()
        user_id_str = str(user_id)
        user_data = self._get_user_data(user_id, username, data)

        current_count = user_data.get("message_count", 0)
        new_count = current_count + 1
        point_added = False

        # +++ Use correct threshold loaded from config +++
        threshold = self.messages_per_point_guild # Changed from self.messages_per_point
        if new_count >= threshold:
            current_points = user_data.get("points", self.starting_points)
            data["user_points"][user_id_str]["points"] = current_points + 1
            data["user_points"][user_id_str]["message_count"] = 0
            point_added = True
            # Use the correct threshold variable in the log message
            logger.info(f"GUILD MSG COUNT: User {user_id_str} ({username}) hit threshold ({threshold}). +1 point. New total: {current_points + 1}")
        else:
            data["user_points"][user_id_str]["message_count"] = new_count

        await self._save_points_data(data)
        return point_added
    
    async def increment_dm_message_count(self, user_id: int, username: str) -> bool: # Add username param
        """Increments DM message count. Returns True if point added."""
        data = await self._load_points_data()
        user_id_str = str(user_id)
        user_data = self._get_user_data(user_id, username, data) # Pass username

        current_count = user_data.get("dm_message_count", 0)
        new_count = current_count + 1
        point_added = False

        # Use DM threshold loaded from config
        threshold = self.messages_per_point_dm
        if new_count >= threshold:
            current_points = user_data.get("points", self.starting_points)
            data["user_points"][user_id_str]["points"] = current_points + 1
            data["user_points"][user_id_str]["dm_message_count"] = 0 # Reset DM counter
            point_added = True
            logger.info(f"DM MSG COUNT: User {user_id_str} ({username}) hit threshold ({threshold}). +1 point. New total: {current_points + 1}")
        else:
            data["user_points"][user_id_str]["dm_message_count"] = new_count

        await self._save_points_data(data)
        return point_added

    async def get_message_count(self, user_id: int, username: Optional[str] = "Unknown") -> Dict[str, int]:
        """Gets the user's current message count towards the next point."""
        data = await self._load_points_data()
        user_data = self._get_user_data(user_id, username, data)
        return {
            "guild_count": user_data.get("message_count", 0),
            "dm_count": user_data.get("dm_message_count", 0)
        }

    async def get_cooldown_data(self, user_id: int) -> Optional[Dict]:
        """Gets the cooldown data for a user."""
        data = await self._load_points_data()
        return data.get("cooldowns", {}).get(str(user_id))

    async def set_cooldown_data(self, user_id: int, cooldown_info: Dict) -> None:
        """Sets the cooldown data for a user."""
        data = await self._load_points_data()
        if "cooldowns" not in data: data["cooldowns"] = {}
        data["cooldowns"][str(user_id)] = cooldown_info
        await self._save_points_data(data)

    async def remove_cooldown_data(self, user_id: int) -> None:
        """Removes cooldown data for a user."""
        data = await self._load_points_data()
        if "cooldowns" in data and str(user_id) in data["cooldowns"]:
            del data["cooldowns"][str(user_id)]
            await self._save_points_data(data)

    async def set_threshold(self, threshold_type: Literal['guild', 'dm'], value: int) -> bool:
        """Updates a message count threshold."""
        if value <= 0:
            logger.error("Threshold value must be positive.")
            return False # Or raise error

        data = await self._load_points_data()
        if "config" not in data: data["config"] = {} # Should exist from init, but safety

        key = f"messages_per_point_{threshold_type}"
        if key not in data["config"]:
             logger.warning(f"Threshold key '{key}' not found in config, adding.")

        data["config"][key] = value
        await self._save_points_data(data)

        # Update instance variable immediately
        if threshold_type == 'guild':
            self.messages_per_point_guild = value
        elif threshold_type == 'dm':
            self.messages_per_point_dm = value

        logger.info(f"Threshold '{key}' set to {value}.")
        return True
# Create a single instance for easy import across cogs
points_manager = PointsManager()
# --- END OF assets/points_manager.py ---