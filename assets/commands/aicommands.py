# --- START OF assets/commands/aicommands.py ---
import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
from discord.ext.commands import Context
import json
import os
import asyncio
import time
from typing import Dict, Literal, Optional, List
from datetime import datetime, timedelta


from assets.points_manager import points_manager


# --- Constants ---
DISTRIBUTE_COOLDOWN_SECONDS = 30
DISTRIBUTE_CHECKER_SECONDS = 30 # checkerAfterCooldown duration
DISTRIBUTE_CHECKER_MAX_SECONDS = 60 # Max duration for checkerAfterCooldown after doubling
MAX_COOLDOWN_MULTIPLIER = 8 # Example: Max cooldown 30 * 8 = 240 seconds (4 mins)


#helper Function for Cooldown Formatting ---
def format_time_delta(seconds: float) -> str:
    """Formats a duration in seconds into a human-readable string."""
    if seconds < 1: return "less than a second"
    delta = timedelta(seconds=int(seconds))
    parts = []
    total_seconds = int(delta.total_seconds())
    hrs, rem = divmod(total_seconds, 3600)
    mins, secs = divmod(rem, 60)
    if hrs > 0: parts.append(f"{hrs} hour{'s' if hrs > 1 else ''}")
    if mins > 0: parts.append(f"{mins} minute{'s' if mins > 1 else ''}")
    if secs > 0: parts.append(f"{secs} second{'s' if secs > 1 else ''}")
    if not parts: return "0 seconds"
    return ", ".join(parts[:-1]) + f" and {parts[-1]}" if len(parts) > 1 else parts[0]

# --- Ai Help View Class ---


class AIHelpView(ui.View):
    # --- Use the AIHelpView class exactly as provided in Step 4 ---
    # --- of the response beginning "Okay, I see the code..." ---
    # --- It includes the init, buttons, callbacks, embed builders ---
    def __init__(self, commands_data: List[Dict], timeout=180.0):
        super().__init__(timeout=timeout)
        self.commands_data = commands_data
        self.current_index = -1 # -1 indicates the main list view
        self.command_buttons = []
        row = 0
        for i, cmd_info in enumerate(self.commands_data):
             if i > 0 and i % 5 == 0: row += 1
             if row >= 4: break
             button = ui.Button(label=cmd_info["name"], style=discord.ButtonStyle.secondary, custom_id=f"help_cmd_{i}", row=row)
             button.callback = self.command_button_callback
             self.command_buttons.append(button)
        self.prev_button = ui.Button(label="⬅️ Previous", style=discord.ButtonStyle.blurple, custom_id="help_prev", disabled=True, row=4)
        self.prev_button.callback = self.nav_callback
        self.next_button = ui.Button(label="Next ➡️", style=discord.ButtonStyle.blurple, custom_id="help_next", row=4)
        self.next_button.callback = self.nav_callback
        self.back_button = ui.Button(label="Back to List", style=discord.ButtonStyle.grey, custom_id="help_back", row=4)
        self.back_button.callback = self.nav_callback
        self._update_view() # Initial setup

    def _update_view(self):
        self.clear_items()
        if self.current_index == -1:
            for btn in self.command_buttons: self.add_item(btn)
        else:
            self.prev_button.disabled = (self.current_index == 0)
            self.next_button.disabled = (self.current_index >= len(self.commands_data) - 1)
            self.add_item(self.prev_button); self.add_item(self.next_button); self.add_item(self.back_button)

    async def command_button_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        try:
            self.current_index = int(custom_id.split("_")[-1])
            if self.current_index >= len(self.commands_data): raise IndexError
            await self.show_command_help(interaction)
        except (ValueError, IndexError):
            await interaction.response.send_message("Invalid button action.", ephemeral=True)
            await self.show_command_list(interaction) # Show list again

    async def nav_callback(self, interaction: discord.Interaction):
        custom_id = interaction.data["custom_id"]
        if custom_id == "help_prev":
            if self.current_index > 0: self.current_index -= 1
            await self.show_command_help(interaction)
        elif custom_id == "help_next":
            if self.current_index < len(self.commands_data) - 1: self.current_index += 1
            await self.show_command_help(interaction)
        elif custom_id == "help_back":
            await self.show_command_list(interaction)

    async def _build_command_list_embed(self) -> discord.Embed:
        embed = discord.Embed(title="🤖 Hu Tao AI Commands", description="Click a button below.", color=discord.Color.purple())
        for cmd_info in self.commands_data: embed.add_field(name=f"`/{cmd_info['name']}`", value=cmd_info['short_desc'], inline=False)
        return embed

    async def _build_command_help_embed(self) -> Optional[discord.Embed]:
        if self.current_index < 0 or self.current_index >= len(self.commands_data): return None
        cmd_info = self.commands_data[self.current_index]
        embed = discord.Embed(title=f"🤖 Help: `/{cmd_info['name']}`", description=cmd_info['long_desc'], color=discord.Color.purple())
        if cmd_info.get('usage'): embed.add_field(name="Usage", value=f"`/{cmd_info['name']} {cmd_info['usage']}`", inline=False)
        if cmd_info.get('example'): embed.add_field(name="Example", value=f"`{cmd_info['example']}`", inline=False)
        if cmd_info.get('cooldown'): embed.add_field(name="Cooldown", value=cmd_info['cooldown'], inline=False)
        embed.set_footer(text=f"Command {self.current_index + 1} of {len(self.commands_data)}")
        return embed

    async def show_command_list(self, interaction: discord.Interaction):
        self.current_index = -1
        self._update_view()
        embed = await self._build_command_list_embed()
        try:
            if not interaction.response.is_done(): await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
            else: await interaction.edit_original_response(embed=embed, view=self)
        except Exception as e: print(f"Error show_command_list: {e}")

    async def show_command_help(self, interaction: discord.Interaction):
        self._update_view()
        embed = await self._build_command_help_embed()
        if embed is None: await self.show_command_list(interaction); return
        try:
            if not interaction.response.is_done(): await interaction.response.send_message(embed=embed, view=self, ephemeral=True)
            else: await interaction.edit_original_response(embed=embed, view=self)
        except Exception as e: print(f"Error show_command_help: {e}")

    async def on_timeout(self):
         # Disable buttons visually (actual interaction check handles logic)
         for item in self.children:
             if isinstance(item, discord.ui.Button): item.disabled = True
         # Try editing the original message
         try:
             # Get original message if stored (need to modify view init to store it)
             # await original_message.edit(view=self)
             pass # Placeholder - editing requires storing the message reference
         except discord.NotFound: pass # Ignore if message deleted


