import discord
from discord.ext import commands
import discord.app_commands
import os
from dotenv import load_dotenv
import logging

# main.py と共有するためのグローバル変数を定義
is_maintenance_mode = False 
is_bot_ready_for_commands = False 

load_dotenv() 

OWNER_ID = int(os.getenv('DISCORD_OWNER_ID')) if os.getenv('DISCORD_OWNER_ID') else None

logger = logging.getLogger(__name__)

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
        # --- ここに defer を追加 ---
        # ephemeral=True を設定し、一時的な「thinking...」メッセージも実行者のみに見えるようにする
        await interaction.response.defer(ephemeral=True, thinking=True) 
        # --- 追加ここまで ---

        # ボットがコマンド受付準備ができていない場合は、全員アクセスを拒否
        if not is_bot_ready_for_commands:
            await interaction.followup.send( # deferしているので followup.send を使う
                "現在ボットは起動準備中のため、このコマンドは使用できません。\n"
                "しばらく時間をおいてから再度お試しください。", 
                ephemeral=True
            )
            return False

        # ボットがコマンド受付準備ができていて、かつメンテナンスモードがオンで、
        # 実行者が製作者でない場合に制限
        if is_maintenance_mode and interaction.user.id != OWNER_ID:
            await interaction.followup.send( # deferしているので followup.send を使う
                "現在ボットはメンテナンス中のため、このコマンドは使用できません。", 
                ephemeral=True
            )
            return False
        
        # defer しているので、何らかのメッセージを送らないと interaction は開かれたままになる。
        # コマンドが許可された場合は、ここで defer を解除する必要はない。
        # コマンド自体がその後の応答を行うため。
        
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

        # コマンドレベルの defer は、チェック内で既に defer しているので不要になる
        # await interaction.response.defer(ephemeral=True, thinking=True) 
        # ただし、安全のため残しておくか、ロジックを再考してもよい。
        # 今回はチェック内で defer しているため、この行は削除またはコメントアウトしても動作するはず。
        # コマンドの実行は成功するため、実際にはここには到達しない可能性がある。
        # コマンド本体で defer する場合は、チェック関数内では send_message を使うべき。
        # 今回はチェック関数が最終的なメッセージを送るため、この行は削除します。

        current_status = interaction.guild.me.status 

        if current_status == discord.Status.online:
            new_status = discord.Status.dnd 
            status_message = "取り込み中"
        else:
            new_status = discord.Status.online
            status_message = "オンライン"
        
        current_activity = interaction.guild.me.activity
        await self.bot.change_presence(status=new_status, activity=current_activity)

        # チェック関数内で defer しているので、followup.send を使う
        await interaction.followup.send(f"ボットのステータスを **{status_message}** に変更しました。", ephemeral=True)

# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))