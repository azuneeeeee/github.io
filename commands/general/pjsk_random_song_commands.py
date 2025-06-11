import discord
from discord.ext import commands
import discord.app_commands
import random
import logging

# data/songs.py から情報をインポート
try:
    from data import songs
except ImportError:
    logging.critical("致命的なエラー: data/songs.py が見つからないか、インポートできませんでした。")
    # ボットが起動できないように、ここではエラーを発生させるか、適切なハンドリングを行う
    # 例: raise SystemExit("data/songs.py が見つかりません。")

# admin_commands から not_in_maintenance と is_owner_check をインポート
from commands.admin.admin_commands import not_in_maintenance, is_owner_check

logger = logging.getLogger(__name__)

class PjskRandomSongCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("PjskRandomSongCommandsコグが初期化されています。")

    # コマンド名を 'pjsk_random_song' に変更
    @discord.app_commands.command(name="pjsk_random_song", description="プロセカのランダムな曲を提示します。")
    @not_in_maintenance() # メンテナンスモード中は利用不可
    async def pjsk_random_song(self, interaction: discord.Interaction):
        await interaction.response.defer() # 処理に時間がかかる可能性があるため、deferで応答を保留

        if not songs.proseka_songs:
            await interaction.followup.send("曲データが見つかりませんでした。", ephemeral=True)
            logger.warning("警告: /pjsk_random_song コマンドが実行されましたが、proseka_songs が空でした。")
            return

        try:
            # ランダムに曲を選択
            random_song = random.choice(songs.proseka_songs)

            # 難易度情報を取得し、表示をMasterのみに絞る
            difficulty_info = ""
            if "master" in random_song and random_song["master"] is not None:
                difficulty_info += f"Master: {random_song['master']}"
            elif "expert" in random_song and random_song["expert"] is not None:
                difficulty_info += f"Expert: {random_song['expert']}" # Masterがない場合のフォールバック
            elif "hard" in random_song and random_song["hard"] is not None:
                difficulty_info += f"Hard: {random_song['hard']}" # Expertもない場合のフォールバック
            elif "normal" in random_song and random_song["normal"] is not None:
                difficulty_info += f"Normal: {random_song['normal']}" # Hardもない場合のフォールバック
            elif "easy" in random_song and random_song["easy"] is not None:
                difficulty_info += f"Easy: {random_song['easy']}" # Normalもない場合のフォールバック
            else:
                difficulty_info = "情報なし" # どの難易度情報もない場合

            # 曲のサムネイルURLを安全に取得
            thumbnail_url = random_song.get("thumbnail", None)

            # Embedの作成
            embed = discord.Embed(
                title=f"🎧 {random_song.get('name', 'タイトル情報なし')}",
                color=discord.Color.blue() # プロセカっぽい色 (任意)
            )

            # アーティスト、ユニット、イベントのフィールドを削除
            # embed.add_field(name="アーティスト", value=random_song.get("artist", "情報なし"), inline=False)
            # embed.add_field(name="ユニット", value=random_song.get("unit", "情報なし"), inline=False)
            # embed.add_field(name="イベント", value=random_song.get("event", "情報なし"), inline=False)

            # 難易度情報を単一で追加
            embed.add_field(name="難易度", value=difficulty_info, inline=False)

            # サムネイルがある場合のみ設定
            if thumbnail_url:
                embed.set_thumbnail(url=thumbnail_url)

            embed.set_footer(text="プロセカ ランダム選曲") # フッターはそのまま

            await interaction.followup.send(embed=embed)
            logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_random_song コマンドを使用しました。曲: {random_song.get('name', 'タイトル情報なし')}")

        except Exception as e:
            await interaction.followup.send(f"曲の選曲中にエラーが発生しました: {e}", ephemeral=True)
            logger.error(f"エラー: /pjsk_random_song コマンドの実行中にエラーが発生しました: {e}", exc_info=True)


    async def cog_load(self):
        logger.info("PjskRandomSongCommandsコグがロードされました。")

    async def cog_unload(self):
        logger.info("PjskRandomSongCommandsコグがアンロードされました。")

async def setup(bot):
    await bot.add_cog(PjskRandomSongCommands(bot))