# cogs/help_command.py

import discord
from discord.ext import commands
from discord import app_commands
import logging

# main.pyから必要なグローバルチェック関数をインポート
from main import is_not_admin_mode_for_non_owner, is_owner_global

class HelpCommand(commands.Cog):
    """
    Cog for providing custom help commands.
    ボットのカスタムヘルプコマンドを提供するコグです。
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logging.info("HelpCommand Cog initialized.") # コグの初期化ログ

    @app_commands.command(name="help", description="ボットのコマンドリストを表示します。")
    @is_not_admin_mode_for_non_owner() # ★追加: 管理者モードチェックを適用★
    async def help_command(self, interaction: discord.Interaction):
        """
        Slash command to display the bot's command list.
        ボットのコマンドリストを表示するスラッシュコマンドです。
        """
        # Discord Embedの作成
        embed = discord.Embed(
            title="ボットヘルプ", # 埋め込みのタイトル
            description="このボットが提供するコマンドのリストです。\n\n"
                        "ボットが**管理者モード**の場合、製作者以外のユーザーはほとんどのコマンドを使用できません。", # 埋め込みの説明
            color=discord.Color.blue() # 埋め込みの色
        )
        
        # 各コマンドの説明をフィールドとして追加
        embed.add_field(name="`/pjsk_list_songs`", value="プロセカの楽曲リストをソート・フィルター付きで表示します。", inline=False)
        embed.add_field(name="`/pjsk_search_song <query>`", value="プロセカの楽曲を検索します。(未実装)", inline=False) # 未実装であることを明記
        embed.add_field(name="`/pjsk_random_song`", value="プロセカの楽曲からランダムで1曲選曲します。難易度・レベル指定可。", inline=False) 
        embed.add_field(name="`/pjsk_rankmatch_song`", value="ランクマッチで推奨される楽曲を表示します。", inline=False)
        embed.add_field(name="`/pjsk_record_result`", value="楽曲の精度記録を管理します。", inline=False)
        embed.add_field(name="`/pjsk_rankmatch_result`", value="ランクマッチの結果を投稿・集計します。(最大5人対応)", inline=False)
        embed.add_field(name="`/premium_info`", value="あなたのプレミアムステータスを表示します。", inline=False)
        embed.add_field(name="`/link_patreon`", value="PatreonアカウントとDiscordアカウントを連携します。", inline=False) # <email>を削除 (引数は不要なため)
        
        embed.add_field(name="--- オーナー専用コマンド (製作者のみ利用可能) ---", value="これらのコマンドはボットの製作者のみが使用できます。", inline=False)
        embed.add_field(name="`/set_status <status>`", value="ボットのステータスを設定し、管理者モードを切り替えます。", inline=False)
        embed.add_field(name="`/debug_status`", value="ボットの現在の管理者モード状態とオーナーIDを表示します。", inline=False)
        embed.add_field(name="`/sync_patrons`", value="Patreonメンバーを強制的に同期します。", inline=False)
        embed.add_field(name="`/grant_premium <user>`", value="指定したユーザーにプレミアム権限を付与します。", inline=False)
        embed.add_field(name="`/revoke_premium <user>`", value="指定したユーザーからプレミアム権限を剥奪します。", inline=False)
        embed.add_field(name="`!sync`", value="スラッシュコマンドを強制的に同期します。", inline=False) # プレフィックスコマンド
        
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
