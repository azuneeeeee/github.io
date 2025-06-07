import discord
from discord.ext import commands
import discord.app_commands
import os
from dotenv import load_dotenv

load_dotenv() 

OWNER_ID = int(os.getenv('DISCORD_OWNER_ID')) if os.getenv('DISCORD_OWNER_ID') else None

is_maintenance_mode = False 

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
        if is_maintenance_mode and interaction.user.id != OWNER_ID:
            await interaction.response.send_message("現在ボットはメンテナンス中のため、このコマンドは使用できません。", ephemeral=True)
            return False
        return True
    return discord.app_commands.check(predicate)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="maintenance_status", description="現在のメンテナンスモードの状態を表示します。")
    @is_owner()
    async def maintenance_status(self, interaction: discord.Interaction):
        # --- ここから追加/修正 ---
        # コマンドを受け取ったことをDiscordに通知 (3秒のタイムアウト回避)
        await interaction.response.defer(ephemeral=True, thinking=True) 
        # ephemeral=True は製作者のみに見えるようにするため
        # thinking=True は "Bot is thinking..." の表示を出すため

        status = "オン" if is_maintenance_mode else "オフ"
        # defer 後の応答は followuo.send_message を使用
        await interaction.followup.send(f"現在のメンテナンスモードは **{status}** です。", ephemeral=True)
        # --- ここまで追加/修正 ---

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))