import discord
from discord.ext import commands
import discord.app_commands

# ボットの製作者IDを格納する変数
OWNER_ID = None # main.py からも参照される

# 取り込み中モードの状態を管理する変数
is_maintenance_mode = False # main.py からも参照される

# 製作者のみがコマンドを使えるようにするチェック関数（app_commands 用）
def is_owner():
    async def predicate(interaction: discord.Interaction):
        if OWNER_ID is None:
            await interaction.response.send_message("エラー: ボットの製作者IDが設定されていません。", ephemeral=True)
            return False
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("あなたはボットの製作者ではありません。このコマンドは使用できません。", ephemeral=True)
            return False
        return True
    return discord.app_commands.check(predicate)

# 取り込み中モード中に特定のコマンドを制限するチェック関数（app_commands 用）
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

    # --- 製作者専用コマンド群 ---

    # @discord.app_commands.command(name="set_owner", description="ボットの製作者IDを設定します (初回のみ)。") # 削除
    # @is_owner()
    # async def set_owner(self, interaction: discord.Interaction, user_id: str):
    #     # ... 処理 ...

    # @discord.app_commands.command(name="owner_status", description="現在の製作者IDを表示します。") # 削除
    # @is_owner()
    # async def owner_status(self, interaction: discord.Interaction):
    #     # ... 処理 ...

    # @discord.app_commands.command(name="toggle_maintenance", description="ボットのメンテナンスモードを切り替えます。") # 削除
    # @is_owner()
    # async def toggle_maintenance(self, interaction: discord.Interaction):
    #     # ... 処理 ...

    @discord.app_commands.command(name="maintenance_status", description="現在のメンテナンスモードの状態を表示します。")
    @is_owner() # メンテナンスモードは製作者しか操作・確認できないため、製作者チェックは残す
    async def maintenance_status(self, interaction: discord.Interaction):
        status = "オン" if is_maintenance_mode else "オフ"
        await interaction.response.send_message(f"現在のメンテナンスモードは **{status}** です。", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
