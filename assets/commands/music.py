# --- START OF assets/commands/music.py ---
import discord
from discord import app_commands, ui
from discord.ext import commands, tasks
from discord.ext.commands import Context
import asyncio
from datetime import datetime, timedelta # Keep timedelta for duration formatting
import yt_dlp
import logging
from typing import Dict, Optional, List, Literal, Any
import assets.guild_auth as guild_auth # Import authorization helper


# --- Constants ---
FFMPEG_PATH = "ffmpeg" # Change if not in PATH
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn -loglevel quiet'}
# Use YDL options compatible with directly feeding to FFmpegOpusAudio if possible
YDL_OPTIONS = {
    'format': 'bestaudio/best', # Get best audio stream URL
    'extractaudio': True,
    'audioformat': 'best', # Let FFmpeg handle format needed for Opus
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    # Don't need outtmpl if not downloading
    # 'outtmpl': 'downloads/%(extractor)s-%(id)s-%(title)s.%(ext)s'
}
INACTIVITY_TIMEOUT = 300.0 # 5 minutes

# --- Player State Class ---
class GuildPlayerState:
    def __init__(self, guild_id: int, logger: logging.Logger, bot: commands.Bot):
        self.guild_id = guild_id
        self.logger = logger
        self.bot = bot
        self.queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
        self.voice_client: Optional[discord.VoiceClient] = None
        self.current_song: Optional[Dict[str, Any]] = None
        self.loop_mode: Literal['off', 'song', 'queue'] = 'off'
        self.player_task: Optional[asyncio.Task] = None
        self.now_playing_message: Optional[discord.Message] = None
        self.last_activity_time = asyncio.get_event_loop().time()

    def is_playing_or_pending(self) -> bool:
        """Check if player is active or has items queued."""
        vc = self.voice_client
        # Check voice client exists and is playing OR queue is not empty OR current song is set (about to play)
        return (vc and vc.is_playing()) or not self.queue.empty() or self.current_song is not None

    def _schedule_next_song(self, error=None):
        """Callback function for vc.play(after=...). Schedules the next song."""
        if error:
            self.logger.error(f"Player 'after' callback error in guild {self.guild_id}: {error}", exc_info=error)
            # Consider sending error message via run_coroutine_threadsafe
            # coro = self.send_channel_message(f"❌ Player error: {error}")
            # asyncio.run_coroutine_threadsafe(coro, self.bot.loop)

        current_song_finished = self.current_song
        self.current_song = None # Mark current as finished

        # Safely schedule the async task from the synchronous callback context
        self.player_task = asyncio.create_task(self._play_next_from_queue(current_song_finished))
        self.logger.debug(f"Guild {self.guild_id}: Scheduled next song check via _schedule_next_song.")


    async def _play_next_from_queue(self, last_song: Optional[Dict[str, Any]] = None):
        """Internal async method to handle fetching and playing the next song."""
        self.logger.debug(f"Guild {self.guild_id}: _play_next_from_queue entered.")

        if not self.voice_client or not self.voice_client.is_connected():
            self.logger.warning(f"Guild {self.guild_id}: Player disconnected, cleaning up in _play_next.")
            await self.cleanup()
            return

        next_item = None
        try:
            # --- Handle Looping ---
            if self.loop_mode == 'song' and last_song:
                self.logger.info(f"Guild {self.guild_id}: Looping song: {last_song.get('title')}")
                next_item = last_song
            elif self.loop_mode == 'queue' and last_song:
                 self.logger.info(f"Guild {self.guild_id}: Re-adding to queue: {last_song.get('title')}")
                 await self.queue.put(last_song)
                 # Fall through to get next item
            # else: Loop off or no previous song

            # --- Get Item From Queue (if not looping song) ---
            if next_item is None:
                 if self.queue.empty():
                     self.logger.info(f"Guild {self.guild_id}: Queue is empty. Starting inactivity timer.")
                     await asyncio.sleep(INACTIVITY_TIMEOUT)
                     if not self.is_playing_or_pending() and self.voice_client and self.voice_client.is_connected():
                         self.logger.info(f"Guild {self.guild_id}: Inactivity timeout reached. Cleaning up.")
                         await self.cleanup()
                     else:
                         self.logger.info(f"Guild {self.guild_id}: Player became active during timeout or disconnected. Aborting timeout action.")
                     return # Stop this task iteration
                 else:
                     self.logger.debug(f"Guild {self.guild_id}: Waiting for queue item...")
                     next_item = await self.queue.get()
                     self.logger.debug(f"Guild {self.guild_id}: Got item from queue: {next_item.get('title')}")

            if not next_item:
                 self.logger.warning(f"Guild {self.guild_id}: Next item became None. Stopping player.")
                 await self.cleanup()
                 return

            # --- Play the song ---
            self.current_song = next_item
            title = self.current_song.get('title', 'Unknown Title')
            url = self.current_song.get('url') # This should be the direct stream URL from yt-dlp

            if not url:
                self.logger.error(f"Guild {self.guild_id}: Missing stream URL for '{title}'. Skipping.")
                if not self.queue.empty(): self.queue.task_done() # Mark done if skipping
                self.current_song = None
                self.player_task = asyncio.create_task(self._play_next_from_queue()) # Try next immediately
                return

            try:
                # +++ WORKAROUND: Use FFmpegOpusAudio constructor +++
                self.logger.debug(f"Guild {self.guild_id}: Creating FFmpegOpusAudio source for '{title}'")
                source = discord.FFmpegOpusAudio(url, executable=FFMPEG_PATH, before_options=FFMPEG_OPTIONS.get('before_options'), options=FFMPEG_OPTIONS.get('options'))
                self.logger.debug(f"Guild {self.guild_id}: FFmpegOpusAudio source created for '{title}'.")

                if not self.voice_client or not self.voice_client.is_connected():
                     self.logger.warning(f"Guild {self.guild_id}: Disconnected before play could start.")
                     await self.cleanup()
                     return

                self.logger.debug(f"Guild {self.guild_id}: Calling voice_client.play() for '{title}'.")
                self.voice_client.play(source, after=self._schedule_next_song)
                self.logger.info(f"Guild {self.guild_id}: Now Playing '{title}' (play() called).")
                self.last_activity_time = asyncio.get_event_loop().time()
                await self.update_now_playing_message()

            except discord.ClientException as e:
                 self.logger.error(f"Guild {self.guild_id}: discord.ClientException during play setup for '{title}': {e}", exc_info=True)
                 await self.send_channel_message(f"⚠️ Error setting up play for '{title}'. Already playing?")
                 if not self.queue.empty(): self.queue.task_done()
                 self.current_song = None
                 self.player_task = asyncio.create_task(self._play_next_from_queue())
            except Exception as e:
                 self.logger.error(f"Guild {self.guild_id}: Error creating/playing source for '{title}': {e}", exc_info=True)
                 await self.send_channel_message(f"❌ Error playing '{title}'. Skipping...")
                 if not self.queue.empty(): self.queue.task_done()
                 self.current_song = None
                 self.player_task = asyncio.create_task(self._play_next_from_queue())

        except asyncio.CancelledError:
             self.logger.info(f"Player task cancelled cleanly for guild {self.guild_id}")
             # Don't mark task done here, item wasn't processed
        except Exception as e:
            self.logger.error(f"Guild {self.guild_id}: Unexpected error in _play_next_from_queue: {e}", exc_info=True)
            await self.cleanup() # Cleanup on major loop errors
        # Removed finally block, task_done handled within try/except for skips


    async def start_player_task(self):
        """Starts the player task if not already running."""
        if self.player_task and not self.player_task.done():
            self.logger.warning(f"Guild {self.guild_id}: start_player_task called but task already running.")
            return

        self.logger.info(f"Guild {self.guild_id}: Starting player task via start_player_task.")
        self.player_task = asyncio.create_task(self._play_next_from_queue())

    async def cleanup(self):
        """Stops player, cancels tasks, disconnects voice, removes state, clears UI."""
        guild_id = self.guild_id # Store before potentially deleting self
        self.logger.info(f"Cleaning up player for guild {guild_id}")
        # ... (cancel task, stop vc, disconnect vc - keep this logic) ...
        if self.player_task and not self.player_task.done(): self.player_task.cancel()
        self.player_task = None
        vc = self.voice_client
        self.voice_client = None # Clear reference
        if vc:
            if vc.is_playing(): vc.stop()
            if vc.is_connected(): await vc.disconnect(force=True)

        self.current_song = None
        self.queue = asyncio.Queue() # Reset queue

        # --- Edit message to remove controls and show stopped state ---
        if self.now_playing_message:
            try:
                 # Update embed to show stopped state
                 stopped_embed = discord.Embed(description="⏹️ Playback stopped. Queue cleared.", color=discord.Color.greyple())
                 await self.now_playing_message.edit(embed=stopped_embed, view=None) # Remove view
            except discord.NotFound: pass
            except Exception as e: self.logger.error(f"Error editing NP message on cleanup: {e}")
        self.now_playing_message = None
        # --- End Edit message ---

        # Remove self from parent cog's dictionary
        music_cog = self.bot.get_cog("Music")
        if music_cog and guild_id in music_cog.players:
             del music_cog.players[guild_id]
             self.logger.info(f"Removed player state for guild {guild_id}")


    async def update_now_playing_message(self, channel: Optional[discord.TextChannel] = None):
        """Creates or edits the Now Playing message, adding controls."""
        vc = self.voice_client
        # Only show controls if connected and either playing, paused, or something in queue
        show_controls = vc and vc.is_connected() and (vc.is_playing() or vc.is_paused() or not self.queue.empty())

        # Try to get channel if not provided
        current_channel = channel or (self.now_playing_message.channel if self.now_playing_message else None)
        if not current_channel:
            self.logger.warning(f"Cannot update NP message for guild {self.guild_id}: No channel.")
            return

        embed = self.create_now_playing_embed()
        view = MusicControlsView(self) if show_controls else None # Create view only if needed

        try:
            if self.now_playing_message:
                await self.now_playing_message.edit(embed=embed, view=view)
            else: # Send new message
                 self.now_playing_message = await current_channel.send(embed=embed, view=view)
        except discord.NotFound:
            self.logger.warning(f"NP message {self.now_playing_message.id if self.now_playing_message else 'N/A'} for guild {self.guild_id} not found, sending new one.")
            self.now_playing_message = None # Clear invalid reference
            try:
                 self.now_playing_message = await current_channel.send(embed=embed, view=view)
            except Exception as e: self.logger.error(f"Failed to send new NP message to {current_channel.id}: {e}")
        except Exception as e:
            self.logger.error(f"Failed to edit/send NP message for guild {self.guild_id}: {e}")


    def create_now_playing_embed(self) -> discord.Embed:
        """Helper to build the Now Playing embed."""
        if not self.current_song: return discord.Embed(description="⏹️ Nothing currently playing.")

        title = self.current_song.get('title', 'Unknown Title')
        url = self.current_song.get('webpage_url', None)
        duration_sec = self.current_song.get('duration', 0)
        duration_fmt = str(timedelta(seconds=int(duration_sec))) if duration_sec else "N/A"
        requester = self.current_song.get('requester', 'Unknown')
        thumbnail = self.current_song.get('thumbnail', None)
        q_size = self.queue.qsize()

        embed = discord.Embed(title="🎶 Now Playing", color=discord.Color.blurple())
        embed.description = f"**[{title}]({url})**" if url else f"**{title}**"
        embed.add_field(name="Duration", value=duration_fmt, inline=True)
        embed.add_field(name="Requested by", value=requester, inline=True)
        embed.add_field(name="Queue", value=f"{q_size} song{'s' if q_size != 1 else ''}", inline=True)
        # TODO: Add Loop status, Volume etc. fields here
        if thumbnail: embed.set_thumbnail(url=thumbnail)

        return embed

    async def send_channel_message(self, message: str, channel: Optional[discord.TextChannel] = None):
        """Sends a message to the channel of the NP message or a specified channel."""
        target_channel = channel or (self.now_playing_message.channel if self.now_playing_message else None)
        if target_channel:
            try: await target_channel.send(message, delete_after=15)
            except Exception as e: self.logger.error(f"Failed to send message to channel {target_channel.id}: {e}")


