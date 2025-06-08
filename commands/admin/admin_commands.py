import discord
from discord.ext import commands
import discord.app_commands
import os
from dotenv import load_dotenv

load_dotenv() 

OWNER_ID = int(os.getenv('DISCORD_OWNER_ID')) if os.getenv('DISCORD_OWNER_ID') else None

is_maintenance_mode = False 

# is_owner と not_in_maintenance はそのまま維持
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
    # @is_owner() # <-- ここからデコレーターを削除！
    async def maintenance_status(self, interaction: discord.Interaction):
        # --- ここから変更 ---
        # まず、Discordに処理中であることを通知 (最優先)
        await interaction.response.defer(ephemeral=True, thinking=True) 

        # その後、権限チェックを実行
        # is_owner() のロジックをここに直接記述するか、関数を呼び出す
        if OWNER_ID is None:
            await interaction.followup.send("エラー: ボットの製作者IDが設定されていません。環境変数をご確認ください。", ephemeral=True)
            return
        if interaction.user.id != OWNER_ID:
            await interaction.followup.send("あなたはボットの製作者ではありません。このコマンドは使用できません。", ephemeral=True)
            return
        
        # 権限チェックを通過したら、通常のコマンド処理
        status = "オン" if is_maintenance_mode else "オフ"
        await interaction.followup.send(f"現在のメンテナンスモードは **{status}** です。", ephemeral=True)
        # --- ここまで変更 ---

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
