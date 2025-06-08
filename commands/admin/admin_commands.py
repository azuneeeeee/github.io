import discord
from discord.ext import commands
import discord.app_commands
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
        return True # <-- ここはTrueのままにしておきます
    return discord.app_commands.check(predicate)

def not_in_maintenance():
    async def predicate(interaction: discord.Interaction):
        # --- 追加するデバッグ情報 ---
        print(f"デバッグ: not_in_maintenanceチェック: defer実行前 (ユーザーID={interaction.user.id}, interaction ID={interaction.id})", file=sys.stdout)
        # --- 追加ここまで ---

        await interaction.response.defer(ephemeral=True, thinking=True) 

        # --- 追加するデバッグ情報 ---
        print(f"デバッグ: not_in_maintenanceチェック: defer実行後", file=sys.stdout)
        # --- 追加ここまで ---
        
        # 以下のreturn Trueはそのままにしておきます
        return True # <-- ここもTrueのままにしておきます

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

# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))