import discord
from discord.ext import commands
import discord.app_commands
import time
import logging # <-- loggingモジュールをインポート

# ロガーを取得
logger = logging.getLogger(__name__) # <-- ロガーを定義

class PingCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="ping", description="ボットの応答速度を測定します。")
    async def ping(self, interaction: discord.Interaction):
        # --- ここから追加 ---
        # コマンド実行ログ
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /ping コマンドを使用しました。")
        # --- ここまで追加 ---

        await interaction.response.defer(ephemeral=False, thinking=True) 
        
        websocket_latency = round(self.bot.latency * 1000, 2) 
        
        await interaction.followup.send(
            f"Pong! 🏓\n"
            f"ボットのレイテンシ: `{websocket_latency}ms`\n"
            f"（これはボットとDiscord間のWebSocket接続の遅延です。）"
        )

# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(PingCommand(bot))