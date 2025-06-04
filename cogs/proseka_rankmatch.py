import discord
from discord.ext import commands
from discord import app_commands
import random
import os
from dotenv import load_dotenv
import traceback
import asyncio # asyncio をインポート

# .envファイルから環境変数を読み込む
load_dotenv()

# main.py の OWNER_ID と同じ値をここに設定してください
# 環境変数から読み込む
_owner_id_str = os.getenv('OWNER_ID')
if _owner_id_str is None:
    print("CRITICAL ERROR: OWNER_ID environment variable is not set. Please set it in Render's Environment settings.")
    # OWNER_IDが設定されていない場合、Botが正しく動作しないことを明確にする
    # int(None)エラーを回避しつつ、問題を早期に発見できるように無効なIDを設定
    OWNER_ID = -1
else:
    try:
        OWNER_ID = int(_owner_id_str)
    except ValueError:
        print(f"CRITICAL ERROR: OWNER_ID environment variable '{_owner_id_str}' is not a valid integer. Please check Render's Environment settings.")
        # 無効な値の場合も無効なIDを設定
        OWNER_ID = -1

# オーナーチェック用の関数 (このファイル内にも定義)
def is_owner_global(interaction: discord.Interaction) -> bool:
    # OWNER_IDが-1の場合は常にFalseを返すことで、未設定時の誤動作を防ぐ
    return interaction.user.id == OWNER_ID and OWNER_ID != -1

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

        self.valid_difficulties = []
        # ★変更: __init__ では songs_data を None に初期化し、非同期でロードする
        self.songs_data = None 

        # 既存のAP/FCレートコグへの参照を保持 (setup時に設定される)
        self.ap_fc_rate_cog = None

        # AP/FCレート表示の更新を有効にするかどうかのフラグ
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

    # ★変更: _load_songs_data を非同期関数にする
    async def _async_load_songs_data(self):
        """
        data/songs.py から楽曲データを非同期で読み込み、self.songs_data に設定します。
        """
        songs_file_path = 'data/songs.py'

        try:
            # ファイルI/Oは同期的なので、ThreadPoolExecutorを使って非同期で実行する
            # これにより、ボットのメインループをブロックしない
            loop = asyncio.get_running_loop()
            with open(songs_file_path, 'r', encoding='utf-8') as f:
                file_content = await loop.run_in_executor(None, f.read)
            
            _globals = {}
            # exec() も同期的なので、executor で実行
            await loop.run_in_executor(None, exec, file_content, _globals)

            loaded_proseka_songs = _globals.get('proseka_songs', [])
            self.valid_difficulties = _globals.get('VALID_DIFFICULTIES', ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"])

            formatted_songs = []
            if not isinstance(loaded_proseka_songs, list):
                print(f"ERROR (rankmatch): proseka_songs in {songs_file_path} is not a list. Type: {type(loaded_proseka_songs)}. Returning empty list.")
                self.songs_data = [] # エラー時も空のリストを設定
                return

            for i, song_item in enumerate(loaded_proseka_songs):
                if not isinstance(song_item, dict):
                    print(f"WARNING (rankmatch): Item {i+1} in proseka_songs from {songs_file_path} is not a dictionary. Skipping: {song_item}")
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
                        formatted_song[diff_name.lower()] = None
                    else:
                        formatted_song[diff_name.lower()] = None

                formatted_songs.append(formatted_song)

            self.songs_data = formatted_songs # 読み込み成功時に設定
            print(f"DEBUG: {songs_file_path} から {len(self.songs_data)} 曲の楽曲データを非同期で正常に読み込みました。")

        except FileNotFoundError:
            print(f"CRITICAL ERROR (rankmatch): {songs_file_path} が見つかりません。'data'フォルダにあることを確認してください。")
            self.songs_data = [] # エラー時も空のリストを設定
        except Exception as e:
            print(f"CRITICAL ERROR (rankmatch): Error executing {songs_file_path} or converting data: {e}.")
            traceback.print_exc()
            self.songs_data = [] # エラー時も空のリストを設定

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
        # コマンド開始直後に遅延応答（defer）を呼び出す
        await interaction.response.defer(ephemeral=False)

        # 楽曲データがまだ読み込まれていない場合は、読み込みを待つ
        if self.songs_data is None:
            await interaction.followup.send("楽曲データを読み込み中です。しばらくお待ちください。", ephemeral=False)
            print("DEBUG: songs_data is None. Waiting for async load to complete.")
            # 必要であれば、ここで少し待機するか、読み込みが完了するまでループする
            # ただし、無限ループにならないよう注意
            # 簡単な方法として、再度コマンド実行を促す
            return

        if not self.songs_data: # 読み込みは完了したが、データが空の場合
            await interaction.followup.send("現在、楽曲データが読み込まれていません。ボットのログを確認してください。", ephemeral=False)
            return

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

        # AP/FCレート表示がある場合、かつ should_update_ap_fc_rate_display が True の場合のみ、既存のメッセージを削除して更新する
        if self.ap_fc_rate_cog and self.should_update_ap_fc_rate_display:
            try:
                await self.ap_fc_rate_cog.update_ap_fc_rate_display(interaction.user.id, interaction.channel)
                print("DEBUG: AP/FC rate display updated for /pjsk_rankmatch_song.")
            except Exception as e:
                print(f"ERROR: Error updating AP/FC rate display for /pjsk_rankmatch_song: {e}")
                traceback.print_exc()
        else:
            print("DEBUG: AP/FC rate display update skipped for /pjsk_rankmatch_song (cog not available or update disabled).")


async def setup(bot):
    cog = ProsekaRankMatchCommands(bot)
    await bot.add_cog(cog)
    print("ProsekaRankMatchCommands cog loaded.")
    # ★追加: コグがロードされた後に非同期で楽曲データを読み込む
    asyncio.create_task(cog._async_load_songs_data())
