import discord
from discord.ext import commands
import discord.app_commands
import os
from dotenv import load_dotenv

# .envファイルを読み込む (このファイルでOWNER_IDを直接読み込むため)
load_dotenv() 

# ボットの製作者IDを環境変数から直接読み込む
# ファイル冒頭で読み込むことで、is_owner() 関数が定義される時点で値が設定されているようにする
# 環境変数が設定されていない場合でもエラーにならないようにNoneを設定
OWNER_ID = int(os.getenv('DISCORD_OWNER_ID')) if os.getenv('DISCORD_OWNER_ID') else None

# 取り込み中モードの状態を管理する変数 (main.py からも参照されます)
is_maintenance_mode = False 

# --- 製作者のみがコマンドを使えるようにするチェック関数 ---
def is_owner():
    async def predicate(interaction: discord.Interaction):
        if OWNER_ID is None:
            # 製作者IDが設定されていない場合のエラーメッセージ
            await interaction.response.send_message("エラー: ボットの製作者IDが設定されていません。環境変数をご確認ください。", ephemeral=True)
            return False
        if interaction.user.id != OWNER_ID:
            # 製作者ではない場合のエラーメッセージ
            await interaction.response.send_message("あなたはボットの製作者ではありません。このコマンドは使用できません。", ephemeral=True)
            return False
        return True
    return discord.app_commands.check(predicate)

# --- 取り込み中モード中に特定のコマンドを制限するチェック関数 ---
def not_in_maintenance():
    async def predicate(interaction: discord.Interaction):
        # メンテナンスモード中で、かつユーザーが製作者ではない場合に制限
        if is_maintenance_mode and interaction.user.id != OWNER_ID:
            await interaction.response.send_message("現在ボットはメンテナンス中のため、このコマンドは使用できません。", ephemeral=True)
            return False
        return True
    return discord.app_commands.check(predicate)

# --- AdminCommands コグの定義 ---
class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="maintenance_status", description="現在のメンテナンスモードの状態を表示します。")
    @is_owner() # 製作者チェックを適用
    async def maintenance_status(self, interaction: discord.Interaction):
        status = "オン" if is_maintenance_mode else "オフ"
        await interaction.response.send_message(f"現在のメンテナンスモードは **{status}** です。", ephemeral=True)

# --- コグをボットに追加するためのセットアップ関数 ---
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))