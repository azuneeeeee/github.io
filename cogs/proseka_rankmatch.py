import discord
from discord.ext import commands
from discord import app_commands
import random
import os
from dotenv import load_dotenv
import traceback

# .envファイルから環境変数を読み込む
load_dotenv()

# main.py の OWNER_ID と同じ値をここに設定してください
# 環境変数から読み込む場合は以下のように変更
OWNER_ID = int(os.getenv('OWNER_ID'))

# オーナーチェック用の関数 (このファイル内にも定義)
def is_owner_global(interaction: discord.Interaction) -> bool:
    return interaction.user.id == OWNER_ID

class ProsekaRankMatchCommands(commands.Cog):
    def __init__(self, bot):
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

        # valid_difficulties は _load_songs_data で設定されるため、ここでは初期化のみ
        self.valid_difficulties = []
        # ここで _load_songs_data を呼び出して楽曲データを初期化します
        self.songs_data = self._load_songs_data()

        # 既存のAP/FCレートコグへの参照を保持 (setup時に設定される)
        self.ap_fc_rate_cog = None # setup時に設定される

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

    def _load_songs_data(self):
        """
        data/songs.py から楽曲データを読み込み、ProsekaGeneralCommands と同じ形式に変換して返します。
        """
        try:
            _globals = {}
            with open('data/songs.py', 'r', encoding='utf-8') as f:
                exec(f.read(), _globals)

            loaded_proseka_songs = _globals.get('proseka_songs', [])
            self.valid_difficulties = _globals.get('VALID_DIFFICULTIES', ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"])

            formatted_songs = []
            if not isinstance(loaded_proseka_songs, list):
                print(f"ERROR (rankmatch): proseka_songs in data/songs.py is not a list. Type: {type(loaded_proseka_songs)}. Returning empty list.")
                return []

            for i, song_item in enumerate(loaded_proseka_songs):
                if not isinstance(song_item, dict):
                    print(f"WARNING (rankmatch): Item {i+1} in proseka_songs is not a dictionary. Skipping: {song_item}")
                    continue

                formatted_song = {
                    "title": song_item.get("title"),
                    "image_url": song_item.get("image_url"),
                }
                for diff_name in self.valid_difficulties:
                    level = song_item.get(diff_name.lower())
                    if isinstance(level, (int, float)):
                        formatted_song[diff_name.lower()] = int(level)
                    elif level is not None:
                        print(f" -> WARNING (rankmatch): Difficulty '{diff_name.lower()}' for song '{song_item.get('title')}' has non-numeric level: {level}. Skipping this difficulty.")

                formatted_songs.append(formatted_song)

            return formatted_songs

        except FileNotFoundError:
            print("CRITICAL ERROR (rankmatch): data/songs.py not found. Please ensure it's in the 'data' folder. Returning empty list.")
            return []
        except Exception as e:
            print(f"CRITICAL ERROR (rankmatch): Error loading data/songs.py or converting data: {e}. Returning empty list.")
            traceback.print_exc()
            return []

    # ProsekaGeneralCommandsの_get_difficulty_levelと同じヘルパー関数をここに実装
    def _get_difficulty_level(self, song: dict, difficulty_name: str) -> int | None:
        """楽曲データから指定された難易度のレベルを取得する"""
        return song.get(difficulty_name.lower())

    # --- ランクマッチ選曲コマンド ---
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
        rank: str,        # 必須引数
    ):
        await interaction.response.defer(ephemeral=False)

        rank_info = self.RANK_LEVEL_MAP.get(rank)
        if not rank_info:
            await interaction.followup.send(f"指定されたランク `{rank}` は無効です。有効なランクは {', '.join(self.RANK_LEVEL_MAP.keys())} です。", ephemeral=False)
            return

        eligible_songs = []

        for song in self.songs_data:
            candidate_difficulties_with_ranges = []

            # HARD, EXPERT, MASTER は常に考慮
            target_difficulties_for_check = ["HARD", "EXPERT", "MASTER"]
            if rank_info["append_allowed"]:
                target_difficulties_for_check.append("APPEND")

            for selected_difficulty_upper in target_difficulties_for_check:
                level = self._get_difficulty_level(song, selected_difficulty_upper)

                if level is None: # レベル情報がない場合はスキップ
                    continue

                current_level_min, current_level_max = (0, 0)

                if selected_difficulty_upper == "APPEND":
                    if rank == "ダイヤモンド":
                        current_level_min, current_level_max = rank_info.get("normal_append", (0, 0))
                    elif rank == "マスター":
                        current_level_min, current_level_max = rank_info.get("master_append", (0, 0))
                    else: # APPENDは許可されているが、特定のランクに合致しない場合
                        continue
                else: # HARD, EXPERT, MASTER の場合
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
            embed.set_thumbnail(url=selected_song_candidate["image_url"])

        await interaction.followup.send(embed=embed, ephemeral=False)

        # AP/FCレート表示がある場合、既存のメッセージを削除して更新する
        # ★ここを修正しました★
        if self.ap_fc_rate_cog:
            try:
                await self.ap_fc_rate_cog.update_ap_fc_rate_display(interaction.user.id, interaction.channel)
                print("DEBUG: AP/FC rate display updated for /pjsk_rankmatch_song.")
            except Exception as e:
                print(f"ERROR: Error updating AP/FC rate display for /pjsk_rankmatch_song: {e}")
                traceback.print_exc()
        else:
            print("DEBUG: ap_fc_rate_cog not available for /pjsk_rankmatch_song, skipping update.")


async def setup(bot):
    cog = ProsekaRankMatchCommands(bot)
    await bot.add_cog(cog)
    print("ProsekaRankMatchCommands cog loaded.")