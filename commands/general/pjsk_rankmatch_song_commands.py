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

# ランクマッチで選択可能な難易度のリスト（songs.pyのAPPENDを考慮）
RANK_MATCH_VALID_DIFFICULTIES_LOCAL = ["EXPERT", "MASTER", "APPEND"]

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
        # ★★★ここを修正: デフォルト値の None を削除し、必須項目にする★★★
        rank: app_commands.Choice[str]
    ):
        self.logger.info(f"デバッグ: /pjsk_rankmatch_song コマンドが {interaction.user.name} ({interaction.user.id}) によって実行されました。")
        
        # メンテナンスモードのチェックは残す
        if not self.bot.is_bot_ready_for_commands:
            await interaction.response.send_message(
                "Botが現在メンテナンス中のため、このコマンドは利用できません。", ephemeral=True
            )
            return

        # songs.py に楽曲が登録されているか確認
        if not songs.proseka_songs:
            await interaction.response.send_message("現在、登録されている楽曲がありません。", ephemeral=True)
            self.logger.warning("警告: /pjsk_rankmatch_song: songs.proseka_songs が空です。")
            return

        await interaction.response.defer(ephemeral=False)

        songs_to_choose_from = list(songs.proseka_songs) # 全楽曲をコピーしてフィルタリングを開始

        # ランクによるレベル範囲フィルタリング (rankが必須になったため、常に実行)
        selected_rank_value = rank.value # rankが必須なので、Noneチェックは不要
        level_ranges_for_rank = RANK_LEVEL_RANGES.get(selected_rank_value)
        
        if not level_ranges_for_rank:
            await interaction.followup.send(f"指定されたランク `{rank.name}` のレベル範囲情報が見つかりませんでした。")
            self.logger.warning(f"警告: 未知のランク値 '{selected_rank_value}' が指定されました。")
            return

        rank_filtered_songs = []
        for song in songs_to_choose_from:
            song_meets_rank_criteria = False
            
            # EXPERT/MASTERの範囲をチェック
            em_range = level_ranges_for_rank.get("expert_master_range")
            if em_range:
                for diff_upper in ["EXPERT", "MASTER"]: # ランクマッチで対象となる難易度
                    diff_lower = diff_upper.lower()
                    level = song.get(diff_lower)
                    if level is not None and em_range["min"] <= level <= em_range["max"]:
                        song_meets_rank_criteria = True
                        break # この曲はこの範囲で条件を満たした
            
            # APPENDの範囲をチェック
            append_range = level_ranges_for_rank.get("append_range")
            if append_range:
                level = song.get("append") # APPEND難易度のみ
                if level is not None and append_range["min"] <= level <= append_range["max"]:
                    song_meets_rank_criteria = True
            
            if song_meets_rank_criteria:
                rank_filtered_songs.append(song)
        
        if not rank_filtered_songs:
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
        
        songs_to_choose_from = rank_filtered_songs # ランクで絞り込んだ結果を使用

        # countは常に1に固定されるため、ランダム選択は常に1曲
        count = 1 
        if not songs_to_choose_from: # フィルタリングの結果、楽曲が0になった場合
            await interaction.followup.send("選択可能な楽曲がありませんでした。フィルタリング条件を確認してください。") 
            self.logger.warning("警告: 選択可能な楽曲が0のため、コマンドを終了します。")
            return

        selected_songs = random.sample(songs_to_choose_from, count) # countは常に1

        embeds = []
        for song in selected_songs:
            title = song.get("title", "不明な楽曲")
            
            description = ""
            
            difficulty_fields = []
            for diff_upper in songs.VALID_DIFFICULTIES:
                diff_lower = diff_upper.lower()
                level = song.get(diff_lower)
                if level is not None:
                    difficulty_fields.append(f"{diff_upper}: {level}")
            
            if difficulty_fields:
                description += "難易度: " + ", ".join(difficulty_fields)
            else:
                description += "難易度情報なし"


            embed = discord.Embed(
                title=title,
                description=description,
                color=discord.Color.blue()
            )
            if song.get("image_url"):
                embed.set_thumbnail(url=song["image_url"])
            
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