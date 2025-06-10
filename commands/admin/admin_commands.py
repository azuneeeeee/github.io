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
        # deferはここで一度だけ、必要に応じて行う
        # このデコレータが適用される全てのコマンドがdeferを必要とするわけではないため、
        # deferの判断をより柔軟にするか、コマンド内でdeferするかを検討
        # ただし、現在のping_command.pyがdefer前提のfollowup.sendを使っているので、
        # ここでdeferを実行し、ephemeral=Falseを設定することでping_commandの動作を保証します。

        # 既にresponseが送信されているか、defer済みでないか確認
        if not interaction.response.is_done():
            # pingコマンドはephemeral=Falseを意図しているので、ここではephemeral=Falseでdeferする
            # thinking=Trueはメッセージが表示されるまでの「ボットが考えている」表示
            await interaction.response.defer(ephemeral=False, thinking=True)
            print(f"デバッグ: not_in_maintenanceチェック: defer実行 (ユーザーID={interaction.user.id}, interaction ID={interaction.id})", file=sys.stdout)


        # ボットがまだコマンドを受け付ける準備ができていない場合は、全員アクセスを拒否
        if not is_bot_ready_for_commands:
            # defer済みなのでfollowup.sendを使う
            await interaction.followup.send(
                "現在ボットは起動準備中のため、このコマンドは使用できません。\n"
                "しばらく時間をおいてから再度お試しください。",
                ephemeral=True # エラーメッセージは通常エフェメラル
            )
            return False

        # ボットがコマンド受付準備ができていて、かつメンテナンスモードがオンで、
        # 実行者が製作者でない場合にコマンドを制限
        if is_maintenance_mode and interaction.user.id != OWNER_ID:
            # defer済みなのでfollowup.sendを使う
            await interaction.followup.send(
                "現在ボットはメンテナンス中のため、このコマンドは使用できません。",
                ephemeral=True # エラーメッセージは通常エフェメラル
            )
            return False
        
        return True # すべてのチェックを通過した場合、Trueを返します
    return discord.app_commands.check(predicate)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="status_toggle", description="ボットのDiscordステータス（オンライン/取り込み中）を切り替えます。")
    @is_owner()
    @not_in_maintenance()
    async def status_toggle(self, interaction: discord.Interaction):
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /status_toggle コマンドを使用しました。")

        # not_in_maintenance() で既に defer されているため、ここでは defer は不要です。
        # defer が ephemeral=False で行われているため、このメッセージは公開されます。
        # await interaction.response.defer(ephemeral=True, thinking=True) # <= この行は削除

        current_status = interaction.guild.me.status

        if current_status == discord.Status.online:
            new_status = discord.Status.dnd # Do Not Disturb (取り込み中)
            status_message = "取り込み中"
        else:
            new_status = discord.Status.online
            status_message = "オンライン"
        
        current_activity = interaction.guild.me.activity
        await self.bot.change_presence(status=new_status, activity=current_activity)

        # deferしているのでfollowup.sendを使います
        await interaction.followup.send(f"ボットのステータスを **{status_message}** に変更しました。", ephemeral=True) # ステータス変更通知はephemeralで
        
    @discord.app_commands.command(name="maintenance", description="ボットのメンテナンスモードを切り替えます (管理者のみ)。")
    @is_owner()
    @app_commands.guild_only() # DMでは実行不可
    async def maintenance(self, interaction: discord.Interaction, mode: bool):
        # maintenance コマンド自体は not_in_maintenance() チェックを回避するため、
        # このコマンドには not_in_maintenance() を適用しません。
        # そのため、このコマンド内で defer を実行する必要があります。
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        global is_maintenance_mode # グローバル変数にアクセス
        is_maintenance_mode = mode
        status = "有効" if mode else "無効"
        await interaction.followup.send(f"メンテナンスモードを **{status}** に設定しました。", ephemeral=True)
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) がメンテナンスモードを {status} に切り替えました。")


# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))