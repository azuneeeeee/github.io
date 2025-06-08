import discord
from discord.ext import commands
import discord.app_commands
import time
import logging

# admin_commands.py から not_in_maintenance をインポート
from commands.admin.admin_commands import not_in_maintenance 

logger = logging.getLogger(__name__)

class PingCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="ping", description="ボットの応答速度を測定します。")
    @not_in_maintenance() # not_in_maintenanceチェックを適用
    async def ping(self, interaction: discord.Interaction):
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /ping コマンドを使用しました。")

        # not_in_maintenance() 内で既にdeferされているため、ここではdeferは不要です
        # await interaction.response.defer(ephemeral=False, thinking=True) 
        
        websocket_latency = round(self.bot.latency * 1000, 2) 
        
        # deferされているためfollowup.sendを使います
        await interaction.followup.send(
            f"Pong! 🏓\n"
            f"ボットのレイテンシ: `{websocket_latency}ms`\n"
            f"（これはボットとDiscord間のWebSocket接続の遅延です。）"
        )

# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(PingCommand(bot))