import discord
from discord.ext import commands
from discord import app_commands
import random
import traceback
import logging
import asyncio

# main.pyから必要なグローバルチェック関数とGUILD_IDをインポート
# pjsk_rankmatch_settings, pjsk_clear_rankmatch_history コマンドを削除したため、
# is_bot_owner はこのコグでは不要になります。
from main import is_not_admin_mode_for_non_owner, GUILD_ID 

# songs.pyからVALID_DIFFICULTIESをインポート (もしsongs.pyに定義されている場合)
try:
    from data.songs import VALID_DIFFICULTIES
except ImportError:
    logging.warning("Failed to import VALID_DIFFICULTIES from data/songs.py. Using default fallback within cog if needed.")
    pass # このコグのコードには VALID_DIFFICULTIES の直接利用がないため、ここで定義は不要

class ProsekaRankMatchCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logging.info("ProsekaRankMatchCommands.__init__ started.")

        self.DIFFICULTY_COLORS = {
            "EASY": discord.Color(0x76B66B),
            "NORMAL": discord.Color(0x56A8DB),
            "HARD": discord.Color(0xFFFF00),
            "EXPERT": discord.Color(0xFF0000),
            "MASTER": discord.Color(0x800080),
            "APPEND": discord.Color(0xFFC0CB)
        }

        # ★修正: self.songs_data と self.valid_difficulties の初期化を削除★
        # これらのデータは bot.proseka_songs_data と bot.SONG_DATA_MAP から取得します
        
        self.ap_fc_rate_cog = None # main.pyのsetup_hookで設定される予定

        self.should_update_ap_fc_rate_display = False # ユーザーが提供したこの行は維持
        logging.info(f"AP/FCレート表示の自動更新は現在 {'有効' if self.should_update_ap_fc_rate_display else '無効'} に設定されています。")

        self.RANK_LEVEL_MAP = {
            "ビギナー": {"normal": (18, 25), "append_allowed": False},
            "ブロンズ": {"normal": (23, 26), "append_allowed": False},
            "シルバー": {"normal": (25, 28), "append_allowed": False},
            "ゴールド": {"normal": (26, 30), "append_allowed": False},
            "プラチナ": {"normal": (28, 31), "append_allowed": False},
            "ダイヤモンド": {"normal": (29, 32), "normal_append": (27, 30), "append_allowed": True},
            "マスター": {"normal": (30, 37), "master_append": (28, 37), "append_allowed": True},
        }

        self.RANK_EMOJIS = {
            "ビギナー": "<:rankmatch_beginner:1375065245067776100>",
            "ブロンズ": "<:rankmatch_bronze:1375070952584646738>",
            "シルバー": "<:rankmatch_silver:1375072587452907561>",
            "ゴールド": "<:rankmatch_gold:1375075224688787516>",
            "プラチナ": "<:rankmatch_platinum:1375077178789593159>",
            "ダイヤモンド": "<:rankmatch_diamond:1375078667495149589>",
            "マスター": "<:rankmatch_master:1375079350294020156>",
        }
        logging.info("ProsekaRankMatchCommands.__init__ completed.")

    # on_readyリスナーは、bot.is_ready()がTrueになった後にap_fc_rate_cogを設定するために重要
    @commands.Cog.listener()
    async def on_ready(self):
        if not self.ap_fc_rate_cog and self.bot.is_ready():
            self.ap_fc_rate_cog = self.bot.get_cog('ApFcRate')
            if self.ap_fc_rate_cog:
                logging.info("ProsekaRankMatchCommands: ap_fc_rate_cog reference set via on_ready.")
            else:
                logging.warning("ProsekaRankMatchCommands: ApFcRate cog not found on_ready.")

    def _get_difficulty_level(self, song: dict, difficulty_name: str) -> int | None:
        return song.get(difficulty_name.lower())

    @app_commands.command(name="pjsk_rankmatch_song", description="プロジェクトセカイのランクマッチ形式で楽曲を選曲します。")
    @app_commands.describe(
        rank="現在のランクを選択してください",
    )
    @app_commands.choices(
        rank=[
            app_commands.Choice(name="ビギナー", value="ビギナー"),
            app_commands.Choice(name="ブロンズ", value="ブロンズ"),
            app_commands.Choice(name="シルバー", value="シルバー"),
            app_commands.Choice(name="ゴールド", value="ゴールド"),
            app_commands.Choice(name="プラチナ", value="プラチナ"),
            app_commands.Choice(name="ダイヤモンド", value="ダイヤモンド"),
            app_commands.Choice(name="マスター", value="マスター"),
        ]
    )
    @app_commands.guilds(discord.Object(id=GUILD_ID)) # GUILD_IDをmain.pyからインポート
    @is_not_admin_mode_for_non_owner() # 管理者モードチェックを適用
    async def pjsk_rankmatch_song(
        self,
        interaction: discord.Interaction,
        rank: str,
    ):
        logging.info(f"Command '/pjsk_rankmatch_song' invoked by {interaction.user.name} (ID: {interaction.user.id}).")
        
        try:
            await interaction.response.defer(ephemeral=False)
            logging.info(f"Successfully deferred interaction for '{interaction.command.name}'.")
        except discord.errors.NotFound:
            logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound). This will be caught by global error handler.", exc_info=True)
            return
        except Exception as e:
            logging.error(f"Unexpected error during defer for '{interaction.command.name}': {e}", exc_info=True)
            return

        if not self.bot.is_bot_ready:
            logging.warning(f"Bot not ready for command '{interaction.command.name}'. User: {interaction.user.name}. Sending 'bot not ready' message via followup.")
            await interaction.followup.send("ボットがまだ起動中です。しばらくお待ちください。", ephemeral=True)
            return

        # ★修正: 楽曲データをボットインスタンスから直接取得★
        songs_data = self.bot.proseka_songs_data
        # song_data_map は pjsk_rankmatch_song では直接使われていないため、ここでは取得しない

        if not songs_data: # ★修正: self.songs_data ではなく songs_data をチェック★
            logging.warning(f"songs_data is empty for '{interaction.command.name}'. Sending error message.")
            await interaction.followup.send("現在、楽曲データが読み込まれていません。ボットのログを確認してください。", ephemeral=False)
            return
        
        rank_info = self.RANK_LEVEL_MAP.get(rank)
        if not rank_info:
            logging.warning(f"Invalid rank '{rank}' provided for '{interaction.command.name}'.")
            await interaction.followup.send(f"指定されたランク `{rank}` は無効です。有効なランクは {', '.join(self.RANK_LEVEL_MAP.keys())} です。", ephemeral=False)
            return

        eligible_songs = []

        for song in songs_data: # ★修正: self.songs_data ではなく songs_data を使用★
            candidate_difficulties_with_ranges = []

            target_difficulties_for_check = ["HARD", "EXPERT", "MASTER"]
            if rank_info["append_allowed"]:
                target_difficulties_for_check.append("APPEND")

            for selected_difficulty_upper in target_difficulties_for_check:
                level = self._get_difficulty_level(song, selected_difficulty_upper)

                if level is None:
                    continue

                current_level_min, current_level_max = (0, 0)

                if selected_difficulty_upper == "APPEND":
                    if rank == "ダイヤモンド":
                        current_level_min, current_level_max = rank_info.get("normal_append", (0, 0))
                    elif rank == "マスター":
                        current_level_min, current_level_max = rank_info.get("master_append", (0, 0))
                    else:
                        continue
                else:
                    current_level_min, current_level_max = rank_info.get("normal", (0, 0))

                if current_level_min <= level <= current_level_max:
                    candidate_difficulties_with_ranges.append({
                        "difficulty": selected_difficulty_upper,
                        "level": level,
                        "level_range_for_display": (current_level_min, current_level_max)
                    })

            if candidate_difficulties_with_ranges:
                song_copy = song.copy()
                song_copy["_candidate_difficulties_with_ranges"] = candidate_difficulties_with_ranges
                eligible_songs.append(song_copy)

        if not eligible_songs:
            logging.info(f"No eligible songs found for rank '{rank}' for command '{interaction.command.name}'.")
            await interaction.followup.send(f"申し訳ありません、指定された条件（ランク: {rank}）に合う楽曲が見つかりませんでした。", ephemeral=False)
            return

        selected_song_candidate = random.choice(eligible_songs)
        chosen_difficulty_info = random.choice(selected_song_candidate["_candidate_difficulties_with_ranges"])

        selected_difficulty_for_display = chosen_difficulty_info["difficulty"]
        actual_level = chosen_difficulty_info["level"]
        display_level_min, display_level_max = chosen_difficulty_info["level_range_for_display"]

        embed_color = self.DIFFICULTY_COLORS.get(selected_difficulty_for_display, discord.Color.blue())

        level_display_str = f"Lv.{actual_level} ({display_level_min}-{display_level_max})" if actual_level is not None else "(レベル情報なし)"

        rank_emoji = self.RANK_EMOJIS.get(rank, "🎧")

        embed = discord.Embed(
            title=f"{rank_emoji} {selected_song_candidate['title']}",
            description=f"難易度: **{selected_difficulty_for_display}** {level_display_str}\nランク: **{rank}**",
            color=embed_color
        )
        if selected_song_candidate.get("image_url"):
            embed.set_thumbnail(url=selected_song_candidate["image_url"])

        await interaction.followup.send(embed=embed, ephemeral=False)
        logging.info(f"Successfully sent song selection for '{interaction.command.name}'. Song: {selected_song_candidate['title']}, Difficulty: {selected_difficulty_for_display}.")

        # ここからAP/FCレート表示部分 (ap_fc_rate_cog が存在する場合にのみ実行)
        if self.ap_fc_rate_cog and self.should_update_ap_fc_rate_display:
            try:
                # ユーザーのAP/FCレート表示を更新 (ap_fc_rate_cogが実装されていれば)
                await self.ap_fc_rate_cog.update_ap_fc_rate_display(interaction.user.id, interaction.channel)
                logging.info("AP/FC rate display updated for /pjsk_rankmatch_song.")
            except Exception as e:
                logging.error(f"Error updating AP/FC rate display for /pjsk_rankmatch_song: {e}", exc_info=True)
        else:
            logging.info("AP/FC rate display update skipped for /pjsk_rankmatch_song (cog not available or auto-update disabled).")

# ★修正: pjsk_rankmatch_settings コマンドと pjsk_clear_rankmatch_history コマンドを削除★

async def setup(bot):
    cog = ProsekaRankMatchCommands(bot)
    await bot.add_cog(cog)
    logging.info("ProsekaRankMatchCommands cog loaded.")

