import discord
from discord.ext import commands
import discord.app_commands
import logging

# data/songs.py から情報をインポート
try:
    from data import songs
except ImportError:
    logging.critical("致命的なエラー: data/songs.py が見つからないか、インポートできませんでした。")
    raise SystemExit("data/songs.py が見つかりません。")

# admin_commands から not_in_maintenance をインポート
from commands.admin.admin_commands import not_in_maintenance

logger = logging.getLogger(__name__)

class PjskListSongCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("PjskListSongCommandsコグが初期化されています。")

    # 利用可能な難易度タイプを定義 (小文字で内部処理、大文字で表示) - この部分はもう使われませんが、削除しても良いです
    ALL_DIFFICULTY_TYPES = ["easy", "normal", "hard", "expert", "master", "append"]
    DISPLAY_DIFFICULTY_TYPES = {
        "easy": "EASY",
        "normal": "NORMAL",
        "hard": "HARD",
        "expert": "EXPERT",
        "master": "MASTER",
        "append": "APPEND"
    }

    @discord.app_commands.command(name="pjsk_list_song", description="プロセカの全曲リスト（最初の10曲）を表示します。")
    @not_in_maintenance() # メンテナンスモード中は利用不可
    async def pjsk_list_song(
        self,
        interaction: discord.Interaction
    ):
        await interaction.response.defer() # 処理に時間がかかる可能性があるため、deferで応答を保留

        if not songs.proseka_songs:
            await interaction.followup.send("曲データが見つかりませんでした。", ephemeral=True)
            logger.warning("警告: /pjsk_list_song コマンドが実行されましたが、proseka_songs が空でした。")
            return

        try:
            # 全曲を対象とする
            filtered_songs = list(songs.proseka_songs) 

            if not filtered_songs:
                await interaction.followup.send(
                    "曲データが見つかりませんでした。",
                    ephemeral=True
                )
                logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song コマンドを使用しましたが、曲が見つかりませんでした。")
                return

            # 結果のソート (タイトル順)
            filtered_songs.sort(key=lambda s: s.get('title', ''))

            # ★★★ Embedに表示する文字列を生成 (最初の10曲のみ、難易度情報なし) ★★★
            song_entries = []
            for i, song in enumerate(filtered_songs):
                if i >= 10: # 10曲で停止
                    break
                song_entry = f"**{song.get('title', 'タイトル不明')}**\n"
                song_entries.append(song_entry)

            # ★★★ 単一のEmbedを作成して送信するロジック ★★★
            full_description = "".join(song_entries)

            if not full_description:
                full_description = "表示できる曲がありませんでした。" # 念のため空の場合のメッセージ

            embed = discord.Embed(
                title="プロセカ楽曲リスト (最初の10曲)",
                description=full_description,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"全{len(filtered_songs)}件中、最初の{min(len(filtered_songs), 10)}件を表示")
            
            await interaction.followup.send(embed=embed)
            logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /pjsk_list_song コマンドを使用しました。最初の{min(len(filtered_songs), 10)}件の曲が単一のEmbedで表示されました。")

        except Exception as e:
            await interaction.followup.send(f"曲リストの取得中にエラーが発生しました: {e}", ephemeral=True)
            logger.error(f"エラー: /pjsk_list_song コマンドの実行中に予期せぬエラーが発生しました: {e}", exc_info=True)

    async def cog_load(self):
        logger.info("PjskListSongCommandsコグがロードされました。")

    async def cog_unload(self):
        logger.info("PjskListSongCommandsコグがアンロードされました。")

async def setup(bot):
    await bot.add_cog(PjskListSongCommands(bot))