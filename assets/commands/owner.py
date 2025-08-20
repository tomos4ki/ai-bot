# --- START OF assets/commands/owner.py ---

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
import traceback
import json
import os
import asyncio
import logging
from typing import Dict, Optional, Literal
import time


from assets.points_manager import points_manager
import assets.guild_auth as guild_auth
class Owner(commands.Cog, name="owner"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.logger = bot.logger

    @commands.command(
        #Global sync can take up to an hour to propagate, while guild sync is instant
        name="sync",
        description="Synchonizes the slash commands.",
    )
    @app_commands.describe(scope="The scope of the sync. Can be `global` or `guild`")
    @commands.is_owner()
    async def sync(self, context: Context, scope: str) -> None:
        """
        Synchonizes the slash commands.
        
        :param context: The command context.
        :param scope: The scope of the sync. Can be `global` or `guild`.
        """


        try:
            if scope == "global":
                await context.bot.tree.sync()
                embed = discord.Embed(
                    description="Slash commands have been globally synchronized.",
                    color=0xBEBEFE,
                )
                await context.send(embed=embed)
                return
            elif scope == "guild":
                if context.guild is None:
                    embed = discord.Embed(
                        description="This command can only be used in a guild.",
                        color=0xE02B2B,
                    )
                    await context.send(embed=embed)
                    return
                context.bot.tree.copy_global_to(guild=context.guild)
                await context.bot.tree.sync(guild=context.guild)
                embed = discord.Embed(
                    description="Slash commands have been synchronized in this guild.",
                    color=0xBEBEFE,
                )
                await context.send(embed=embed)
                return
            embed = discord.Embed(
                description="The scope must be `global` or `guild`.", 
                color=0xE02B2B
            )
            await context.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"An error occurred while synchronizing the commands: {e}",
                color=discord.Color.red(),
            )
            await context.send(embed=embed)
    @commands.command(
        name="unsync",
        description="Unsynchonizes the slash commands.",
    )
    @app_commands.describe(
        scope="The scope of the sync. Can be `global`, `current_guild` or `guild`"
    )
    @commands.is_owner()
    async def unsync(self, context: Context, scope: str) -> None:
        """
        Unsynchonizes the slash commands.
        
        :param context: The command context.
        :param scope: The scope of the sync. Can be `global`, `current_guild` or `guild`.
        """
        if scope == "global":
            context.bot.tree.clear_commands(guild=None)
            await context.bot.tree.sync()
            embed = discord.Embed(
                description="Slash commands have been globally unsynchronized.",
                color=0xBEBEFE,
            )
            await context.send(embed=embed)
            return
        elif scope == "guild":
            context.bot.tree.clear_commands(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            embed = discord.Embed(
                description="Slash commands have been unsynchronized in this guild.",
                color=0xBEBEFE,
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description="The scope must be `global`, `current_guild` or `guild`.",
            color=0xE02B2B,
        )
        await context.send(embed=embed)
    @commands.hybrid_command(
        name="load",
        description="loads a cog"
    )
    @app_commands.describe(cog="The name of the cog to load")
    @commands.is_owner()
    async def load(self, context: Context, cog: str) -> None:
        """
        Loads a cog.

        :param context: The command context.
        :param cog: The name of the cog to load.
        """
        try:
            # Example: If cogs are in assets/commands/
            await self.bot.load_extension(f"assets.commands.{cog}")
            # Example: If cogs are directly in assets/
            # await self.bot.load_extension(f"assets.{cog}")
            # Choose the correct path based on your structure!
        except Exception:
            embed = discord.Embed(
                description=f"Could not load the `{cog}` cog.",
                color=0xE02B2B,
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description=f"Successfully loaded the `{cog}` cog.",
            color=0xBEBEFE,
        )
        await context.send(embed=embed)
    
    # -------------------------------------  *** Need to make these commans *** -----------------------------------------------------
    # @commands.hybrid_command(name="unload", ...)
    # async def unload(self, context: Context, cog: str) -> None: ... # Keep implementation

    # @commands.hybrid_command(name="reload", ...)
    # async def reload(self, context: Context, cog: str) -> None: ... # Keep implementation

    # --- +++ Add the adjustpoints command (uses central manager) +++ ---
    @commands.hybrid_command(
        name="adjustpoints",
        description="Owner Only: Adjusts points for a user or the AI.",
        with_app_command=True
    )
    @app_commands.describe(
        target="The user to adjust points for, or type 'AI' for the bot.",
        amount="The amount to adjust points by (can be negative)."
    )
    @commands.is_owner()
    async def adjustpoints(self, context: Context, target: str, amount: int) -> None:
        """Adjusts points for a user or the AI. Owner only."""
        target_user = Optional[discord.User]
        target_name = "AI"
        is_ai = False

        if target.upper() == "AI":
            is_ai = True
        else: # Try to resolve user
            try: target_user = await commands.MemberConverter().convert(context, target)#; target_name = target_user.mention
            except commands.UserNotFound: await context.send(f"❌ Error: Could not find user '{target}'.", ephemeral=True); return
            target_name = target_user.mention if isinstance(target_user, discord.Member) else f"{target_user.name}#{target_user.discriminator}"

        try:
            if is_ai:
                # +++ Call central manager +++
                new_total = await points_manager.adjust_ai_points(amount)
                log_target = "AI"
            elif target_user:
                # +++ Call central manager +++
                new_total = await points_manager.adjust_points(target_user.id, target_user.name, amount)
                log_target = f"{target_user} ({target_user.id})"
            else: await context.send("❌ Error: Invalid target.", ephemeral=True); return # Should not happen

            self.logger.info(f"Owner {context.author} adjusted points for {log_target} by {amount}. New total: {new_total}")
            embed = discord.Embed(title="✅ Points Adjusted", description=f"Successfully adjusted points for **{target_name}** by `{amount}`.\nNew total: `{new_total}` points.", color=discord.Color.green() if amount >= 0 else discord.Color.orange())
            await context.send(embed=embed)

        except Exception as e:
            self.logger.error(f"[Owner Cog] Error in adjustpoints: {e}", exc_info=True)
            embed = discord.Embed(title="❌ Error Adjusting Points", description=f"{e}", color=discord.Color.red())
            await context.send(embed=embed, ephemeral=True)

    @commands.hybrid_command(
        name= "managecooldown",
        description= "Owner Only : manage cooldowns for a user."
    )
    @app_commands.describe(
        target= "The user to manage cooldown for.",
        action= "Choose action: 'remove' or 'set'.",
        duration_seconds= "Duration in seconds if action is 'set' (default 0)."
    )
    @commands.is_owner()
    async def managecooldown(self, context: Context, target: discord.User, action: Literal['remove', 'set'], duration_seconds: int = 0) -> None: # Correct type hint
        """Manages distributepoints cooldowns for a user using central manager."""
        user_id = target.id # Get user ID correctly
        self.logger.info(f"ManageCooldown triggered by {context.author} for {target} ({user_id}). Action: {action}, Duration: {duration_seconds}")

        try:
            action_desc = ""
            if action == 'remove':
                await points_manager.remove_cooldown_data(user_id) # Use manager
                action_desc = "removed"
            elif action == 'set':
                if duration_seconds <= 0:
                    await context.send("❌ Duration must be positive seconds to set a cooldown.", ephemeral=True); return
                current_time = time.time()
                new_cooldown_info = {
                    "action": "manual_set",
                    "expires": current_time + duration_seconds,
                    "multiplier": 1, # Reset multiplier
                    "checker_expires": current_time + duration_seconds + 30 # Standard checker window
                }
                await points_manager.set_cooldown_data(user_id, new_cooldown_info) # Use manager
                action_desc = f"set to {duration_seconds} seconds"
            else:
                await context.send("❌ Invalid action. Use 'remove' or 'set'.", ephemeral=True); return

            embed = discord.Embed(title="✅ Cooldown Managed", description=f"Cooldown for {target.mention} has been {action_desc}.", color=discord.Color.green())
            await context.send(embed=embed)

        except Exception as e:
            self.logger.error(f"[Owner Cog] Error in managecooldown: {e}", exc_info=True)
            embed = discord.Embed(title="❌ Error Managing Cooldown", description=f"{e}", color=discord.Color.red())
            # Fix typo: context.send, not interaction.responce
            await context.send(embed=embed, ephemeral=True)
    
    @commands.hybrid_command(name="setpointthresholds", description="Owner Only: Sets messages needed per point.")
    @app_commands.describe(
        scope="Which message counter threshold to set ('guild' or 'dm').",
        value="The number of messages required to earn 1 point (must be > 0)."
    )
    @commands.is_owner()
    async def setpointthresholds(self, context: Context, scope: Literal['guild', 'dm'], value: int):
        """Sets the number of messages needed to earn a point."""
        self.logger.info(f"SetPointThresholds triggered by {context.author}. Scope: {scope}, Value: {value}")
        if value <= 0:
            await context.send("❌ Threshold value must be a positive number.", ephemeral=True)
            return

        try:
            success = await points_manager.set_threshold(scope, value)
            if success:
                embed = discord.Embed(title="✅ Threshold Updated", description=f"The threshold for `{scope}` messages has been set to **{value}** messages per point.", color=discord.Color.green())
                await context.send(embed=embed)
            else: # Should be caught by validation, but just in case
                 await context.send("❌ Failed to set threshold (check logs).", ephemeral=True)

        except Exception as e:
            self.logger.error(f"[Owner Cog] Error in setpointthresholds: {e}", exc_info=True)
            embed = discord.Embed(title="❌ Error Setting Threshold", description=f"{e}", color=discord.Color.red())
            await context.send(embed=embed, ephemeral=True)
    @commands.hybrid_command(name="unload", description="Unloads a cog extension.")
    @app_commands.describe(cog="The path of the extension to unload (e.g., `assets.commands.general`)")
    @commands.is_owner()
    async def unload(self, context: Context, cog: str) -> None:
        """Unloads a cog extension. Use the full Python path."""
        self.logger.info(f"Unload attempt for '{cog}' by {context.author}.")
        # Example path check:
        if cog == "assets.commands.owner":
            await context.send("❌ Cannot unload the owner cog.", ephemeral=True); return
        try:
            await self.bot.unload_extension(cog) # Use full path like assets.commands.general
            embed = discord.Embed(title="✅ Unload Extension", description=f"`{cog}` unloaded.", color=0xBEBEFE)
            await context.send(embed=embed)
            self.logger.info(f"Unloaded extension '{cog}'")
        except commands.ExtensionNotLoaded:
            embed = discord.Embed(title="⚠️ Unload Error", description=f"`{cog}` is not loaded.", color=0xFFCC00)
            await context.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title="❌ Unload Error", description=f"Error unloading `{cog}`:\n```py\n{e}\n```", color=0xE02B2B)
            await context.send(embed=embed); self.logger.error(f"Failed to unload {cog}:", exc_info=True)

    @commands.hybrid_command(name="reload", description="Reloads a cog extension.")
    @app_commands.describe(cog="The path of the extension to reload (e.g., `assets.commands.general`)")
    @commands.is_owner()
    async def reload(self, context: Context, cog: str) -> None:
        """Reloads a cog extension. Use the full Python path."""
        self.logger.info(f"Reload attempt for '{cog}' by {context.author}.")
        try:
            await self.bot.reload_extension(cog) # Use full path like assets.commands.general
            embed = discord.Embed(title="✅ Reload Extension", description=f"`{cog}` reloaded.", color=0xBEBEFE)
            await context.send(embed=embed)
            self.logger.info(f"Reloaded extension '{cog}'")
        except commands.ExtensionNotLoaded:
            embed = discord.Embed(title="⚠️ Reload Error", description=f"`{cog}` not loaded. Use `load` first.", color=0xFFCC00)
            await context.send(embed=embed, ephemeral=True)
        except commands.ExtensionNotFound:
            embed = discord.Embed(title="❌ Reload Error", description=f"Extension `{cog}` not found.", color=0xE02B2B)
            await context.send(embed=embed, ephemeral=True)
        except Exception as e:
            embed = discord.Embed(title="❌ Reload Error", description=f"Error reloading `{cog}`:\n```py\n{e}\n```", color=0xE02B2B)
            await context.send(embed=embed); self.logger.error(f"Failed to reload {cog}:", exc_info=True)

    musicguild_group = app_commands.Group(name="musicguild", description="Owner Only: Manage guilds authorized for music commands.")

    @musicguild_group.command(name="add", description="Authorize a guild to use music commands.")
    @app_commands.describe(guild_id="The ID of the guild to authorize.")
    @commands.is_owner()
    async def musicguild_add(self, interaction: discord.Interaction, guild_id: str):
        try:
            gid = int(guild_id)
        except ValueError:
            await interaction.response.send_message("❌ Invalid Guild ID format. Please provide numbers only.", ephemeral=True)
            return

        guild = self.bot.get_guild(gid) # Try to get guild name for confirmation
        guild_name = f" ({guild.name})" if guild else ""

        try:
            added = await guild_auth.add_authorized_guild(gid)
            if added:
                embed = discord.Embed(title="✅ Music Guild Authorized", description=f"Guild ` {gid} `{guild_name} can now use music commands.", color=discord.Color.green())
                await interaction.response.send_message(embed=embed)
                self.logger.info(f"Owner {interaction.user} authorized music guild: {gid}{guild_name}")
            else:
                embed = discord.Embed(title="ℹ️ Music Guild Info", description=f"Guild ` {gid} `{guild_name} is already authorized.", color=discord.Color.blue())
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error adding music guild {gid}: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ An error occurred while adding guild {gid}.", ephemeral=True)


    @musicguild_group.command(name="remove", description="Deauthorize a guild from using music commands.")
    @app_commands.describe(guild_id="The ID of the guild to deauthorize.")
    @commands.is_owner()
    async def musicguild_remove(self, interaction: discord.Interaction, guild_id: str):
        try:
            gid = int(guild_id)
        except ValueError:
            await interaction.response.send_message("❌ Invalid Guild ID format.", ephemeral=True)
            return

        guild = self.bot.get_guild(gid)
        guild_name = f" ({guild.name})" if guild else ""

        try:
            removed = await guild_auth.remove_authorized_guild(gid)
            if removed:
                embed = discord.Embed(title="✅ Music Guild Deauthorized", description=f"Guild ` {gid} `{guild_name} can no longer use music commands.", color=discord.Color.orange())
                await interaction.response.send_message(embed=embed)
                self.logger.info(f"Owner {interaction.user} deauthorized music guild: {gid}{guild_name}")
            else:
                embed = discord.Embed(title="ℹ️ Music Guild Info", description=f"Guild ` {gid} `{guild_name} was not found in the authorized list.", color=discord.Color.blue())
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            self.logger.error(f"Error removing music guild {gid}: {e}", exc_info=True)
            await interaction.response.send_message(f"❌ An error occurred while removing guild {gid}.", ephemeral=True)


    @musicguild_group.command(name="list", description="Lists guilds authorized to use music commands.")
    @commands.is_owner()
    async def musicguild_list(self, interaction: discord.Interaction):
        try:
            guild_ids = await guild_auth.get_authorized_guilds()
            if not guild_ids:
                await interaction.response.send_message("ℹ️ No guilds are currently authorized for music commands.", ephemeral=True)
                return

            description = "Guilds authorized for music commands:\n"
            for gid in guild_ids:
                guild = self.bot.get_guild(gid)
                guild_name = guild.name if guild else "Unknown (Bot not in Guild?)"
                description += f"- `{gid}` : {guild_name}\n"

            embed = discord.Embed(title="🎶 Authorized Music Guilds", description=description, color=discord.Color.purple())
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except Exception as e:
            self.logger.error(f"Error listing music guilds: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while listing guilds.", ephemeral=True)
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Owner(bot))
    


# --- END OF assets/commands/owner.py ---