# +++music ui class +++
class MusicControlsView(ui.View):
    def __init__(self, player_state: GuildPlayerState, timeout=None): # Timeout=None for persistent view
        super().__init__(timeout=timeout)
        self.player_state = player_state
        self._update_buttons() # Initial button state

    def _update_buttons(self):
        """Enable/disable buttons based on player state."""
        vc = self.player_state.voice_client
        is_playing = vc and vc.is_playing()
        is_paused = vc and vc.is_paused()
        is_queue_empty = self.player_state.queue.empty()

        # Find buttons by custom_id (more robust than order)
        pause_resume_button = discord.utils.get(self.children, custom_id="music_pause_resume")
        skip_button = discord.utils.get(self.children, custom_id="music_skip")
        stop_button = discord.utils.get(self.children, custom_id="music_stop")

        if pause_resume_button:
            pause_resume_button.label = "Resume" if is_paused else "Pause"
            pause_resume_button.emoji = "▶️" if is_paused else "⏸️"
            pause_resume_button.disabled = not (is_playing or is_paused) # Disable if stopped
            pause_resume_button.style = discord.ButtonStyle.primary

        if skip_button:
            skip_button.disabled = not is_playing # Disable skip if not playing (or maybe allow skip if paused?)
            # Could also disable if queue is empty and not looping song
            # skip_button.disabled = not (is_playing or is_paused) or (is_queue_empty and self.player_state.loop_mode != 'song')

        if stop_button:
            stop_button.disabled = not (is_playing or is_paused) # Disable stop if already stopped

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if the user interacting is in the same channel."""
        # Allow anyone in the same VC to use controls? Or only requester?
        # For simplicity, allow anyone in the channel.
        if not interaction.user.voice or not interaction.user.voice.channel:
             await interaction.response.send_message("You need to be in a voice channel to use controls.", ephemeral=True)
             return False
        if self.player_state.voice_client and interaction.user.voice.channel == self.player_state.voice_client.channel:
            return True
        else:
            await interaction.response.send_message("You need to be in the same voice channel as the bot.", ephemeral=True)
            return False

    @ui.button(label="Pause", emoji="⏸️", style=discord.ButtonStyle.primary, custom_id="music_pause_resume")
    async def pause_resume(self, interaction: discord.Interaction, button: ui.Button):
        vc = self.player_state.voice_client
        if not vc: return # Should not happen if check passes

        if vc.is_paused():
            vc.resume()
            await interaction.response.send_message("Resumed playback.", ephemeral=True)
            self.player_state.logger.info(f"Guild {self.player_state.guild_id}: Playback resumed by {interaction.user}")
        elif vc.is_playing():
            vc.pause()
            await interaction.response.send_message("Paused playback.", ephemeral=True)
            self.player_state.logger.info(f"Guild {self.player_state.guild_id}: Playback paused by {interaction.user}")
        # else: ignore if stopped

        self._update_buttons()
        await interaction.message.edit(view=self) # Update button labels/state
        # Also update the main embed if needed (e.g., add Paused status)
        await self.player_state.update_now_playing_message()


    @ui.button(label="Skip", emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="music_skip")
    async def skip(self, interaction: discord.Interaction, button: ui.Button):
        vc = self.player_state.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            await interaction.response.send_message("Skipping song...", ephemeral=True)
            self.player_state.logger.info(f"Guild {self.player_state.guild_id}: Song skipped by {interaction.user}")
            vc.stop() # Stopping triggers the 'after' callback (_schedule_next_song)
            # _schedule_next_song will handle playing the next item
        else:
            await interaction.response.send_message("Nothing to skip.", ephemeral=True)

        # Buttons will update automatically when next track starts or playback stops

    @ui.button(label="Stop", emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="music_stop")
    async def stop(self, interaction: discord.Interaction, button: ui.Button):
        vc = self.player_state.voice_client
        if vc and vc.is_connected():
            await interaction.response.send_message("Stopping playback and leaving channel...", ephemeral=True)
            self.player_state.logger.info(f"Guild {self.player_state.guild_id}: Stop requested by {interaction.user}")
            # Cleanup handles stopping, disconnecting, clearing queue, updating message
            await self.player_state.cleanup()
        else:
             await interaction.response.send_message("Not connected.", ephemeral=True)

        # Disable buttons on the view after stopping
        for item in self.children:
             if isinstance(item, discord.ui.Button): item.disabled = True
        try: await interaction.message.edit(view=self)
        except: pass # Ignore if message deleted
        self.stop() # Stop the view itself

    # TODO: Add loop button, maybe queue button


# --- Music Cog ---
class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = bot.logger
        self.players: Dict[int, GuildPlayerState] = {} # Store state per guild

    def get_player(self, interaction: discord.Interaction) -> Optional[GuildPlayerState]:
        """Gets or creates the player state for the interaction's guild."""
        if not interaction.guild_id:
            self.logger.error("get_player called without guild_id in interaction.")
            return None
        if interaction.guild_id not in self.players:
            self.logger.info(f"Creating new GuildPlayerState for guild {interaction.guild_id}")
            self.players[interaction.guild_id] = GuildPlayerState(interaction.guild_id, self.logger, self.bot)
        return self.players[interaction.guild_id]

    async def cog_check(self, ctx: Context) -> bool:
        """Global check for all commands in this cog."""
        # Convert Context to Interaction if needed for get_player, or adapt get_player
        # For slash commands, interaction is usually available directly
        interaction : Optional[discord.Interaction] = None
        if hasattr(ctx, 'interaction') and ctx.interaction:
             interaction = ctx.interaction
        elif isinstance(ctx, discord.Interaction): # If invoked via slash directly
             interaction = ctx

        # Use interaction if available, otherwise fallback to ctx (might fail if no guild)
        target = interaction or ctx

        if not target.guild:
            # For message commands, ctx.guild is needed
            if isinstance(ctx, commands.Context) and not ctx.guild:
                raise commands.NoPrivateMessage("Music commands only work in servers.")
            # For interactions, target.guild might be None if invoked weirdly, handle it
            elif not target.guild:
                 self.logger.warning("Music cog check failed: No guild context found.")
                 raise commands.CommandError("Could not determine server context.")


        if not await guild_auth.is_guild_authorized(target.guild.id):
             self.logger.warning(f"Unauthorized music command use attempt in guild {target.guild.id} by {target.user}")
             # Raise specific error for slash commands if possible
             if interaction:
                  # await interaction.response.send_message("❌ This server is not authorized to use music commands.", ephemeral=True) # Cannot respond in check
                  # Return False or raise CheckFailure
                  raise commands.CheckFailure("Server not authorized.")
             else:
                 raise commands.CheckFailure("❌ This server is not authorized to use music commands. Ask the bot owner.")
        return True

    async def cog_unload(self):
        """Cleanup players when cog unloads."""
        self.logger.info("Music cog unloading...")
        # Create tasks for cleanup to avoid blocking unload
        cleanup_tasks = [player_state.cleanup() for player_state in self.players.values()]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True) # Run cleanups concurrently
        self.players.clear()
        self.logger.info("Music cog unloaded.")

    # --- Commands ---

    @app_commands.command(name="join", description="Joins your current voice channel.")
    async def join(self, interaction: discord.Interaction):
        """Joins the invoker's voice channel."""
        # Cog check already verified guild exists
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("❌ You need to be in a voice channel.", ephemeral=True); return

        player_state = self.get_player(interaction)
        if not player_state: await interaction.response.send_message("❌ Error getting player state.", ephemeral=True); return # Should not happen

        channel = interaction.user.voice.channel

        vc = player_state.voice_client
        if vc and vc.is_connected():
            if vc.channel == channel:
                 await interaction.response.send_message("✅ Already here!", ephemeral=True); return
            else:
                 try:
                     await vc.move_to(channel)
                     await interaction.response.send_message(f"✅ Moved to {channel.mention}.", ephemeral=True); return
                 except Exception as e:
                      self.logger.error(f"Error moving VC in guild {interaction.guild_id}: {e}")
                      await interaction.response.send_message("❌ Error moving voice channel.", ephemeral=True); return
        try:
            player_state.voice_client = await channel.connect() # timeout parameter optional
            await interaction.response.send_message(f"✅ Joined {channel.mention}!", ephemeral=True)
            self.logger.info(f"Joined VC {channel.id} in guild {interaction.guild_id}")
        except asyncio.TimeoutError:
             await interaction.response.send_message("❌ Connection attempt timed out.", ephemeral=True)
        except discord.ClientException as e: # Already connected?
             await interaction.response.send_message(f"❌ Client Exception: {e}", ephemeral=True)
        except Exception as e:
            self.logger.error(f"Failed joining VC {channel.id}: {e}", exc_info=True)
            await interaction.response.send_message("❌ Failed to join channel.", ephemeral=True)

    @app_commands.command(name="leave", description="Leaves the voice channel and clears the queue.")
    async def leave(self, interaction: discord.Interaction):
        """Disconnects the bot and cleans up."""
        player_state = self.get_player(interaction)
        if not player_state or not player_state.voice_client or not player_state.voice_client.is_connected():
             await interaction.response.send_message("❌ Not in a voice channel.", ephemeral=True); return

        self.logger.info(f"Leave command initiated in guild {interaction.guild_id} by {interaction.user}")
        await player_state.cleanup()
        await interaction.response.send_message("👋 Left the channel and cleared the queue.", ephemeral=True)


    @app_commands.command(name="play", description="Plays or queues a song/playlist (URL or Search).")
    @app_commands.describe(query="YouTube/SoundCloud/etc. URL or search query.")
    async def play(self, interaction: discord.Interaction, query: str):
        """Plays or adds song/playlist to the queue."""
        # Check for guild already done by cog_check
        await interaction.response.defer(thinking=True) # Defer response immediately

        player_state = self.get_player(interaction)
        if not player_state: await interaction.followup.send("❌ Error getting player state.", ephemeral=True); return

        # --- Ensure Connection ---
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("❌ Join a voice channel first!", ephemeral=True); return

        target_channel = interaction.user.voice.channel
        vc = player_state.voice_client

        # Connect if not connected
        if not vc or not vc.is_connected():
             try:
                 player_state.voice_client = await target_channel.connect()
                 vc = player_state.voice_client # Update local vc reference
             except Exception as e:
                 self.logger.error(f"Failed connecting to VC {target_channel.id} for play: {e}", exc_info=True)
                 await interaction.followup.send(f"❌ Failed to join {target_channel.mention}.", ephemeral=True); return
        # Move if connected to wrong channel
        elif vc.channel != target_channel:
             try: await vc.move_to(target_channel)
             except Exception as e:
                  self.logger.error(f"Failed moving to VC {target_channel.id} for play: {e}", exc_info=True)
                  await interaction.followup.send(f"❌ Failed to move to {target_channel.mention}.", ephemeral=True); return


        # --- Search with yt-dlp ---
        loop = asyncio.get_event_loop()
        try:
            # Run blocking I/O in executor
            data = await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(YDL_OPTIONS).extract_info(query, download=False))
        except Exception as e:
            self.logger.warning(f"yt-dlp failed for query '{query}' in guild {interaction.guild_id}: {e}")
            await interaction.followup.send(f"❌ Couldn't process `{query}`. Check the link or search term.", ephemeral=True); return

        # --- Process Result ---
        if not data:
             await interaction.followup.send(f"❌ No information found for `{query}`.", ephemeral=True); return

        entries_to_add = []
        playlist_title = None

        if data.get('_type') == 'playlist': # Check if yt-dlp identified it as a playlist
             entries_to_add = data.get('entries', [])
             playlist_title = data.get('title', 'Playlist')
        elif 'entries' in data: # Search results
             entries_to_add = data['entries']
             # Don't set playlist_title for search results
        else: # Single track
             entries_to_add.append(data)

        if not entries_to_add:
             await interaction.followup.send(f"❌ No playable tracks found in `{query}`.", ephemeral=True); return

        added_count = 0
        first_added_title = None
        error_messages = []

        for entry in entries_to_add:
            # --- Sanity check entry ---
            if not entry: continue # Skip None entries in playlist
            url = entry.get('url') # Should be streamable URL
            title = entry.get('title')
            if not url or not title:
                self.logger.warning(f"Skipping entry with no URL/Title in guild {interaction.guild_id}: {entry.get('id', 'N/A')}")
                error_messages.append(f"Skipped item `({entry.get('id', 'N/A')})` - Missing data.")
                continue

            queue_item = {
                'title': title,
                'url': url,
                'webpage_url': entry.get('webpage_url', query if not playlist_title else None),
                'duration': entry.get('duration', 0),
                'thumbnail': entry.get('thumbnail', None),
                'requester': interaction.user.mention
            }
            await player_state.queue.put(queue_item)
            added_count += 1
            if first_added_title is None: first_added_title = queue_item['title']

            # Limit queued playlist size?
            # if playlist_title and added_count >= 50:
            #    error_messages.append("Stopped queuing playlist at 50 songs.")
            #    break

        if added_count == 0:
             base_error = f"❌ No playable tracks could be added from `{query}`."
             if error_messages: base_error += "\n" + "\n".join(error_messages[:3]) # Show first few errors
             await interaction.followup.send(base_error, ephemeral=True); return

        # --- Confirmation Message ---
        if playlist_title:
             message = f"✅ Queued **{added_count}** songs from playlist **{playlist_title}**!"
        else:
             # If only one song added from search/single link
             if added_count == 1 and first_added_title:
                  message = f"✅ Queued **{first_added_title}**!"
             # If multiple songs added from search results
             elif added_count > 1 and first_added_title:
                  message = f"✅ Queued **{first_added_title}** and {added_count-1} other(s)!" # Maybe ambiguous?
             else: # Fallback if title somehow missing
                  message = f"✅ Queued **{added_count}** track{'s' if added_count != 1 else ''}!"

        # Append any Skipped messages
        if error_messages and not playlist_title: # Don't spam for playlists
            message += "\n" + "\n".join(error_messages[:3])

        await interaction.followup.send(message) # Send public confirmation

        # --- Start Player & Update UI ---
        if player_state.voice_client and player_state.voice_client.is_connected():
            # Check if player is already playing - start_player_task handles this check internally
            await player_state.start_player_task()
            # Update UI immediately if something is now playing or was already playing
            if interaction.channel:
                await player_state.update_now_playing_message(interaction.channel)
            else:
                 self.logger.warning(f"Cannot update player UI for guild {interaction.guild_id}: interaction.channel is None.")

        self.logger.info(f"Added {added_count} track(s) for query '{query}' in guild {interaction.guild_id}")


    # TODO: Add other commands: skip, stop, queue, np, loop, volume, etc.


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))
# --- END OF assets/commands/music.py ---