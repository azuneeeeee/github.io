import discord
from discord.ext import commands
from discord import app_commands
import random
import os
from dotenv import load_dotenv
import traceback

load_dotenv()

_owner_id_str = os.getenv('OWNER_ID')
if _owner_id_str is None:
    print("CRITICAL ERROR: OWNER_ID environment variable is not set. Please set it in Render's Environment settings.")
    OWNER_ID = -1
else:
    try:
        OWNER_ID = int(_owner_id_str)
    except ValueError:
        print(f"CRITICAL ERROR: OWNER_ID environment variable '{_owner_id_str}' is not a valid integer. Please check Render's Environment settings.")
        OWNER_ID = -1

def is_owner_global(interaction: discord.Interaction) -> bool:
    return interaction.user.id == OWNER_ID and OWNER_ID != -1

class ProsekaRankMatchCommands(commands.Cog):
    def __init__(self, bot, songs_data: list = None, valid_difficulties: list = None):
        self.bot = bot
        self.owner_id = OWNER_ID

        self.DIFFICULTY_COLORS = {
            "EASY": discord.Color(0x76B66B),
            "NORMAL": discord.Color(0x56A8DB),
            "HARD": discord.Color(0xFFFF00),
            "EXPERT": discord.Color(0xFF0000),
            "MASTER": discord.Color(0x800080),
            "APPEND": discord.Color(0xFFC0CB)
        }

        self.songs_data = songs_data if songs_data is not None else []
        self.valid_difficulties = valid_difficulties if valid_difficulties is not None else ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"]
        
        self.ap_fc_rate_cog = None

        self.should_update_ap_fc_rate_display = False 
        print(f"INFO: AP/FCレート表示の自動更新は現在 {'有効' if self.should_update_ap_fc_rate_display else '無効'} に設定されています。")

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
    async def pjsk_rankmatch_song(
        self,
        interaction: discord.Interaction,
        rank: str,
    ):
        # ★修正: ボットが完全に準備完了しているかチェック
        if not self.bot.is_bot_ready:
            print(f"DEBUG: Bot not ready for command '{interaction.command.name}'. User: {interaction.user.name}")
            # defer() の前に応答する必要があるため、ここで直接応答を試みる
            # ただし、既にタイムアウトしている可能性もあるため、try-except で囲む
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("ボットがまだ起動中です。しばらくお待ちください。", ephemeral=True)
                return # 応答したら処理を中断
            except discord.errors.InteractionResponded:
                # 既に何らかの理由で応答済みの場合、何もしない（グローバルエラーハンドラーが捕捉する可能性）
                print(f"WARNING: Interaction for '{interaction.command.name}' was already responded to before 'bot not ready' check.")
                return
            except Exception as e:
                print(f"ERROR: Failed to send 'bot not ready' message for '{interaction.command.name}': {e}")
                # ここで例外が発生した場合、defer()も失敗する可能性が高いので、
                # コマンドの残りの処理は実行しない
                return

        # コマンド開始直後に遅延応答（defer）を呼び出す
        # ここで発生する NotFound はグローバルエラーハンドラーで捕捉される
        await interaction.response.defer(ephemeral=False)

        if not self.songs_data:
            await interaction.followup.send("現在、楽曲データが読み込まれていません。ボットのログを確認してください。", ephemeral=False)
            return

        rank_info = self.RANK_LEVEL_MAP.get(rank)
        if not rank_info:
            await interaction.followup.send(f"指定されたランク `{rank}` は無効です。有効なランクは {', '.join(self.RANK_LEVEL_MAP.keys())} です。", ephemeral=False)
            return

        eligible_songs = []

        for song in self.songs_data:
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
            embed.set_thumbnail(url=selected_song["image_url"])

        await interaction.followup.send(embed=embed, ephemeral=False)

        if self.ap_fc_rate_cog and self.should_update_ap_fc_rate_display:
            try:
                await self.ap_fc_rate_cog.update_ap_fc_rate_display(interaction.user.id, interaction.channel)
                print("DEBUG: AP/FC rate display updated for /pjsk_rankmatch_song.")
            except Exception as e:
                print(f"ERROR: Error updating AP/FC rate display for /pjsk_rankmatch_song: {e}")
                traceback.print_exc()
        else:
            print("DEBUG: AP/FC rate display update skipped for /pjsk_rankmatch_song (cog not available or update disabled).")


async def setup(bot, songs_data: list, valid_difficulties: list):
    cog = ProsekaRankMatchCommands(bot, songs_data=songs_data, valid_difficulties=valid_difficulties)
    await bot.add_cog(cog)
    print("ProsekaRankMatchCommands cog loaded.")
