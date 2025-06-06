import discord
from discord.ext import commands
from discord import app_commands
import random
import os
from dotenv import load_dotenv
import asyncio
import traceback
import logging
from discord.ui import Button, View, Modal, TextInput, Select

load_dotenv()

_owner_id_str = os.getenv('OWNER_ID')
if _owner_id_str is None:
    logging.critical("OWNER_ID environment variable is not set. Please set it in Render's Environment settings.")
    OWNER_ID = -1
else:
    try:
        OWNER_ID = int(_owner_id_str)
    except ValueError:
        logging.critical(f"OWNER_ID environment variable '{_owner_id_str}' is not a valid integer. Please check Render's Environment settings.")
        OWNER_ID = -1

def is_owner_global(interaction: discord.Interaction) -> bool:
    """
    Checks if the interaction user is the owner (global check function).
    This function is defined here but the cog's slash commands should ideally use the one imported from main.py
    for consistency and proper owner_id resolution from bot.owner_id.
    """
    return interaction.user.id == OWNER_ID

class ProsekaGeneralCommands(commands.Cog):
    """
    Cog for general Project SEKAI functionalities, including an interactive song list and random song selection.
    """
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = OWNER_ID # Store owner_id for this cog
        logging.info("ProsekaGeneralCommands.__init__ started.")

        # Define color mapping for difficulties
        self.DIFFICULTY_COLORS = {
            "EASY": discord.Color(0x76B66B),
            "NORMAL": discord.Color(0x56A8DB),
            "HARD": discord.Color(0xFFFF00),
            "EXPERT": discord.Color(0xFF0000),
            "MASTER": discord.Color(0x800080),
            "APPEND": discord.Color(0xFFC0CB)
        }

        # These will be populated by main.py's setup_hook
        self.songs_data = [] 
        self.valid_difficulties = ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"] 

        # Reference to the AP/FC rate cog for cross-cog communication
        self.ap_fc_rate_cog = None 

        # Flag to control if AP/FC rate display should be updated when list_songs is used
        self.should_update_ap_fc_rate_display = False 
        logging.info(f"ProsekaGeneralCommands - AP/FCレート表示の自動更新は現在 {'有効' if self.should_update_ap_fc_rate_display else '無効'} に設定されています。")

        logging.info("ProsekaGeneralCommands.__init__ completed.")
        logging.debug(f"ProsekaGeneralCommands __init__ - initial ap_fc_rate_cog: {self.ap_fc_rate_cog}")
        if self.songs_data:
            logging.debug(f"Loaded {len(self.songs_data)} songs.")
        else:
            logging.debug("No songs loaded or songs_data is empty.")
        # 修正: ロギングの引数渡しを修正
        logging.debug("Valid Difficulties loaded: %s", self.valid_difficulties)

    def _get_difficulty_level(self, song: dict, difficulty_name: str) -> int | None:
        """Helper to get difficulty level for a song."""
        return song.get(difficulty_name.lower())

    @app_commands.command(name="pjsk_list_songs", description="プロジェクトセカイの楽曲一覧をメニューで並べ替えて表示します。")
    async def pjsk_list_songs(self, interaction: discord.Interaction):
        """
        Displays an interactive list of Project SEKAI songs with sorting and filtering options.
        """
        logging.info(f"Command '/pjsk_list_songs' invoked by {interaction.user.name} (ID: {interaction.user.id}).")
        
        # Defer response as quickly as possible
        try:
            await interaction.response.defer(ephemeral=False) # Public response
            logging.info(f"Successfully deferred interaction for '{interaction.command.name}'.")
        except discord.errors.NotFound:
            logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound). This will be caught by global error handler.", exc_info=True)
            return # If defer fails, stop processing
        except Exception as e:
            logging.error(f"Unexpected error during defer for '{interaction.command.name}': {e}", exc_info=True)
            return # If defer fails, stop processing

        if not self.bot.is_bot_ready:
            logging.warning(f"Bot not ready for command '{interaction.command.name}'. User: {interaction.user.name}. Sending 'bot not ready' message via followup.")
            await interaction.followup.send("ボットがまだ起動中です。しばらくお待ちください。", ephemeral=True)
            return

        if not self.songs_data:
            logging.warning(f"songs_data is empty for '{interaction.command.name}'. Sending error message.")
            await interaction.followup.send("現在、登録されている楽曲がありません。", ephemeral=False)
            return

        try:
            # Create the interactive View for song listing
            view = SongListView(
                original_songs_data=self.songs_data,
                valid_difficulties=self.valid_difficulties,
                difficulty_colors=self.DIFFICULTY_COLORS,
                original_user_id=interaction.user.id,
                get_difficulty_level_func=self._get_difficulty_level
            )
            logging.info("SongListView instance created.")
        except Exception as e:
            logging.error(f"Failed to create SongListView instance for '{interaction.command.name}': {e}", exc_info=True)
            await interaction.followup.send("楽曲リストの初期化中にエラーが発生しました。", ephemeral=False)
            return

        try:
            # Get the initial embed and send the message with the View
            initial_embed = view.get_current_embed()
            response_message = await interaction.followup.send(embed=initial_embed, view=view, ephemeral=False)
            view.message = response_message # Store the message object in the View for later edits
            logging.info(f"Initial list message sent via followup.send for '{interaction.command.name}'. View message set.")
        except Exception as e:
            logging.error(f"Failed to send initial list message for '{interaction.command.name}': {e}", exc_info=True)
            await interaction.followup.send("楽曲リストの送信中にエラーが発生しました。", ephemeral=False)
            return

        # Check if AP/FC rate display should be updated (if cog is available and flag is true)
        if self.ap_fc_rate_cog and self.should_update_ap_fc_rate_display:
            try:
                await self.ap_fc_rate_cog.update_ap_fc_rate_display(interaction.user.id, interaction.channel)
                logging.info("AP/FC rate display updated for /pjsk_list_songs.")
            except Exception as e:
                logging.error(f"Error updating AP/FC rate display for /pjsk_list_songs: {e}", exc_info=True)
        else:
            logging.info("AP/FC rate display update skipped for /pjsk_list_songs (cog not available or auto-update disabled).")

    # ★ここから /pjsk_random_song コマンドの再追加
    @app_commands.command(name="pjsk_random_song", description="プロジェクトセカイの楽曲からランダムで1曲選曲します。")
    @app_commands.describe(
        difficulty="難易度を指定します (EASY, NORMAL, HARD, EXPERT, MASTER, APPEND)",
        min_level="最小レベル (1-37)",
        max_level="最大レベル (1-37)"
    )
    @app_commands.choices(
        difficulty=[app_commands.Choice(name=d, value=d) for d in ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"]]
    )
    async def pjsk_random_song(self, 
                               interaction: discord.Interaction, 
                               difficulty: str = None, 
                               min_level: app_commands.Range[int, 1, 37] = None, 
                               max_level: app_commands.Range[int, 1, 37] = None):
        """
        Selects a random Project SEKAI song based on optional difficulty and level filters.
        """
        logging.info(f"Command '/pjsk_random_song' invoked by {interaction.user.name} (ID: {interaction.user.id}). "
                     f"Difficulty: {difficulty}, Min_level: {min_level}, Max_level: {max_level}")
        
        try:
            await interaction.response.defer(ephemeral=False)
            logging.info(f"Successfully deferred interaction for '{interaction.command.name}'.")
        except discord.errors.NotFound:
            logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound).", exc_info=True)
            return
        except Exception as e:
            logging.error(f"Unexpected error during defer for '{interaction.command.name}': {e}", exc_info=True)
            return

        if not self.bot.is_bot_ready:
            logging.warning(f"Bot not ready for command '{interaction.command.name}'. Sending 'bot not ready' message.")
            await interaction.followup.send("ボットがまだ起動中です。しばらくお待ちください。", ephemeral=True)
            return

        if not self.songs_data:
            logging.warning(f"songs_data is empty for '{interaction.command.name}'. Sending error message.")
            await interaction.followup.send("現在、登録されている楽曲がありません。", ephemeral=False)
            return

        # Validate level range if provided
        if min_level is not None and max_level is not None and min_level > max_level:
            await interaction.followup.send("最小レベルが最大レベルより大きいです。", ephemeral=True)
            return

        eligible_songs = []
        for song in self.songs_data:
            eligible_difficulties_for_song = []
            
            # If a specific difficulty is requested, check only that one
            if difficulty:
                d_lower = difficulty.lower()
                level = self._get_difficulty_level(song, d_lower)
                if level is not None:
                    # Check if level is within range if provided
                    if (min_level is None or level >= min_level) and \
                       (max_level is None or level <= max_level):
                        eligible_difficulties_for_song.append({"difficulty": d_lower, "level": level})
            else: # If no specific difficulty, check all valid difficulties for the song
                for d_upper in self.valid_difficulties:
                    d_lower = d_upper.lower()
                    level = self._get_difficulty_level(song, d_lower)
                    if level is not None:
                         # Check if level is within range if provided
                        if (min_level is None or level >= min_level) and \
                           (max_level is None or level <= max_level):
                            eligible_difficulties_for_song.append({"difficulty": d_lower, "level": level})

            if eligible_difficulties_for_song:
                song_copy = song.copy()
                song_copy["_eligible_difficulties"] = eligible_difficulties_for_song
                eligible_songs.append(song_copy)

        if not eligible_songs:
            logging.info(f"No eligible songs found for random selection based on criteria: Diff={difficulty}, MinLv={min_level}, MaxLv={max_level}.")
            await interaction.followup.send("申し訳ありません、指定された条件に合う楽曲が見つかりませんでした。", ephemeral=False)
            return

        # Select a random song from the eligible list
        selected_song = random.choice(eligible_songs)
        
        # Select a random eligible difficulty for the chosen song (if a specific difficulty wasn't requested)
        if difficulty:
            chosen_difficulty_info = next((d for d in selected_song["_eligible_difficulties"] if d["difficulty"] == difficulty.lower()), None)
            if not chosen_difficulty_info: # Fallback if for some reason the exact difficulty isn't found (shouldn't happen with proper filtering)
                chosen_difficulty_info = random.choice(selected_song["_eligible_difficulties"])
        else:
            chosen_difficulty_info = random.choice(selected_song["_eligible_difficulties"])
            
        selected_difficulty_display = chosen_difficulty_info["difficulty"].upper()
        actual_level = chosen_difficulty_info["level"]

        embed_color = self.DIFFICULTY_COLORS.get(selected_difficulty_display, discord.Color.blue())

        level_display_str = f"Lv.{actual_level}" if actual_level is not None else "(レベル情報なし)"

        embed = discord.Embed(
            title=f"🎲 ランダム選曲: {selected_song['title']}",
            description=f"アーティスト: {selected_song.get('artist', '不明')}\n"
                        f"難易度: **{selected_difficulty_display}** {level_display_str}",
            color=embed_color
        )
        if selected_song.get("image_url"):
            embed.set_thumbnail(url=selected_song["image_url"])
        
        # Optionally add more details like BPM or notes count
        if selected_song.get("bpm"):
            embed.add_field(name="BPM", value=selected_song["bpm"], inline=True)
        if selected_song.get(f"notes_{selected_difficulty_display.lower()}"):
            embed.add_field(name="ノーツ数", value=selected_song[f"notes_{selected_difficulty_display.lower()}"], inline=True)
        
        await interaction.followup.send(embed=embed, ephemeral=False)
        logging.info(f"Successfully sent random song selection for '{interaction.command.name}'. Song: {selected_song['title']}, Difficulty: {selected_difficulty_display}.")

        # Update AP/FC rate display if the cog is available and auto-update is enabled
        if self.ap_fc_rate_cog and self.should_update_ap_fc_rate_display:
            try:
                await self.ap_fc_rate_cog.update_ap_fc_rate_display(interaction.user.id, interaction.channel)
                logging.info("AP/FC rate display updated for /pjsk_random_song.")
            except Exception as e:
                logging.error(f"Error updating AP/FC rate display for /pjsk_random_song: {e}", exc_info=True)
        else:
            logging.info("AP/FC rate display update skipped for /pjsk_random_song (cog not available or auto-update disabled).")
    # ★ここまで /pjsk_random_song コマンドの再追加


