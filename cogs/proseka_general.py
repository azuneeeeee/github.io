import discord
from discord.ext import commands
from discord import app_commands
import random
import os
from dotenv import load_dotenv
import asyncio
import traceback
import logging
from discord.ui import Button, View, Modal, TextInput, Select # ★修正: Button をインポート

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
    return interaction.user.id == OWNER_ID

class ProsekaGeneralCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owner_id = OWNER_ID
        logging.info("ProsekaGeneralCommands.__init__ started.")

        self.DIFFICULTY_COLORS = {
            "EASY": discord.Color(0x76B66B),
            "NORMAL": discord.Color(0x56A8DB),
            "HARD": discord.Color(0xFFFF00),
            "EXPERT": discord.Color(0xFF0000),
            "MASTER": discord.Color(0x800080),
            "APPEND": discord.Color(0xFFC0CB)
        }

        self.songs_data = []
        self.valid_difficulties = ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"]

        self.ap_fc_rate_cog = None

        self.should_update_ap_fc_rate_display = False
        logging.info(f"ProsekaGeneralCommands - AP/FCレート表示の自動更新は現在 {'有効' if self.should_update_ap_fc_rate_display else '無効'} に設定されています。")

        logging.info("ProsekaGeneralCommands.__init__ completed.")
        logging.debug(f"ProsekaGeneralCommands __init__ - initial ap_fc_rate_cog: {self.ap_fc_rate_cog}")
        if self.songs_data:
            logging.debug(f"Loaded {len(self.songs_data)} songs.")
        else:
            logging.debug("No songs loaded or songs_data is empty.")
        logging.debug("Valid Difficulties loaded:", self.valid_difficulties)

    def _get_difficulty_level(self, song: dict, difficulty_name: str) -> int | None:
        return song.get(difficulty_name.lower())

    @app_commands.command(name="pjsk_list_songs", description="プロジェクトセカイの楽曲一覧をメニューで並べ替えて表示します。")
    async def pjsk_list_songs(self, interaction: discord.Interaction):
        logging.info(f"Command '/pjsk_list_songs' invoked by {interaction.user.name} (ID: {interaction.user.id}).")
        
        if not self.bot.is_bot_ready:
            logging.warning(f"Bot not ready for command '{interaction.command.name}'. User: {interaction.user.name}. Sending 'bot not ready' message.")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("ボットがまだ起動中です。しばらくお待ちください。", ephemeral=True)
                return
            except discord.errors.InteractionResponded:
                logging.warning(f"Interaction for '{interaction.command.name}' was already responded to before 'bot not ready' check. Skipping send_message.")
                return
            except Exception as e:
                logging.error(f"Failed to send 'bot not ready' message for '{interaction.command.name}': {e}", exc_info=True)
                return

        logging.info(f"Bot is ready. Proceeding with defer for '{interaction.command.name}'.")
        try:
            # ★修正: わずかな遅延を挿入
            await asyncio.sleep(0.1)
            await interaction.response.defer(ephemeral=False)
            logging.info(f"Successfully deferred interaction for '{interaction.command.name}'.")
        except discord.errors.NotFound:
            logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound). This will be caught by global error handler.", exc_info=True)
            return
        except Exception as e:
            logging.error(f"Unexpected error during defer for '{interaction.command.name}': {e}", exc_info=True)
            return

        if not self.songs_data:
            logging.warning(f"songs_data is empty for '{interaction.command.name}'. Sending error message.")
            await interaction.followup.send("現在、登録されている楽曲がありません。", ephemeral=False)
            return

        try:
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
            initial_embed = view.get_current_embed()
            response_message = await interaction.followup.send(embed=initial_embed, view=view, ephemeral=False)
            view.message = response_message
            logging.info(f"Initial list message sent via followup.send for '{interaction.command.name}'. View message set.")
        except Exception as e:
            logging.error(f"Failed to send initial list message for '{interaction.command.name}': {e}", exc_info=True)
            await interaction.followup.send("楽曲リストの送信中にエラーが発生しました。", ephemeral=False)
            return

        logging.info(f"'/pjsk_list_songs' - self.ap_fc_rate_cog: {self.ap_fc_rate_cog}. Skipping AP/FC rate update as requested.")


    @app_commands.command(name="pjsk_random_song", description="プロジェクトセカイの楽曲をランダムで選曲します。(難易度: 複数可, カンマ区切り例: EASY,HARD,MASTER)")
    @app_commands.describe(
        difficulty="難易度指定 (複数可, カンマ区切り例: EASY,HARD,MASTER)",
        level_min="最小レベル (1～37)",
        level_max="最大レベル (1～37)"
    )
    async def pjsk_random_song(
        self, interaction: discord.Interaction,
        difficulty: str = None,
        level_min: app_commands.Range[int, 1, 37] = None,
        level_max: app_commands.Range[int, 1, 37] = None
    ):
        logging.info(f"Command '/pjsk_random_song' invoked by {interaction.user.name} (ID: {interaction.user.id}).")
        
        if not self.bot.is_bot_ready:
            logging.warning(f"Bot not ready for command '{interaction.command.name}'. User: {interaction.user.name}. Sending 'bot not ready' message.")
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("ボットがまだ起動中です。しばらくお待ちください。", ephemeral=True)
                return
            except discord.errors.InteractionResponded:
                logging.warning(f"Interaction for '{interaction.command.name}' was already responded to before 'bot not ready' check. Skipping send_message.")
                return
            except Exception as e:
                logging.error(f"Failed to send 'bot not ready' message for '{interaction.command.name}': {e}", exc_info=True)
                return

        logging.info(f"Bot is ready. Proceeding with defer for '{interaction.command.name}'.")
        try:
            # ★修正: わずかな遅延を挿入
            await asyncio.sleep(0.1)
            await interaction.response.defer(ephemeral=False)
            logging.info(f"Successfully deferred interaction for '{interaction.command.name}'.")
        except discord.errors.NotFound:
            logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound). This will be caught by global error handler.", exc_info=True)
            return
        except Exception as e:
            logging.error(f"Unexpected error during defer for '{interaction.command.name}': {e}", exc_info=True)
            return

        logging.info(f"'/pjsk_random_song' called with difficulty='{difficulty}', level_min={level_min}, level_max={level_max}")

        selected_difficulties_from_input = []
        if difficulty:
            selected_difficulties_from_input = [d.strip().upper() for d in difficulty.split(',')]
            invalid_difficulties = [d for d in selected_difficulties_from_input if d not in self.valid_difficulties]
            if invalid_difficulties:
                logging.warning(f"Invalid difficulties provided for '{interaction.command.name}': {invalid_difficulties}")
                await interaction.followup.send(f"指定された難易度 `{', '.join(invalid_difficulties)}` は無効です。有効な難易度は {', '.join(self.valid_difficulties)} です。", ephemeral=False)
                return

        difficulties_to_filter = selected_difficulties_from_input if selected_difficulties_from_input else self.valid_difficulties
        logging.debug(f"Filtering with difficulties: {difficulties_to_filter}")

        options_to_use = {
            "difficulties": difficulties_to_filter,
            "level_min": level_min,
            "level_max": level_max
        }

        logging.debug(f"pjsk_random_song final options for selection: {options_to_use}")

        filtered_songs = []
        if self.songs_data:
            logging.debug(f"Total songs available for filtering: {len(self.songs_data)}")
            for song in self.songs_data:
                song_matched_by_difficulty = False

                for target_diff_name in options_to_use["difficulties"]:
                    level = self._get_difficulty_level(song, target_diff_name)

                    if level is None:
                        continue

                    level_ok = True
                    if options_to_use.get("level_min") is not None and level < options_to_use["level_min"]:
                        level_ok = False
                    if options_to_use.get("level_max") is not None and level > options_to_use["level_max"]:
                        level_ok = False

                    if level_ok:
                        song_matched_by_difficulty = True
                        break

                if song_matched_by_difficulty:
                    filtered_songs.append(song)

        logging.info(f"Final number of filtered songs: {len(filtered_songs)}")
        if not filtered_songs:
            logging.info(f"No songs found for random selection with provided criteria for '{interaction.command.name}'.")
            await interaction.followup.send("申し訳ありません、指定された条件に合う楽曲が見つかりませんでした。", ephemeral=False)
            return

        selected_song = random.choice(filtered_songs)
        logging.info(f"Randomly selected song: {selected_song.get('title')}")

        display_difficulty_str = ""
        embed_color = discord.Color.blue()

        selected_diff_name_for_display = None

        candidate_display_difficulties = []
        for target_diff_name in options_to_use["difficulties"]:
            level = self._get_difficulty_level(selected_song, target_diff_name)

            if level is None:
                continue

            level_ok = True
            if options_to_use.get("level_min") is not None and level < options_to_use["level_min"]:
                level_ok = False
            if options_to_use.get("level_max") is not None and level > options_to_use["level_max"]:
                level_ok = False

            if level_ok:
                candidate_display_difficulties.append(target_diff_name)

        if candidate_display_difficulties:
            selected_diff_name_for_display = random.choice(candidate_display_difficulties)
            logging.debug(f"Displaying difficulty selected from candidates: {selected_diff_name_for_display}")
        else:
            sort_priority = {'APPEND': 0, 'MASTER': 1, 'EXPERT': 2, 'HARD': 3, 'NORMAL': 4, 'EASY': 5}

            available_difficulties_in_song = []
            for d in self.valid_difficulties:
                level = self._get_difficulty_level(selected_song, d)
                if level is not None:
                    available_difficulties_in_song.append((d, level))

            if available_difficulties_in_song:
                selected_diff_name_for_display = sorted(
                    available_difficulties_in_song,
                    key=lambda item: (sort_priority.get(item[0], 99), -item[1])
                )[0][0]
                logging.debug(f"Fallback difficulty for display (no candidates): {selected_diff_name_for_display}")
            else:
                logging.debug("No valid difficulty found for display in fallback.")


        if selected_diff_name_for_display:
            level = self._get_difficulty_level(selected_song, selected_diff_name_for_display)
            if level is not None:
                level_str = f" Lv.{level}"
                display_difficulty_str = f"【{selected_diff_name_for_display}{level_str}】"
                embed_color = self.DIFFICULTY_COLORS.get(selected_diff_name_for_display, discord.Color.blue())
                logging.debug(f"Display string: {display_difficulty_str}, Color: {embed_color}")
            else:
                display_difficulty_str = f"【{selected_diff_name_for_display} (レベル情報なし)】"
                logging.debug(f"Display string: {display_difficulty_str} (level missing)")
        else:
            display_difficulty_str = "【難易度情報なし】"
            logging.debug("Display string: 【難易度情報なし】 (no difficulty selected)")

        embed = discord.Embed(
            title=f"🎧 {selected_song['title']}",
            description=f"難易度: {display_difficulty_str}",
            color=embed_color
        )
        if selected_song.get("image_url"):
            embed.set_thumbnail(url=selected_song["image_url"])
            logging.debug(f"Thumbnail set to: {selected_song['image_url']}")
        else:
            logging.debug("No image_url found for thumbnail.")

        await interaction.followup.send(embed=embed, ephemeral=False)
        logging.info("Embed sent successfully.")

        if self.ap_fc_rate_cog and self.should_update_ap_fc_rate_display:
            try:
                await self.ap_fc_rate_cog.update_ap_fc_rate_display(interaction.user.id, interaction.channel)
                logging.info("AP/FC rate display updated for /pjsk_random_song.")
            except Exception as e:
                logging.error(f"Error updating AP/FC rate display for /pjsk_random_song: {e}", exc_info=True)
        else:
            logging.info("AP/FC rate display update skipped for /pjsk_random_song (cog not available or update disabled).")


