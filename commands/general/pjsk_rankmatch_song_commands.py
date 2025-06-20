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

        # 楽曲データに、合致する難易度とレベルの情報を一時的に追加する
        eligible_songs_with_details = [] 
        selected_rank_value = rank.value
        level_ranges_for_rank = RANK_LEVEL_RANGES.get(selected_rank_value)
        
        if not level_ranges_for_rank:
            await interaction.followup.send(f"指定されたランク `{rank.name}` のレベル範囲情報が見つかりませんでした。")
            self.logger.warning(f"警告: 未知のランク値 '{selected_rank_value}' が指定されました。")
            return

        for song in songs.proseka_songs:
            # 各楽曲で、ランクのレベル範囲に合致する難易度を探す
            matched_difficulty = None
            matched_level = None

            # EXPERT/MASTERの範囲をチェック
            em_range = level_ranges_for_rank.get("expert_master_range")
            if em_range:
                for diff_upper in ["EXPERT", "MASTER"]:
                    diff_lower = diff_upper.lower()
                    level = song.get(diff_lower)
                    if level is not None and em_range["min"] <= level <= em_range["max"]:
                        matched_difficulty = diff_upper
                        matched_level = level
                        break # 合致するものが見つかったら、この曲のEMチェックは終了
            
            # APPENDの範囲をチェック (EMで見つからなければ)
            if not matched_difficulty: # EMで見つからなかった場合のみAPPENDをチェック
                append_range = level_ranges_for_rank.get("append_range")
                if append_range:
                    level = song.get("append")
                    if level is not None and append_range["min"] <= level <= append_range["max"]:
                        matched_difficulty = "APPEND"
                        matched_level = level
            
            # 合致する難易度が見つかった場合、リストに追加
            if matched_difficulty and matched_level is not None:
                # 曲情報に、合致した難易度とレベルのペアを追加して格納
                song_copy = song.copy() # 元の辞書を変更しないようにコピー
                song_copy['_matched_difficulty'] = matched_difficulty
                song_copy['_matched_level'] = matched_level
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
        
        # 選ばれた曲は常に1曲
        count = 1 
        selected_songs_with_details = random.sample(eligible_songs_with_details, count)

        embeds = []
        for song_detail in selected_songs_with_details:
            title = song_detail.get("title", "不明な楽曲")
            
            # ★★★ここを修正: 一時的に追加した情報を表示に利用★★★
            # 表示する難易度とそのレベルを確定
            difficulty_display = "難易度情報なし"
            if '_matched_difficulty' in song_detail and '_matched_level' in song_detail:
                difficulty_display = f"{song_detail['_matched_difficulty']}: {song_detail['_matched_level']}"
            
            embed = discord.Embed(
                title=title,
                description=difficulty_display, # 修正された難易度表示を使用
                color=discord.Color.blue()
            )
            if song_detail.get("image_url"):
                embed.set_thumbnail(url=song_detail["image_url"])
            
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