# -----------------------  *** Main Cog *** -----------------------

class AiCommands(commands.Cog, name="AI Commands"):
    def __init__(self, bot: commands.Bot) -> None: # Corrected __init__
        self.bot = bot
        self.logger = bot.logger
        # --- Remove internal point logic ---
        # Remove self.points_file_path, self.starting_points, self.ai_starting_points, self.messages_per_point
        # Remove self._points_lock
        # Remove _load_points_data_aicmd, _save_points_data_aicmd, _initialize_user_data_aicmd

        # --- AI Command Help Data ---
        self.ai_commands_help = [
             {"name": "aihelp", "short_desc": "Shows this help message.", "long_desc": "Displays interactive help.", "usage": "", "example": "/aihelp"},
             {"name": "stats", "short_desc": "Shows your/Hu Tao's points.", "long_desc": "Displays your points, progress to next point, and Hu Tao's points.", "usage": "", "example": "/stats"},
             {"name": "distributepoints", "short_desc": "Give/take points from Hu Tao.", "long_desc": f"Costs 1 point. Cooldown: {DISTRIBUTE_COOLDOWN_SECONDS}s base, doubles on same consecutive action during {DISTRIBUTE_CHECKER_SECONDS}s checker (max {MAX_COOLDOWN_MULTIPLIER}x), resets on opposite action.", "usage": "action:<increase|decrease>", "example": "/distributepoints action:increase", "cooldown": f"{DISTRIBUTE_COOLDOWN_SECONDS}s base, complex rules apply."}
             # Add more commands here
         ]

    # --- Listener for Message Counting (Uses central manager) ---
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # Ignore bots, DMs, interactions, commands
        if message.author.bot or message.guild is None or message.interaction_metadata is not None: return
        if hasattr(self.bot, 'bot_prefix') and message.content.startswith(self.bot.bot_prefix):
             ctx = await self.bot.get_context(message);
             if ctx.valid: return # Is a command

        try:
             # +++ Call central manager +++
             point_added = await points_manager.increment_message_count(message.author.id, message.author.name)
             if point_added: self.logger.info(f"Point added for user {message.author.id} via msg count.") # Optional log
             # +++ Commented-out User Notification +++
                 # try:
                 #     guild_threshold = points_manager.messages_per_point_guild
                 #     new_total = await points_manager.get_points(message.author.id, message.author.name)
                 #     embed = discord.Embed(
                 #         title="👻 Point Earned!",
                 #         description=f"You sent {guild_threshold} messages in servers and earned **1** point! ✨\nYou now have **{new_total}** points.",
                 #         color=discord.Color.gold()
                 #     )
                 #     # Option 1: Send to channel (might be spammy)
                 #     # await message.channel.send(embed=embed, delete_after=30) # Example auto-delete
                 #     # Option 2: Send DM
                 #     await message.author.send(embed=embed)
                 # except discord.Forbidden:
                 #     self.logger.warning(f"Could not DM user {message.author.id} about point gain.")
                 # except Exception as e:
                 #     self.logger.error(f"Error sending point gain notification to {message.author.id}: {e}", exc_info=True)
                 # +++ End Commented-out Notification +++
        except Exception as e:
            self.logger.error(f"[AiCmd Cog] Error incrementing msg count for {message.author.id}: {e}", exc_info=True)

    # --- Commands ---

    @app_commands.command(name="aihelp", description="Get help with Hu Tao's AI commands.")
    async def aihelp(self, interaction: discord.Interaction) -> None:
        """Displays the interactive AI command help menu."""
        self.logger.info(f"[AiCmd Cog] AIHelp command used by {interaction.user}")
        view = AIHelpView(self.ai_commands_help)
        # Let view handle response, make it ephemeral
        await view.show_command_list(interaction)


    @app_commands.command(name = "stats", description = "Check your points and Hu Tao's points.")
    async def stats(self, interaction: discord.Interaction) -> None:
        """Checks your points and Hu Tao's points using central manager."""
        user_id = interaction.user.id
        username = interaction.user.name
        self.logger.info(f"[AiCmd Cog] Stats command used by {interaction.user}")
        try:
            # +++ Use central manager +++
            async with asyncio.TaskGroup() as tg:
                user_points_task = tg.create_task(points_manager.get_points(user_id, username))
                ai_points_task = tg.create_task(points_manager.get_ai_points())
                count_task = tg.create_task(points_manager.get_message_count(user_id, username))
            user_points = user_points_task.result()
            ai_points = ai_points_task.result()
            counts = count_task.result()
            guild_count = counts.get("guilfd_count", 0)
            dm_count = counts.get("dm_count", 0)
            # Access constant from manager instance
            guild_msgs_needed = points_manager.messages_per_point_guild - guild_count
            dm_msgs_needed = points_manager.messages_per_point_dm - dm_count

            embed = discord.Embed(title=f"📊 Point Stats for {interaction.user.display_name}", color=discord.Color.random())
            embed.add_field(name="Your Points", value=f"👻 You have **{user_points}** points.", inline=True)
            embed.add_field(name="Hu Tao's Points", value=f"🌸 Hu Tao has **{ai_points}** points.", inline=True)
            embed.add_field(name=f"Guild Msg Progress (/{points_manager.messages_per_point_guild})", value=f"💬 `{guild_count}` (`{guild_msgs_needed}` needed)", inline=False)
            embed.add_field(name=f"DM Msg Progress (/{points_manager.messages_per_point_dm})", value=f"💬 `{dm_count}` (`{dm_msgs_needed}` needed)", inline=False)
            embed.set_footer(text=f"Keep chatting to earn more points!")
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"[AiCmd Cog] Error in stats: {e}", exc_info=True)
            await interaction.response.send_message("❌ Sorry, couldn't fetch stats.", ephemeral=True)

    @app_commands.command(name="distributepoints", description="Give or take a point from Hu Tao (uses 1 of your points).")
    @app_commands.describe(action="Choose whether to increase or decrease Hu Tao's points.")
    async def distributepoints(self, interaction: discord.Interaction, action: Literal['increase', 'decrease']) -> None:
        """Handles point distribution with complex cooldown logic using central manager."""
        user_id = interaction.user.id
        username = interaction.user.name
        current_time = time.time()
        self.logger.info(f"[AiCmd Cog] DistributePoints by {interaction.user}, action: {action}")

        try:
            # +++ Use central manager for points and cooldowns +++
            user_points = await points_manager.get_points(user_id, username)
            cooldown_info = await points_manager.get_cooldown_data(user_id)

            # --- Check User Points ---
            if user_points < 1:
                await interaction.response.send_message(f"❌ Oops! You need at least **1 point** (have {user_points}).", ephemeral=True); return

            # --- Cooldown Check ---
            on_cooldown = False
            checker_active = False # Was the last cooldown finished, but within the 'checker' window?
            last_action = None
            current_multiplier = 1 # Base multiplier

            if cooldown_info: # Check if exists
                 expires_at = cooldown_info.get("expires", 0.0)
                 checker_expires_at = cooldown_info.get("checker_expires", 0.0)
                 if current_time < expires_at: on_cooldown = True; remaining_time = expires_at - current_time
                 elif current_time < checker_expires_at: checker_active = True
            if on_cooldown: await interaction.response.send_message(f"💨 Use again in **{format_time_delta(remaining_time)}**.", ephemeral=True); return

            # --- Calculate Next Cooldown Based on Rules ---
            next_multiplier = 1 # Default for next time unless changed
            cooldown_message = ""
            # Default checker window duration (e.g., 30 seconds after cooldown ends)
            last_action = cooldown_info.get("action") if cooldown_info else None
            current_multiplier = cooldown_info.get("multiplier", 1) if cooldown_info else 1
            next_checker_duration = DISTRIBUTE_CHECKER_SECONDS
            if checker_active and last_action == action:
                 next_multiplier = min(current_multiplier * 2, MAX_COOLDOWN_MULTIPLIER)
                 next_checker_duration = DISTRIBUTE_CHECKER_MAX_SECONDS
                 cooldown_message = f"\n\n⚠️ Consecutive action! Cooldown **{next_multiplier}x**."
            elif checker_active and last_action != action:
                 cooldown_message = "\n\n✨ Cooldown multiplier reset!"

            next_cooldown_duration = DISTRIBUTE_COOLDOWN_SECONDS * next_multiplier
            new_cooldown_expires = current_time + next_cooldown_duration
            new_checker_expires = new_cooldown_expires + next_checker_duration

            # --- Perform Point Transaction (Attempt) ---
            try:
                # Adjust points using the central manager
                await points_manager.adjust_points(user_id, username, -1) # Deduct user point
                new_ai_points = await points_manager.adjust_ai_points(1 if action == "increase" else -1) # Adjust AI points
            except Exception as point_error:
                self.logger.error(f"Point adjustment failed during distributepoints for {user_id}: {point_error}", exc_info=True)
                await interaction.response.send_message("❌ Error adjusting points. Please try again.", ephemeral=True)
                return # Exit early if points fail

            # --- Save New Cooldown State (Only if points succeeded) ---
            new_cooldown_info = {
                "action": action, # Store the action taken
                "expires": new_cooldown_expires,
                "multiplier": next_multiplier, # Store the multiplier applied THIS time
                "checker_expires": new_checker_expires # Store when the checker window ends
            }
            await points_manager.set_cooldown_data(user_id, new_cooldown_info)

            # --- Prepare and Send Response ---
            action_verb = "increased" if action == "increase" else "decreased"
            embed = discord.Embed(
                title="✅ Point Distributed!",
                description=f"You spent 1 point and **{action_verb}** Hu Tao's points by 1!\nHer new total is **{new_ai_points}** points.{cooldown_message}",
                color=discord.Color.green() if action == "increase" else discord.Color.orange()
            )
            embed.add_field(name="Cooldown Applied", value=f"Next use in: **{format_time_delta(next_cooldown_duration)}**.", inline=False)
            embed.set_footer(text=f"You now have {user_points - 1} points.") # Show updated points
            await interaction.response.send_message(embed=embed) # Public response

            self.logger.info(f"User {interaction.user} {action_verb} AI points. New AI: {new_ai_points}. User: {user_points - 1}. CD: {next_cooldown_duration}s (x{next_multiplier})")

            # --- AI Notification (Attempt) ---
            # (Keep the notification logic using bot.get_cog("DMHandler").inject_system_message)
            try:
                dm_handler_cog = self.bot.get_cog("DMHandler")
                if dm_handler_cog and hasattr(dm_handler_cog, 'trigger_ai_reaction'):
                    # Create the system message for the AI
                    system_message = f"[System Note: You just {'gained' if action == 'increase' else 'lost'} 1 Spirit Point! Your new total is {new_ai_points}.]"
                    # Trigger the reaction asynchronously
                    asyncio.create_task(dm_handler_cog.trigger_ai_reaction(user_id, username, system_message))
                    self.logger.info(f"Triggered AI reaction task for user {user_id} due to point change.")
                elif not dm_handler_cog:
                     self.logger.error("[AiCmd Cog] DMHandler cog not found for AI reaction!")
                else:
                     self.logger.error("[AiCmd Cog] DMHandler cog found, but trigger_ai_reaction method is missing!")
            except Exception as notify_error:
                self.logger.error(f"Failed to trigger AI reaction task for {user_id}: {notify_error}", exc_info=True)
            

        except Exception as e:
            self.logger.error(f"[AiCmd Cog] Error in distributepoints for {user_id}: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An unexpected error occurred.", ephemeral=True)
            else: await interaction.followup.send("❌ An unexpected error occurred after processing.", ephemeral=True)


    # --- --- --- COMMENTED OUT: Alternative /distributepoints using Buttons --- --- ---
    # (Keep the commented out button code block here if you still want it for reference)
    # --- --- --- END OF COMMENTED OUT CODE --- --- ---
    


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AiCommands(bot))

# --- END OF assets/commands/aicommands.py ---


