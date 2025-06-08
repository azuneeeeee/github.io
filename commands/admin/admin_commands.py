import discord
from discord.ext import commands
import discord.app_commands
import os
from dotenv import load_dotenv
import logging

load_dotenv() 

OWNER_ID = int(os.getenv('DISCORD_OWNER_ID')) if os.getenv('DISCORD_OWNER_ID') else None

# is_maintenance_mode は main.py からも更新されるグローバル変数です
is_maintenance_mode = False 
# 新しいグローバル変数：ボットがコマンドを受け付ける準備ができているか
is_bot_ready_for_commands = False # <-- ここを追加。最初はFalse

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

# メンテナンスモード中にコマンドを制限するためのカスタムチェック関数
# 製作者も初期待機中は実行できないようにロジックを変更
def not_in_maintenance():
    async def predicate(interaction: discord.Interaction):
        # --- ここから変更/追加 ---
        # まず、ボットがコマンド受付準備ができていない場合は、全員アクセスを拒否
        if not is_bot_ready_for_commands:
            await interaction.response.send_message(
                "現在ボットは起動準備中のため、このコマンドは使用できません。\n"
                "しばらく時間をおいてから再度お試しください。", 
                ephemeral=True
            )
            return False

        # ボットがコマンド受付準備ができていて、かつメンテナンスモードがオンで、
        # 実行者が製作者でない場合に制限
        if is_maintenance_mode and interaction.user.id != OWNER_ID:
            await interaction.response.send_message(
                "現在ボットはメンテナンス中のため、このコマンドは使用できません。", 
                ephemeral=True
            )
            return False
        # --- ここまで変更/追加 ---
        return True
    return discord.app_commands.check(predicate)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="maintenance_status", description="現在のメンテナンスモードの状態を表示します。")
    # /maintenance_status コマンドは、このチェックを適用しない（製作者が常にアクセスできるように）
    # ※is_owner()は引き続き有効なため、製作者のみが使用可能
    async def maintenance_status(self, interaction: discord.Interaction):
        # コマンド実行ログ
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /maintenance_status コマンドを使用しました。")

        # 起動待機中であっても、製作者がこのコマンドを使えるようにするための分岐
        # ただし、deferは必須
        await interaction.response.defer(ephemeral=True, thinking=True) 

        # 起動準備中で製作者がこのコマンドを実行した場合のメッセージ
        if not is_bot_ready_for_commands and interaction.user.id == OWNER_ID:
             await interaction.followup.send(
                "現在ボットは起動準備中です。完了次第、通常のコマンドが利用可能になります。\n"
                "メンテナンスモードは現在のところ無効です。", 
                ephemeral=True
            )
             return # これで、残りの処理は実行せずに終了

        # 通常の権限チェックと処理
        if OWNER_ID is None:
            await interaction.followup.send("エラー: ボットの製作者IDが設定されていません。環境変数をご確認ください。", ephemeral=True)
            return
        if interaction.user.id != OWNER_ID: # このチェックはnot_in_maintenance()デコレーターがないので、直接行う
            await interaction.followup.send("あなたはボットの製作者ではありません。このコマンドは使用できません。", ephemeral=True)
            return
        
        status = "オン" if is_maintenance_mode else "オフ"
        await interaction.followup.send(f"現在のメンテナンスモードは **{status}** です。", ephemeral=True)

# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))