class SongListView(discord.ui.View):
    """
    An interactive View for displaying and managing a list of songs with pagination,
    sorting (by release order, title, or difficulty level), and difficulty filtering.
    """
    def __init__(self, original_songs_data, valid_difficulties, difficulty_colors, original_user_id, get_difficulty_level_func):
        super().__init__(timeout=86400) # View timeout after 24 hours (86400 seconds)
        self.original_songs_data = original_songs_data
        self.valid_difficulties = valid_difficulties
        self.difficulty_colors = difficulty_colors
        self.current_sort_key = "release_order" # Default sort: by original index (release order)
        self.current_sort_reverse = False # Default sort order: ascending
        self.current_difficulty_filter = None # Default filter: None
        self.current_page = 0 # Current page index
        self.items_per_page = 10 # Number of songs per page
        self.message = None # Reference to the message this View is attached to
        self.original_user_id = original_user_id # ID of the user who initiated the command
        self.get_difficulty_level_func = get_difficulty_level_func # Function to get difficulty level from a song dict
        logging.info("SongListView.__init__ started.")

        # Create indexed copies of songs to preserve original order for "release_order" sort
        self.indexed_songs_data = []
        for i, song in enumerate(self.original_songs_data):
            song_copy = song.copy()
            song_copy['_original_index'] = i
            self.indexed_songs_data.append(song_copy)

        self._update_sorted_songs() # Initial sorting and filtering
        self._set_difficulty_select_options() # Populate options for difficulty dropdown
        self._update_sort_buttons() # Update button styles based on current sort order
        logging.info("SongListView initialized.")

    def _update_sorted_songs(self):
        """
        Applies current difficulty filter and sort order to the song list.
        Updates self.sorted_songs, self.total_pages, and self.current_page.
        """
        logging.debug("Updating sorted songs.")
        filtered_songs_by_difficulty = []
        if self.current_difficulty_filter and self.current_difficulty_filter != "None":
            for song in self.indexed_songs_data:
                # If a difficulty filter is applied, only include songs that have that difficulty level
                if self.get_difficulty_level_func(song, self.current_difficulty_filter) is not None:
                    filtered_songs_by_difficulty.append(song)
            logging.debug(f"Songs filtered by difficulty '{self.current_difficulty_filter}': {len(filtered_songs_by_difficulty)} songs.")
        else:
            # If no filter, use all songs
            filtered_songs_by_difficulty = list(self.indexed_songs_data)
            logging.debug("No difficulty filter, using all songs.")

        # Apply sorting based on current sort key
        if self.current_sort_key == "release_order":
            self.sorted_songs = sorted(
                filtered_songs_by_difficulty,
                key=lambda x: x.get("_original_index", 0), # Sort by original index
                reverse=self.current_sort_reverse
            )
            logging.debug(f"Sorted by release order {'descending' if self.current_sort_reverse else 'ascending'}.")
        elif self.current_sort_key == "title":
            self.sorted_songs = sorted(
                filtered_songs_by_difficulty, 
                key=lambda x: x.get("title", ""), # Sort by title
                reverse=self.current_sort_reverse
            )
            logging.debug(f"Sorted by title {'descending' if self.current_sort_reverse else 'ascending'}.")
        elif self.current_sort_key == "level":
            if self.current_difficulty_filter and self.current_difficulty_filter != "None":
                self.sorted_songs = sorted(
                    filtered_songs_by_difficulty,
                    key=lambda x: self.get_difficulty_level_func(x, self.current_difficulty_filter) if self.get_difficulty_level_func(x, self.current_difficulty_filter) is not None else -1, # Sort by level, put songs without specified difficulty at the end
                    reverse=self.current_sort_reverse
                )
                logging.debug(f"Sorted by level for difficulty {self.current_difficulty_filter} {'descending' if self.current_sort_reverse else 'ascending'}.")
            else:
                # If level sort is requested without a difficulty filter, revert to release order
                self.sorted_songs = sorted(
                    list(self.indexed_songs_data),
                    key=lambda x: x.get("_original_index", 0),
                    reverse=self.current_sort_reverse
                )
                self.current_sort_key = "release_order" # Reset sort key
                logging.debug("Level sort requested without difficulty filter, reset to release order (with current sort reverse).")

        # Recalculate total pages and adjust current page if necessary
        self.total_pages = (len(self.sorted_songs) + self.items_per_page - 1) // self.items_per_page
        self.current_page = min(self.current_page, self.total_pages - 1) if self.total_pages > 0 else 0
        if self.current_page < 0: self.current_page = 0 # Ensure page is not negative

        logging.debug(f"Total {len(self.sorted_songs)} songs, {self.total_pages} pages. Current page: {self.current_page}")

    def _update_sort_buttons(self):
        """Updates the style of sort buttons based on the current sort order."""
        logging.debug("Updating sort buttons.")
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.custom_id == "sort_asc":
                    item.style = discord.ButtonStyle.primary if not self.current_sort_reverse else discord.ButtonStyle.secondary
                elif item.custom_id == "sort_desc":
                    item.style = discord.ButtonStyle.primary if self.current_sort_reverse else discord.ButtonStyle.secondary

    def get_current_embed(self) -> discord.Embed:
        """Generates the Discord Embed object for the current page and settings."""
        logging.debug("Getting current embed.")
        start_index = self.current_page * self.items_per_page
        end_index = min(start_index + self.items_per_page, len(self.sorted_songs))

        display_songs = self.sorted_songs[start_index:end_index]

        embed = discord.Embed(
            title="🎵 プロジェクトセカイ 楽曲リスト",
            color=discord.Color(0x3BBD4E) # A shade of green for Project SEKAI theme
        )

        if not display_songs:
            embed.description = "表示する楽曲がありません。"
        else:
            description_lines = []
            for i, song in enumerate(display_songs):
                title = song.get("title", "不明な楽曲")

                if self.current_difficulty_filter and self.current_difficulty_filter != "None":
                    level = self.get_difficulty_level_func(song, self.current_difficulty_filter)
                    if level is not None:
                        difficulty_info_str = f" ({self.current_difficulty_filter}:Lv.{level})"
                        description_lines.append(f"{start_index + i + 1}. **{title}**{difficulty_info_str}")
                    else:
                        description_lines.append(f"{start_index + i + 1}. **{title}** (指定難易度情報なし)")
                else:
                    description_lines.append(f"{start_index + i + 1}. **{title}**")
            embed.description = "\n".join(description_lines)

        # Determine the display name for sorting
        sort_display_name = ""
        if self.current_sort_key == "release_order":
            sort_display_name = "配信順"
        elif self.current_sort_key == "title":
            sort_display_name = "タイトル順"
        elif self.current_sort_key == "level":
            if self.current_difficulty_filter and self.current_difficulty_filter != "None":
                sort_display_name = f"レベル順 ({self.current_difficulty_filter})"
            else:
                sort_display_name = "レベル順 (フィルターなし)" # Fallback if filter is cleared after level sort

        sort_order_text = " (降順)" if self.current_sort_reverse else " (昇順)"
        sort_display_name += sort_order_text

        filter_display_name = self.current_difficulty_filter if self.current_difficulty_filter else "なし"

        # 修正: フッターの楽曲数表示ロジックを汎用化
        total_songs_count_for_footer = len(self.original_songs_data)
        total_songs_label = "全"

        if self.current_difficulty_filter and self.current_difficulty_filter != "None":
            # フィルターされた難易度を持つ楽曲の総数をカウント
            total_songs_with_filtered_difficulty = sum(
                1 for song in self.original_songs_data 
                if self.get_difficulty_level_func(song, self.current_difficulty_filter) is not None
            )
            total_songs_count_for_footer = total_songs_with_filtered_difficulty
            total_songs_label = f"{self.current_difficulty_filter}譜面あり"
        
        embed.set_footer(text=f"{total_songs_label} {total_songs_count_for_footer} 曲 | ページ {self.current_page + 1}/{self.total_pages} | ソート: {sort_display_name} | フィルター: {filter_display_name}")
        
        return embed

    def _set_difficulty_select_options(self):
        """Populates the options for the difficulty select dropdown."""
        logging.debug("Setting difficulty select options.")
        options = [discord.SelectOption(label="フィルターなし", value="None")]
        for diff in self.valid_difficulties:
            options.append(discord.SelectOption(label=diff, value=diff))

        for item in self.children:
            if isinstance(item, discord.ui.Select) and item.custom_id == "difficulty_select_handler":
                item.options = options
                logging.debug("Difficulty select options set.")
                break

    async def _update_message(self, interaction: discord.Interaction):
        """Updates the current message with the new embed and view state."""
        logging.debug("Updating message display.")
        self._update_sorted_songs() # Recalculate sorted list based on current settings
        self._update_sort_buttons() # Update sort button styles
        embed = self.get_current_embed() # Generate the new embed

        try:
            if self.message:
                # If the view is already attached to a message, edit that message
                await self.message.edit(embed=embed, view=self)
                logging.info(f"SongListView message {self.message.id} updated.")
            else:
                # If the view is not yet attached to a message (e.g., initial response),
                # edit the original interaction response.
                await interaction.response.edit_message(embed=embed, view=self)
                logging.info(f"SongListView interaction response edited.")
        except discord.NotFound:
            logging.warning("SongListView message not found, stopping view.")
            self.stop() # Stop the view if the message is deleted
        except Exception as e:
            logging.error(f"Failed to update SongListView message: {e}", exc_info=True)


    @discord.ui.button(label="← 前へ", style=discord.ButtonStyle.primary, custom_id="prev_page", row=1)
    async def prev_page(self, interaction: discord.Interaction, button: Button):
        """Button to navigate to the previous page."""
        logging.info(f"User {interaction.user.id} clicked 'Previous Page'.")
        await interaction.response.defer() # Defer the interaction
        if self.current_page > 0:
            self.current_page -= 1
            await self._update_message(interaction)
            logging.info(f"User {interaction.user.id} went to previous page: {self.current_page}.")
        else:
            await interaction.followup.send("これ以上前のページはありません。", ephemeral=True)
            logging.info(f"User {interaction.user.id} tried to go beyond first page.")

    @discord.ui.button(label="次へ →", style=discord.ButtonStyle.primary, custom_id="next_page", row=1)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        """Button to navigate to the next page."""
        logging.info(f"User {interaction.user.id} clicked 'Next Page'.")
        await interaction.response.defer() # Defer the interaction
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self._update_message(interaction)
            logging.info(f"User {interaction.user.id} went to next page: {self.current_page}.")
        else:
            await interaction.followup.send("これ以上次のページはありません。", ephemeral=True)
            logging.info(f"User {interaction.user.id} tried to go beyond last page.")

    @discord.ui.button(label="昇順", style=discord.ButtonStyle.primary, custom_id="sort_asc", row=2)
    async def sort_asc(self, interaction: discord.Interaction, button: Button):
        """Button to set sort order to ascending."""
        logging.info(f"User {interaction.user.id} clicked 'Sort Ascending'.")
        await interaction.response.defer() # Defer the interaction
        self.current_sort_reverse = False
        self.current_page = 0 # Reset to first page after sorting
        await self._update_message(interaction)
        logging.info(f"User {interaction.user.id} set sort order to ascending.")

    @discord.ui.button(label="降順", style=discord.ButtonStyle.primary, custom_id="sort_desc", row=2)
    async def sort_desc(self, interaction: discord.Interaction, button: Button):
        """Button to set sort order to descending."""
        logging.info(f"User {interaction.user.id} clicked 'Sort Descending'.")
        await interaction.response.defer() # Defer the interaction
        self.current_sort_reverse = True
        self.current_page = 0 # Reset to first page after sorting
        await self._update_message(interaction)
        logging.info(f"User {interaction.user.id} set sort order to descending.")

    @discord.ui.select(
        custom_id="difficulty_select_handler",
        placeholder="難易度でフィルター...",
        options=[], # Options will be populated in _set_difficulty_select_options
        row=0 # First row for the select dropdown
    )
    async def select_difficulty_callback(self, interaction: discord.Interaction, select: Select):
        """Callback for the difficulty filter dropdown."""
        logging.info(f"User {interaction.user.id} selected difficulty filter: {select.values[0]}.")
        await interaction.response.defer() # Defer the interaction
        selected_value = select.values[0]
        self.current_difficulty_filter = selected_value if selected_value != "None" else None
        self.current_page = 0 # Reset to first page after filtering

        # If a difficulty filter is selected, automatically set sort key to "level" if not already.
        # If filter is cleared, revert to "release_order".
        if self.current_difficulty_filter and self.current_difficulty_filter != "None":
            if self.current_sort_key != "level":
                self.current_sort_key = "level"
                self.current_sort_reverse = False # Default to ascending for level sort
        else:
            self.current_sort_key = "release_order" # Reset sort key if filter is cleared

        await self._update_message(interaction)
        logging.info(f"User {interaction.user.id} filtered by difficulty: {self.current_difficulty_filter}. Auto-set sort key to {self.current_sort_key}.")

    async def on_timeout(self):
        """Called when the View times out."""
        logging.info(f"SongListView for user {self.original_user_id} timed out.")
        if self.message:
            try:
                # Disable all buttons when the view times out
                for item in self.children:
                    if hasattr(item, 'disabled'):
                        item.disabled = True
                await self.message.edit(view=self)
                logging.info(f"Disabled buttons for SongListView message {self.message.id} on timeout.")
            except discord.NotFound:
                logging.warning("SongListView message not found during timeout handling. It might have been deleted.")
                pass # Message might have been deleted, so do nothing.
            except Exception as e:
                logging.error(f"Failed to disable buttons on timeout for user {self.original_user_id}: {e}", exc_info=True)


async def setup(bot):
    """Loads the ProsekaGeneralCommands cog into the bot."""
    cog = ProsekaGeneralCommands(bot)
    await bot.add_cog(cog)
    logging.info("ProsekaGeneralCommands cog loaded and commands added.")
