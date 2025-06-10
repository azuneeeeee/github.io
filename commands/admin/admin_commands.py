import discord
from discord.ext import commands
import discord.app_commands
import os
from dotenv import load_dotenv
import logging
import sys
import json # <-- jsonモジュールをインポート

# === グローバル変数（ファイルからのロードに切り替え） ===
# is_maintenance_mode = False  # <-- この行は削除またはコメントアウト
# is_bot_ready_for_commands = False # <-- この行は削除またはコメントアウト
# main.py と共有するためのグローバル変数定義は、ファイルロード/保存に切り替える

# メンテナンスモードの状態を保存するファイル
MAINTENANCE_FILE = "maintenance_status.json"

# メンテナンスモードの状態をファイルからロードする関数
def load_maintenance_status():
    if os.path.exists(MAINTENANCE_FILE):
        try:
            with open(MAINTENANCE_FILE, 'r') as f:
                data = json.load(f)
                return data.get('is_maintenance_mode', False)
        except json.JSONDecodeError:
            # ファイルが破損している場合、デフォルトでFalse
            logger.error(f"エラー: {MAINTENANCE_FILE} の読み込みに失敗しました。デフォルトの False を使用します。", file=sys.__stderr__)
            return False
    return False # ファイルが存在しない場合もFalse

# メンテナンスモードの状態をファイルに保存する関数
def save_maintenance_status(status: bool):
    try:
        with open(MAINTENANCE_FILE, 'w') as f:
            json.dump({'is_maintenance_mode': status}, f)
        logger.info(f"デバッグ: メンテナンスモードの状態を {MAINTENANCE_FILE} に保存しました: {status}", file=sys.__stdout__)
    except Exception as e:
        logger.error(f"エラー: メンテナンスモードの状態を {MAINTENANCE_FILE} に保存できませんでした: {e}", file=sys.__stderr__)

# 初期ロード
is_maintenance_mode = load_maintenance_status()
is_bot_ready_for_commands = False # これは on_ready で設定するのでここではFalseのまま

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
        # ここは変更なし
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

        # ここでファイルからロードした is_maintenance_mode を使う
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
    @discord.app_commands.guild_only()
    async def maintenance(self, interaction: discord.Interaction, mode: bool):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        global is_maintenance_mode # グローバル変数にアクセス
        is_maintenance_mode = mode # グローバル変数を更新
        save_maintenance_status(mode) # ファイルに保存

        status = "有効" if mode else "無効"
        await interaction.followup.send(f"メンテナンスモードを **{status}** に設定しました。", ephemeral=True)
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) がメンテナンスモードを {status} に切り替えました。")


# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))