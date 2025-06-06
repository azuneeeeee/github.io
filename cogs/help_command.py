# cogs/help_command.py

import discord
from discord.ext import commands
from discord import app_commands
import logging

# ロギング設定
# main.pyで一元的に行われているため、通常は個々のコグでbasicConfigを設定する必要はありません。
# しかし、独立したファイルとしての実行可能性を考慮して、ここに残します。
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class HelpCommand(commands.Cog):
    """
    Cog for providing custom help commands.
    ボットのカスタムヘルプコマンドを提供するコグです。
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logging.info("HelpCommand Cog initialized.") # コグの初期化ログ

    @app_commands.command(name="help", description="ボットのコマンドリストを表示します。")
    async def help_command(self, interaction: discord.Interaction):
        """
        Slash command to display the bot's command list.
        ボットのコマンドリストを表示するスラッシュコマンドです。
        """
        # Discord Embedの作成
        embed = discord.Embed(
            title="ボットヘルプ", # 埋め込みのタイトル
            description="このボットが提供するコマンドのリストです。", # 埋め込みの説明
            color=discord.Color.blue() # 埋め込みの色
        )
        
        # 各コマンドの説明をフィールドとして追加
        embed.add_field(name="`/pjsk_list_songs`", value="プロセカの楽曲リストをソート・フィルター付きで表示します。", inline=False)
        # TODO: /pjsk_search_song がまだ実装されていませんが、将来的な追加を想定して記載しています。
        # 実際のボットでこのコマンドが利用可能になるには、別途実装が必要です。
        embed.add_field(name="`/pjsk_search_song <query>`", value="プロセカの楽曲を検索します。", inline=False) 
        embed.add_field(name="`/pjsk_random_song`", value="プロセカの楽曲からランダムで1曲選曲します。難易度・レベル指定可。", inline=False) 
        embed.add_field(name="`/pjsk_rankmatch_song`", value="ランクマッチで推奨される楽曲を表示します。", inline=False)
        embed.add_field(name="`/pjsk_record_result`", value="楽曲の精度記録を管理します。", inline=False)
        embed.add_field(name="`/pjsk_rankmatch_result`", value="ランクマッチの結果を投稿・集計します。(最大5人対応)", inline=False)
        embed.add_field(name="`/premium_info`", value="あなたのプレミアムステータスを表示します。", inline=False)
        embed.add_field(name="`/link_patreon <email>`", value="PatreonアカウントとDiscordアカウントを連携します。", inline=False)
        embed.add_field(name="`/set_status <status>` (オーナー限定)", value="ボットのステータスを設定します。", inline=False)
        embed.add_field(name="`!sync` (オーナー限定)", value="スラッシュコマンドを強制的に同期します。", inline=False) # プレフィックスコマンド
        embed.add_field(name="`!check_local_commands` (オーナー限定)", value="ボットが内部で認識しているコマンドを表示します。", inline=False) # プレフィックスコマンド
        
        # 埋め込みのフッター
        embed.set_footer(text="詳細なコマンド説明は順次追加されます。")
        
        # インタラクションに応答（エフェメラル、つまりコマンド実行者のみに見えるメッセージ）
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logging.info(f"Command '/help' invoked by {interaction.user.name}.") # コマンド実行ログ

async def setup(bot):
    """
    Loads the HelpCommand cog into the bot.
    HelpCommandコグをボットにロードする関数です。
    """
    cog = HelpCommand(bot)
    await bot.add_cog(cog)
    logging.info("HelpCommand Cog loaded.") # コグのロード完了ログ
