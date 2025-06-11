# commands/general/pjsk_random_song_commands.py

import discord
from discord.ext import commands
import discord.app_commands
import logging
import random

from data import songs # data/songs.py を直接インポート

logger = logging.getLogger(__name__)

# commands/admin/admin_commands.py から not_in_maintenance チェックをインポート
# 同じディレクトリ階層ではないため、commands.admin からインポート
from commands.admin.admin_commands import not_in_maintenance, is_owner_check

class PjskRandomSongCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"デバッグ: コグ {self.qualified_name} がロードされました。")

    @discord.app_commands.command(name="random_song", description="プロセカの登録曲の中からランダムに1曲選曲します。")
    @not_in_maintenance() # メンテナンスモード中は使用不可
    async def random_song(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False) # コマンド応答が遅れる可能性があるため defer
        logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /random_song コマンドを使用しました。")

        try:
            if not songs.proseka_songs:
                await interaction.followup.send("選曲できる曲がデータに登録されていません。")
                logger.warning("警告: data/songs.py の proseka_songs リストが空です。")
                return

            selected_song = random.choice(songs.proseka_songs) # リストからランダムに1曲選択

            # 埋め込みメッセージ用に曲情報を整形
            title = selected_song.get("title", "不明な曲名")
            image_url = selected_song.get("image_url") # 画像URLはオプション

            # songs.py にある VALID_DIFFICULTIES を使って難易度情報を整形
            difficulty_info = []
            for diff_key_upper in songs.VALID_DIFFICULTIES:
                diff_key_lower = diff_key_upper.lower()
                level = selected_song.get(diff_key_lower)
                if level is not None:
                    difficulty_info.append(f"{diff_key_upper.capitalize()}: {level}")
            difficulty_str = ", ".join(difficulty_info) if difficulty_info else "難易度情報なし"

            # songs.py の例に artist, unit, event がないので、デフォルト値を入れる
            artist = selected_song.get("artist", "情報なし")
            unit = selected_song.get("unit", "情報なし")
            event = selected_song.get("event", "情報なし")


            embed = discord.Embed(
                title=f"🎧 {title}",
                description=(
                    f"**アーティスト:** {artist}\n"
                    f"**ユニット:** {unit}\n"
                    f"**イベント:** {event}\n"
                    f"**難易度:** {difficulty_str}"
                ),
                color=discord.Color.blue()
            )
            if image_url:
                embed.set_thumbnail(url=image_url)

            embed.set_footer(text="プロセカ ランダム選曲")

            await interaction.followup.send(embed=embed)
            logger.info(f"ランダム選曲: '{title}' をユーザー {interaction.user.name} に送信しました。")

        except ImportError:
            logger.error("エラー: data/songs.py が見つからないか、インポートできませんでした。", exc_info=True)
            await interaction.followup.send("曲データを読み込めませんでした。ボットの管理者に連絡してください。")
        except Exception as e:
            logger.error(f"エラー: ランダム選曲中に予期せぬエラーが発生しました: {e}", exc_info=True)
            await interaction.followup.send("選曲中に予期せぬエラーが発生しました。")


# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(PjskRandomSongCommands(bot))