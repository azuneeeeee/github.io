# commands/general/pjsk_rankmatch_song_commands.py
import discord
from discord import app_commands
from discord.ext import commands
import random
import datetime
import logging

# data/songs.py から楽曲データをインポート
# songs.py にランクマッチデータがないため、このモジュール内で定義する
try:
    from data import songs
    logger = logging.getLogger(__name__)
    logger.info("デバッグ: data/songs.py を commands/general/pjsk_rankmatch_song_commands.py に正常にインポートしました。")
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("エラー: data/songs.py が見つからないか、インポートできませんでした。一部機能が制限されます。")
    # songs モジュールがない場合のフォールバック
    class SongsMock:
        proseka_songs = []
        VALID_DIFFICULTIES = [] # songs.pyが完全にない場合は空
    songs = SongsMock()


# ★このモジュール内でランクマッチ関連データを定義★
# songs.py を変更しないという制約のため、ここに直接定義します。
# 実際の日付と楽曲に合わせて、この部分を適切に更新してください。
# 例として、今日の日付のランクマッチ楽曲を設定します。
rank_match_songs_by_date_local = {
    # 2025年6月18日の楽曲リスト
    # 実際の「Tell Your World」のタイトルと一致させてください
    "2025-06-18": [
        "Tell Your World"
    ],
    # 例: 明日以降の楽曲を追加する場合はこのように記述
    # (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"): [
    #     "別の楽曲名"
    # ],
    # ... 他の日付 ...
}

# ランクマッチで選択可能な難易度のリスト
# VALID_DIFFICULTIES は songs.py から来るが、ランクマッチに特有の難易度をここに定義
RANK_MATCH_VALID_DIFFICULTIES_LOCAL = ["EXPERT", "MASTER", "APPEND"] # songs.pyのAPPENDを考慮


class PjsekRankMatchSongCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info("デバッグ: PjsekRankMatchSongCommands コグが初期化されました。")

    @app_commands.command(name="pjsk_rankmatch_song", description="今日のランクマッチ楽曲からランダムに選んで表示します。")
    @app_commands.describe(
        count="表示する曲数 (デフォルト: 1曲, 最大: 5曲)",
        difficulty="難易度でフィルタリングします (例: EXPERT, MASTER, APPEND)"
    )
    async def pjsk_rankmatch_song(
        self,
        interaction: discord.Interaction,
        count: app_commands.Range[int, 1, 5] = 1,
        difficulty: str = None
    ):
        self.logger.info(f"デバッグ: /pjsk_rankmatch_song コマンドが {interaction.user.name} ({interaction.user.id}) によって実行されました。")
        self_check_ready = self.bot.get_cog("AdminCommands")
        if self_check_ready and not self_check_ready.is_bot_ready_for_commands():
            await interaction.response.send_message(
                "Botが現在メンテナンス中のため、このコマンドは利用できません。", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=False) # コマンド応答を遅延

        # 今日の日付を取得 (JST)
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        jst_offset = datetime.timedelta(hours=9)
        jst_today = (utc_now + jst_offset).date()
        today_str = jst_today.strftime("%Y-%m-%d")

        self.logger.debug(f"デバッグ: 今日の日付 (JST): {today_str}")

        # ★モジュール内で定義されたランクマッチ楽曲リストを使用★
        current_rank_match_songs_names = rank_match_songs_by_date_local.get(today_str)

        if not current_rank_match_songs_names:
            await interaction.followup.send(
                f"申し訳ありません。今日の ({today_str}) ランクマッチ楽曲情報は見つかりませんでした。\n"
                "このボットのデータが更新されていないか、日付が変わった可能性があります。"
            )
            self.logger.warning(f"警告: 今日のランクマッチ楽曲情報 ({today_str}) が見つかりませんでした。")
            return

        # 楽曲名から楽曲オブジェクトを検索
        available_songs = []
        for song_name in current_rank_match_songs_names:
            found_song = next((s for s in songs.proseka_songs if s.get("title") == song_name), None)
            if found_song:
                available_songs.append(found_song)
            else:
                self.logger.warning(f"警告: ランクマッチ楽曲リストにある '{song_name}' が songs.py の proseka_songs で見つかりませんでした。")

        if not available_songs:
            await interaction.followup.send("今日のランクマッチ楽曲リストに登録されている曲の詳細情報が songs.py に見つかりませんでした。データを確認してください。")
            self.logger.warning("警告: ランクマッチ楽曲名リストは取得できましたが、proseka_songsからの詳細情報が見つかりませんでした。")
            return

        # 難易度フィルタリング
        filtered_songs = []
        if difficulty:
            selected_difficulty_upper = difficulty.upper() # 大文字に変換して比較
            # ★モジュール内で定義されたランクマッチ難易度リストを使用★
            if selected_difficulty_upper not in RANK_MATCH_VALID_DIFFICULTIES_LOCAL:
                await interaction.followup.send(f"指定された難易度 `{difficulty}` はランクマッチでは選択できません。選択可能な難易度: {', '.join(RANK_MATCH_VALID_DIFFICULTIES_LOCAL)}")
                return

            # 難易度キーは小文字なので変換
            selected_difficulty_lower = selected_difficulty_upper.lower() 
            for song in available_songs:
                if selected_difficulty_lower in song and song[selected_difficulty_lower] is not None:
                    filtered_songs.append(song)
            
            if not filtered_songs:
                await interaction.followup.send(f"今日のランクマッチ楽曲の中から、指定された難易度 `{difficulty}` の譜面を持つ曲は見つかりませんでした。")
                self.logger.info(f"情報: 今日のランクマッチ楽曲から、指定難易度 '{difficulty}' の曲が見つかりませんでした。")
                return
            
            songs_to_choose_from = filtered_songs
        else:
            songs_to_choose_from = available_songs
        
        # ランダム選択
        if len(songs_to_choose_from) < count:
            count = len(songs_to_choose_from)
            if count == 0:
                await interaction.followup.send("選択可能な楽曲がありませんでした。")
                self.logger.warning("警告: 選択可能な楽曲が0のため、コマンドを終了します。")
                return
            await interaction.followup.send(f"選択可能な楽曲が指定された曲数より少ないため、{count}曲表示します。")

        selected_songs = random.sample(songs_to_choose_from, count)

        embeds = []
        for song in selected_songs:
            title = song.get("title", "不明な楽曲")
            # artist キーがないため、表示を調整
            # artist = song.get("artist", "不明なアーティスト")
            
            description = ""
            
            difficulty_fields = []
            # songs.VALID_DIFFICULTIES は songs.py から正しく読み込まれる前提
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