class SongListView(discord.ui.View):
    def __init__(self, original_songs_data, valid_difficulties, difficulty_colors, original_user_id, get_difficulty_level_func):
        super().__init__(timeout=86400)
        self.original_songs_data = original_songs_data
        self.valid_difficulties = valid_difficulties
        self.difficulty_colors = difficulty_colors
        self.current_sort_key = "release_order"
        self.current_sort_reverse = False
        self.current_difficulty_filter = None
        self.current_page = 0
        self.items_per_page = 10
        self.message = None
        self.original_user_id = original_user_id
        self.get_difficulty_level_func = get_difficulty_level_func
        logging.info("SongListView.__init__ started.")

        self.indexed_songs_data = []
        for i, song in enumerate(self.original_songs_data):
            song_copy = song.copy()
            song_copy['_original_index'] = i
            self.indexed_songs_data.append(song_copy)

        self._update_sorted_songs()
        self._set_difficulty_select_options()
        self._update_sort_buttons()
        logging.info("SongListView initialized.")

    def _update_sorted_songs(self):
        logging.debug("Updating sorted songs.")
        filtered_songs_by_difficulty = []
        if self.current_difficulty_filter and self.current_difficulty_filter != "None":
            for song in self.indexed_songs_data:
                if self.get_difficulty_level_func(song, self.current_difficulty_filter) is not None:
                    filtered_songs_by_difficulty.append(song)
            logging.debug(f"Songs filtered by difficulty '{self.current_difficulty_filter}': {len(filtered_songs_by_difficulty)} songs.")
        else:
            filtered_songs_by_difficulty = list(self.indexed_songs_data)
            logging.debug("No difficulty filter, using all songs.")

        if self.current_sort_key == "release_order":
            self.sorted_songs = sorted(
                filtered_songs_by_difficulty,
                key=lambda x: x.get("_original_index", 0),
                reverse=self.current_sort_reverse
            )
            logging.debug(f"Sorted by release order {'descending' if self.current_sort_reverse else 'ascending'}.")
        elif self.current_sort_key == "title":
            self.sorted_songs = sorted(
                filtered_songs_by_difficulty, 
                key=lambda x: x.get("title", ""),
                reverse=self.current_sort_reverse
            )
            logging.debug(f"Sorted by title {'descending' if self.current_sort_reverse else 'ascending'}.")
        elif self.current_sort_key == "level":
            if self.current_difficulty_filter and self.current_difficulty_filter != "None":
                self.sorted_songs = sorted(
                    filtered_songs_by_difficulty,
                    key=lambda x: self.get_difficulty_level_func(x, self.current_difficulty_filter) if self.get_difficulty_level_func(x, self.current_difficulty_filter) is not None else -1,
                    reverse=self.current_sort_reverse
                )
                logging.debug(f"Sorted by level for difficulty {self.current_difficulty_filter} {'descending' if self.current_sort_reverse else 'ascending'}.")
            else:
                self.sorted_songs = sorted(
                    list(self.indexed_songs_data),
                    key=lambda x: x.get("_original_index", 0),
                    reverse=self.current_sort_reverse
                )
                self.current_sort_key = "release_order"
                logging.debug("Level sort requested without difficulty filter, reset to release order (with current sort reverse).")

        self.total_pages = (len(self.sorted_songs) + self.items_per_page - 1) // self.items_per_page
        self.current_page = min(self.current_page, self.total_pages - 1) if self.total_pages > 0 else 0
        if self.current_page < 0: self.current_page = 0

        logging.debug(f"Total {len(self.sorted_songs)} songs, {self.total_pages} pages. Current page: {self.current_page}")

    def _update_sort_buttons(self):
        logging.debug("Updating sort buttons.")
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.custom_id == "sort_asc":
                    item.style = discord.ButtonStyle.primary if not self.current_sort_reverse else discord.ButtonStyle.secondary
                elif item.custom_id == "sort_desc":
                    item.style = discord.ButtonStyle.primary if self.current_sort_reverse else discord.ButtonStyle.secondary

    def get_current_embed(self) -> discord.Embed:
        logging.debug("Getting current embed.")
        start_index = self.current_page * self.items_per_page
        end_index = min(start_index + self.items_per_page, len(self.sorted_songs))

        display_songs = self.sorted_songs[start_index:end_index]

        embed = discord.Embed(
            title="🎵 プロジェクトセカイ 楽曲リスト",
            color=discord.Color(0x3BBD4E)
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

        sort_display_name = ""
        if self.current_difficulty_filter and self.current_difficulty_filter != "None":
            sort_display_name = f"レベル順 ({self.current_difficulty_filter})"
        else:
            sort_display_name = "配信順"

        sort_order_text = " (降順)" if self.current_sort_reverse else " (昇順)"

        sort_display_name += sort_order_text

        filter_display_name = self.current_difficulty_filter if self.current_difficulty_filter else "なし"

        embed.set_footer(text=f"全 {len(self.original_songs_data)} 曲 | ページ {self.current_page + 1}/{self.total_pages} | ソート: {sort_display_name} | フィルター: {filter_display_name}")

        return embed

    def _set_difficulty_select_options(self):
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
        logging.debug("Updating message display.")
        self._update_sorted_songs()
        self._update_sort_buttons()
        embed = self.get_current_embed()

        try:
            if self.message:
                await self.message.edit(embed=embed, view=self)
                logging.info(f"SongListView message {self.message.id} updated.")
            else:
                await interaction.response.edit_message(embed=embed, view=self)
                logging.info(f"SongListView interaction response edited.")
        except discord.NotFound:
            logging.warning("SongListView message not found, stopping view.")
            self.stop()
        except Exception as e:
            logging.error(f"Failed to update SongListView message: {e}", exc_info=True)


    @discord.ui.button(label="← 前へ", style=discord.ButtonStyle.primary, custom_id="prev_page", row=1)
    async def prev_page(self, interaction: discord.Interaction, button: Button):
        logging.info(f"User {interaction.user.id} clicked 'Previous Page'.")
        await interaction.response.defer()
        if self.current_page > 0:
            self.current_page -= 1
            await self._update_message(interaction)
            logging.info(f"User {interaction.user.id} went to previous page: {self.current_page}.")
        else:
            await interaction.followup.send("これ以上前のページはありません。", ephemeral=True)
            logging.info(f"User {interaction.user.id} tried to go before first page.")

    @discord.ui.button(label="次へ →", style=discord.ButtonStyle.primary, custom_id="next_page", row=1)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        logging.info(f"User {interaction.user.id} clicked 'Next Page'.")
        await interaction.response.defer()
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            await self._update_message(interaction)
            logging.info(f"User {interaction.user.id} went to next page: {self.current_page}.")
        else:
            await interaction.followup.send("これ以上次のページはありません。", ephemeral=True)
            logging.info(f"User {interaction.user.id} tried to go beyond last page.")

    @discord.ui.button(label="昇順", style=discord.ButtonStyle.primary, custom_id="sort_asc", row=2)
    async def sort_asc(self, interaction: discord.Interaction, button: Button):
        logging.info(f"User {interaction.user.id} clicked 'Sort Ascending'.")
        await interaction.response.defer()
        self.current_sort_reverse = False
        self.current_page = 0
        await self._update_message(interaction)
        logging.info(f"User {interaction.user.id} set sort order to ascending.")

    @discord.ui.button(label="降順", style=discord.ButtonStyle.primary, custom_id="sort_desc", row=2)
    async def sort_desc(self, interaction: discord.Interaction, button: Button):
        logging.info(f"User {interaction.user.id} clicked 'Sort Descending'.")
        await interaction.response.defer()
        self.current_sort_reverse = True
        self.current_page = 0
        await self._update_message(interaction)
        logging.info(f"User {interaction.user.id} set sort order to descending.")

    @discord.ui.select(
        custom_id="difficulty_select_handler",
        placeholder="難易度でフィルター...",
        options=[],
        row=0
    )
    async def select_difficulty_callback(self, interaction: discord.Interaction, select: Select):
        logging.info(f"User {interaction.user.id} selected difficulty filter: {select.values[0]}.")
        await interaction.response.defer()
        selected_value = select.values[0]
        self.current_difficulty_filter = selected_value if selected_value != "None" else None
        self.current_page = 0

        if self.current_difficulty_filter and self.current_difficulty_filter != "None":
            if self.current_sort_key != "level":
                self.current_sort_key = "level"
                self.current_sort_reverse = False
        else:
            self.current_sort_key = "release_order"

        await self._update_message(interaction)
        logging.info(f"User {interaction.user.id} filtered by difficulty: {self.current_difficulty_filter}. Auto-set sort key to {self.current_sort_key}.")

    async def on_timeout(self):
        logging.info(f"SongListView for user {self.original_user_id} timed out.")
        if self.message:
            try:
                for item in self.children:
                    if hasattr(item, 'disabled'):
                        item.disabled = True
                await self.message.edit(view=self)
                logging.info(f"Disabled buttons for SongListView message {self.message.id} on timeout.")
            except discord.NotFound:
                logging.warning("SongListView message not found during timeout handling. It might have been deleted.")
                pass
            except Exception as e:
                logging.error(f"Failed to disable buttons on timeout for user {self.original_user_id}: {e}", exc_info=True)


async def setup(bot):
    cog = ProsekaGeneralCommands(bot)
    await bot.add_cog(cog)
    logging.info("ProsekaGeneralCommands cog loaded and commands added.")
