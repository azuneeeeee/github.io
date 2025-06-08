import discord
from discord.ext import commands
import discord.app_commands
import os
from dotenv import load_dotenv
import logging
import sys # デバッグ用に追加

# main.py と共有するためのグローバル変数を定義
is_maintenance_mode = False 
is_bot_ready_for_commands = False 

load_dotenv() 

OWNER_ID = int(os.getenv('DISCORD_OWNER_ID')) if os.getenv('DISCORD_OWNER_ID') else None

logger = logging.getLogger(__name__)

def is_owner():
    async def predicate(interaction: discord.Interaction):
        # デバッグ用に追加: ユーザーのIDと設定されたオーナーIDを表示
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
        # まず defer を実行し、Discord API のタイムアウト (3秒) を回避する
        # ephemeral=True を設定し、一時的な「thinking...」メッセージも実行者のみに見えるようにする
        await interaction.response.defer(ephemeral=True, thinking=True) 

        # ボットがコマンド受付準備ができていない場合は、全員アクセスを拒否
        if not is_bot_ready_for_commands:
            # defer しているので followup.send を使う
            await interaction.followup.send(
                "現在ボットは起動準備中のため、このコマンドは使用できません。\n"
                "しばらく時間をおいてから再度お試しください。", 
                ephemeral=True
            )
            return False

        # ボットがコマンド受付準備ができていて、かつメンテナンスモードがオンで、
        # 実行者が製作者でない場合に制限
        if is_maintenance_mode and interaction.user.id != OWNER_ID:
            # defer しているので followup.send を使う
            await interaction.followup.send(
                "現在ボットはメンテナンス中のため、このコマンドは使用できません。", 
                ephemeral=True
            )
            return False
        
        # チェックが成功した場合、コマンド本体が further.send を呼び出す
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

        # チェック関数内で既に defer しているので、ここでは defer しない
        # await interaction.response.defer(ephemeral=True, thinking=True) 

        current_status = interaction.guild.me.status 

        if current_status == discord.Status.online:
            new_status = discord.Status.dnd # Do Not Disturb (取り込み中)
            status_message = "取り込み中"
        else:
            new_status = discord.Status.online
            status_message = "オンライン"
        
        current_activity = interaction.guild.me.activity
        await self.bot.change_presence(status=new_status, activity=current_activity)

        # defer しているので followup.send を使う
        await interaction.followup.send(f"ボットのステータスを **{status_message}** に変更しました。", ephemeral=True)

# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))