import discord
from discord.ext import commands
import discord.app_commands
import os
from dotenv import load_dotenv
import logging

# main.py と共有するためのグローバル変数を定義
# is_maintenance_mode も is_bot_ready_for_commands も main.py から直接参照されるため、
# ここでモジュールスコープで定義し、main.pyからは admin_commands.is_maintenance_mode のようにアクセスします。
is_maintenance_mode = False 
is_bot_ready_for_commands = False 

load_dotenv() 

OWNER_ID = int(os.getenv('DISCORD_OWNER_ID')) if os.getenv('DISCORD_OWNER_ID') else None

logger = logging.getLogger(__name__)

# is_owner と not_in_maintenance は変更なし

def is_owner():
    async def predicate(interaction: discord.Interaction):
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
        if not is_bot_ready_for_commands:
            await interaction.response.send_message(
                "現在ボットは起動準備中のため、このコマンドは使用できません。\n"
                "しばらく時間をおいてから再度お試しください。", 
                ephemeral=True
            )
            return False

        if is_maintenance_mode and interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "現在ボットはメンテナンス中のため、このコマンドは使用できません。", 
                ephemeral=True
            )
            return False
        return True
    return discord.app_commands.check(predicate)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- コマンド名を変更し、ステータス切り替え機能を追加 ---
    @discord.app_commands.command(name="status_toggle", description="ボットのDiscordステータス（オンライン/取り込み中）を切り替えます。")
    @is_owner() # 製作者のみが使用できるようにする
    async def status_toggle(self, interaction: discord.Interaction):
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /status_toggle コマンドを使用しました。")

        await interaction.response.defer(ephemeral=True, thinking=True) 

        # 現在のプレゼンス（ステータス）を取得
        current_status = interaction.guild.me.status # ボット自身のステータス

        # 次のステータスを決定
        if current_status == discord.Status.online:
            new_status = discord.Status.dnd # Do Not Disturb (取り込み中)
            status_message = "取り込み中"
        else:
            new_status = discord.Status.online
            status_message = "オンライン"
        
        # ボットのステータスとカスタムアクティビティを更新
        # アクティビティは現在のものを引き継ぎ、新しいステータスを設定
        current_activity = interaction.guild.me.activity
        await self.bot.change_presence(status=new_status, activity=current_activity)

        await interaction.followup.send(f"ボットのステータスを **{status_message}** に変更しました。", ephemeral=True)

# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))