# commands/general/ping_commands.py (内容変更なし)

import discord
from discord.ext import commands
import discord.app_commands
import logging

logger = logging.getLogger(__name__)

from commands.admin.admin_commands import not_in_maintenance, is_owner

class PingCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        logger.info(f"デバッグ: コグ {self.qualified_name} がロードされました。")

    @discord.app_commands.command(name="ping", description="ボットのレイテンシを表示します。")
    @not_in_maintenance()
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        latency = round(self.bot.latency * 1000)
        await interaction.followup.send(f"Pong! 🏓 レイテンシ: `{latency}ms`")
        logger.info(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /ping コマンドを使用しました。レイテンシ: {latency}ms")

async def setup(bot):
    await bot.add_cog(PingCommands(bot))