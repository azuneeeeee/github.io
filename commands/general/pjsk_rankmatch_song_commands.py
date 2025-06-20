# commands/general/pjsk_rankmatch_song_commands.py

import discord
from discord import app_commands
from discord.ext import commands
import random
import datetime
import logging

# data/songs.py から楽曲データをインポート
try:
    from data import songs
    logger = logging.getLogger(__name__)
    logger.info("デバッグ: data/songs.py を commands/general/pjsk_rankmatch_song_commands.py に正常にインポートしました。")
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("エラー: data/songs.py が見つからないか、インポートできませんでした。pjsk_rankmatch_song_commands.pyは動作しません。")
    class SongsMock: # songs.py がない場合のフォールバック
        proseka_songs = []
        VALID_DIFFICULTIES = []
    songs = SongsMock()

# このモジュール内でランクマッチ関連データを定義（songs.py を変更しないため）

# ランクとレベル範囲のマッピング
RANK_LEVEL_RANGES = {
    "beginner": {"expert_master_range": {"min": 18, "max": 25}, "append_range": None},
    "bronze":   {"expert_master_range": {"min": 23, "max": 26}, "append_range": None},
    "silver":   {"expert_master_range": {"min": 25, "max": 28}, "append_range": None},
    "gold":     {"expert_master_range": {"min": 26, "max": 30}, "append_range": None},
    "platinum": {"expert_master_range": {"min": 28, "max": 31}, "append_range": None},
    "diamond":  {"expert_master_range": {"min": 29, "max": 32}, "append_range": {"min": 27, "max": 30}},
    "master":   {"expert_master_range": {"min": 30, "max": 37}, "append_range": {"min": 28, "max": 38}},
}

class PjsekRankMatchSongCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("デバッグ: PjsekRankMatchSongCommands コグが初期化されました。")

    # random_song_commands と同じ難易度ごとの色のマッピングを定義
    # DISPLAY_DIFFICULTY_TYPES も合わせて定義し、小文字キーで扱えるようにする
    DIFFICULTY_COLORS = {
        "easy": discord.Color.green(),      # 緑
        "normal": discord.Color.blue(),     # 青
        "hard": discord.Color.yellow(),     # 黄色
        "expert": discord.Color.red(),      # 赤
        "master": discord.Color.purple(),   # 紫
        "append": discord.Color.from_rgb(255, 192, 203), # 桃色 (RGB: R:255, G:192, B:203)
        "default": discord.Color.light_grey() # デフォルトは薄い灰色
    }
    
    # 難易度の表示名を小文字キーで取得できるようにしておく
    DISPLAY_DIFFICULTY_TYPES_LOWER = {
        "easy": "EASY",
        "normal": "NORMAL",
        "hard": "HARD",
        "expert": "EXPERT",
        "master": "MASTER",
        "append": "APPEND"
    }

    @app_commands.command(name="pjsk_rankmatch_song", description="ランクマッチ楽曲からランダムに1曲選びます。")
    @app_commands.describe(
        rank="選曲するランク (Beginner, Bronze, Silver, Gold, Platinum, Diamond, Masterなど)"
    )
    @app_commands.choices(
        rank=[
            app_commands.Choice(name="Beginner", value="beginner"),
            app_commands.Choice(name="Bronze", value="bronze"),
            app_commands.Choice(name="Silver", value="silver"),
            app_commands.Choice(name="Gold", value="gold"),
            app_commands.Choice(name="Platinum", value="platinum"),
            app_commands.Choice(name="Diamond", value="diamond"),
            app_commands.Choice(name="Master", value="master"),
        ]
    )
    async def pjsk_rankmatch_song(
        self,
        interaction: discord.Interaction,
        rank: app_commands.Choice[str]
    ):
        self.logger.info(f"デバッグ: /pjsk_rankmatch_song コマンドが {interaction.user.name} ({interaction.user.id}) によって実行されました。")
        
        if not self.bot.is_bot_ready_for_commands:
            await interaction.response.send_message(
                "Botが現在メンテナンス中のため、このコマンドは利用できません。", ephemeral=True
            )
            return

        if not songs.proseka_songs:
            await interaction.response.send_message("現在、登録されている楽曲がありません。", ephemeral=True)
            self.logger.warning("警告: /pjsk_rankmatch_song: songs.proseka_songs が空です。")
            return

        await interaction.response.defer(ephemeral=False)

        eligible_songs_with_details = [] 
        selected_rank_value = rank.value
        level_ranges_for_rank = RANK_LEVEL_RANGES.get(selected_rank_value)
        
        if not level_ranges_for_rank:
            await interaction.followup.send(f"指定されたランク `{rank.name}` のレベル範囲情報が見つかりませんでした。")
            self.logger.warning(f"警告: 未知のランク値 '{selected_rank_value}' が指定されました。")
            return

        for song in songs.proseka_songs:
            current_song_matched_difficulties = []

            em_range = level_ranges_for_rank.get("expert_master_range")
            if em_range:
                for diff_upper in ["EXPERT", "MASTER"]:
                    diff_lower = diff_upper.lower()
                    level = song.get(diff_lower)
                    if level is not None and em_range["min"] <= level <= em_range["max"]:
                        current_song_matched_difficulties.append((diff_upper, level))
            
            append_range = level_ranges_for_rank.get("append_range")
            if append_range:
                level = song.get("append")
                if level is not None and append_range["min"] <= level <= append_range["max"]:
                    current_song_matched_difficulties.append(("APPEND", level))
            
            if current_song_matched_difficulties:
                song_copy = song.copy()
                song_copy['_all_matched_difficulties'] = current_song_matched_difficulties 
                eligible_songs_with_details.append(song_copy)
        
        if not eligible_songs_with_details:
            range_msgs = []
            if level_ranges_for_rank.get("expert_master_range"):
                em_r = level_ranges_for_rank["expert_master_range"]
                range_msgs.append(f"EXPERT/MASTER ({em_r['min']}~{em_r['max']})")
            if level_ranges_for_rank.get("append_range"):
                ap_r = level_ranges_for_rank["append_range"]
                range_msgs.append(f"APPEND ({ap_r['min']}~{ap_r['max']})")
            
            range_str = " または ".join(range_msgs) if range_msgs else "指定なし"

            await interaction.followup.send(
                f"登録楽曲の中から、ランク `{rank.name}` ({range_str}) に適合する曲は見つかりませんでした。"
            )
            self.logger.info(f"情報: ランク '{rank.name}' ({range_str}) に適合する曲が見つかりませんでした。")
            return
        
        count = 1 
        selected_songs_with_details = random.sample(eligible_songs_with_details, count)

        embeds = []
        for song_detail in selected_songs_with_details:
            title = song_detail.get("title", "不明な楽曲")
            
            difficulty_display = "難易度情報なし"
            embed_color = self.DIFFICULTY_COLORS["default"] # デフォルト色を初期化
            
            if '_all_matched_difficulties' in song_detail and song_detail['_all_matched_difficulties']:
                chosen_diff_info = random.choice(song_detail['_all_matched_difficulties'])
                chosen_diff_upper = chosen_diff_info[0] # 例: "EXPERT"
                chosen_level = chosen_diff_info[1] # 例: 32

                # Embedの表示テキスト
                difficulty_display = f"**{chosen_diff_upper}**: {chosen_level}"
                
                # Embedの色を設定 (小文字にしてからマッピングを探す)
                embed_color = self.DIFFICULTY_COLORS.get(chosen_diff_upper.lower(), self.DIFFICULTY_COLORS["default"])
            
            embed = discord.Embed(
                title=f"🎧 {title}",
                description=difficulty_display,
                color=embed_color # 設定した色を適用
            )
            if song_detail.get("image_url"):
                embed.set_thumbnail(url=song_detail["image_url"])
            
            embed.set_footer(text="プロセカ ランクマッチ楽曲選曲")

            embeds.append(embed)

        await interaction.followup.send(embeds=embeds)
        self.logger.info(f"デバッグ: /pjsk_rankmatch_song コマンドが正常に完了しました。{count}曲を表示しました。")

    # エラーハンドリング
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"このコマンドはクールダウン中です。あと {error.retry_after:.1f} 秒待ってください。", ephemeral=True)
            self.logger.warning(f"警告: コマンドクールダウン: {interaction.user.name} ({interaction.user.id}) - /pjsk_rankmatch_song")
        elif isinstance(error, app_commands.NoPrivateMessage):
            await interaction.response.send_message("このコマンドはDMでは使えません。", ephemeral=True)
            self.logger.warning(f"警告: DMからのコマンド実行: {interaction.user.name} ({interaction.user.id}) - /pjsk_rankmatch_song")
        else:
            self.logger.error(f"エラー: /pjsk_rankmatch_song コマンドで予期せぬエラーが発生しました: {error}", exc_info=True)
            await interaction.response.send_message(f"コマンドの実行中にエラーが発生しました。\nエラー内容: `{error}`", ephemeral=True)


async def setup(bot):
    await bot.add_cog(PjsekRankMatchSongCommands(bot))
    logger = logging.getLogger(__name__)
    logger.info("デバッグ: PjsekRankMatchSongCommands コグがセットアップされました。")