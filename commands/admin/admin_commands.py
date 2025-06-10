import discord
from discord.ext import commands
import discord.app_commands # <-- この行を追加
import os
from dotenv import load_dotenv
import logging
import sys

# main.py と共有するためのグローバル変数を定義
is_maintenance_mode = False
is_bot_ready_for_commands = False

load_dotenv()

OWNER_ID = int(os.getenv('DISCORD_OWNER_ID')) if os.getenv('DISCORD_OWNER_ID') else None

logger = logging.getLogger(__name__)

def is_owner():
    async def predicate(interaction: discord.Interaction):
        print(f"デバッグ: is_ownerチェック: ユーザーID={interaction.user.id}, OWNER_ID={OWNER_ID}", file=sys.stdout)

        if OWNER_ID is None:
            await interaction.response.send_message("エラー: ボットの製作者IDが設定されていません。環境変数をご確認ください。", ephemeral=True)
            return False
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("あなたはボットの製作者ではありません。このコマンドは使用できません。", ephemeral=True)
            return False
        return True
    return discord.app_commands.check(predicate)

def not_in_maintenance():
    async def predicate(interaction: discord.Interaction):
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False, thinking=True)
            print(f"デバッグ: not_in_maintenanceチェック: defer実行 (ユーザーID={interaction.user.id}, interaction ID={interaction.id})", file=sys.stdout)

        if not is_bot_ready_for_commands:
            await interaction.followup.send(
                "現在ボットは起動準備中のため、このコマンドは使用できません。\n"
                "しばらく時間をおいてから再度お試しください。",
                ephemeral=True
            )
            return False

        if is_maintenance_mode and interaction.user.id != OWNER_ID:
            await interaction.followup.send(
                "現在ボットはメンテナンス中のため、このコマンドは使用できません。",
                ephemeral=True
            )
            return False
        
        return True
    return discord.app_commands.check(predicate)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="status_toggle", description="ボットのDiscordステータス（オンライン/取り込み中）を切り替えます。")
    @is_owner()
    @not_in_maintenance()
    async def status_toggle(self, interaction: discord.Interaction):
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /status_toggle コマンドを使用しました。")

        current_status = interaction.guild.me.status

        if current_status == discord.Status.online:
            new_status = discord.Status.dnd
            status_message = "取り込み中"
        else:
            new_status = discord.Status.online
            status_message = "オンライン"
        
        current_activity = interaction.guild.me.activity
        await self.bot.change_presence(status=new_status, activity=current_activity)

        await interaction.followup.send(f"ボットのステータスを **{status_message}** に変更しました。", ephemeral=True)
        
    @discord.app_commands.command(name="maintenance", description="ボットのメンテナンスモードを切り替えます (管理者のみ)。")
    @is_owner()
    @discord.app_commands.guild_only() # <-- この行のために import が必要でした
    async def maintenance(self, interaction: discord.Interaction, mode: bool):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        global is_maintenance_mode
        is_maintenance_mode = mode
        status = "有効" if mode else "無効"
        await interaction.followup.send(f"メンテナンスモードを **{status}** に設定しました。", ephemeral=True)
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) がメンテナンスモードを {status} に切り替えました。")


# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))