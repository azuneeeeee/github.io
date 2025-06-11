import discord
from discord.ext import commands
import discord.app_commands
import os
from dotenv import load_dotenv
import logging
import sys
import json
import asyncio

# mainモジュール全体をインポート。ここで循環参照に注意が必要だが、
# 今回はmain.maintenance_status_loopを直接触らないため問題ないはず
import main 

logger = logging.getLogger(__name__)

MAINTENANCE_FILE = "maintenance_status.json"

def load_maintenance_status():
    if os.path.exists(MAINTENANCE_FILE):
        try:
            with open(MAINTENANCE_FILE, 'r') as f:
                data = json.load(f)
                if 'is_maintenance_mode' in data and isinstance(data['is_maintenance_mode'], bool):
                    logger.info(f"デバッグ: メンテナンスモードの状態を {MAINTENANCE_FILE} からロードしました: {data['is_maintenance_mode']}")
                    return data['is_maintenance_mode']
                else:
                    logger.warning(f"警告: {MAINTENANCE_FILE} の形式が不正です。デフォルトの False を使用します。")
                    return False
        except json.JSONDecodeError:
            logger.error(f"エラー: {MAINTENANCE_FILE} の読み込みに失敗しました。デフォルトの False を使用します。")
            return False
    logger.info(f"デバッグ: {MAINTENANCE_FILE} が存在しないため、デフォルトの False を使用します。")
    return False

def save_maintenance_status(status: bool):
    try:
        with open(MAINTENANCE_FILE, 'w') as f:
            json.dump({'is_maintenance_mode': status}, f)
        logger.info(f"デバッグ: メンテナンスモードの状態を {MAINTENANCE_FILE} に保存しました: {status}")
    except Exception as e:
        logger.error(f"エラー: メンテナンスモードの状態を {MAINTENANCE_FILE} に保存できませんでした: {e}")

_is_maintenance_mode = load_maintenance_status()

load_dotenv()

OWNER_ID = int(os.getenv('DISCORD_OWNER_ID')) if os.getenv('DISCORD_OWNER_ID') else None

def is_owner():
    async def predicate(interaction: discord.Interaction):
        logger.info(f"デバッグ: is_ownerチェック: ユーザーID={interaction.user.id}, OWNER_ID={OWNER_ID}")

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
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=False, thinking=True)
            logger.info(f"デバッグ: not_in_maintenanceチェック: defer実行 (ユーザーID={interaction.user.id}, interaction ID={interaction.id})")

        if not interaction.client.is_bot_ready_for_commands:
            await interaction.followup.send(
                "現在ボットは起動準備中のため、このコマンドは使用できません。\n"
                "しばらく時間をおいてから再度お試しください。",
                ephemeral=True
            )
            logger.info("デバッグ: not_in_maintenanceチェック: bot.is_bot_ready_for_commands が False のため失敗。")
            return False

        if interaction.client.is_maintenance_mode and interaction.user.id != OWNER_ID:
            await interaction.followup.send(
                "現在ボットはメンテナンス中のため、このコマンドは使用できません。",
                ephemeral=True
            )
            logger.info("デバッグ: not_in_maintenanceチェック: bot.is_maintenance_mode が True かつオーナーではないため失敗。")
            return False

        logger.info("デバッグ: not_in_maintenanceチェック: 全ての条件をパス。")
        return True
    return discord.app_commands.check(predicate)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="status_toggle", description="ボットのDiscordステータス（オンライン/取り込み中）を切り替えます。")
    @is_owner()
    async def status_toggle(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /status_toggle コマンドを使用しました。")

        # ボットが完全に準備できるまで待機
        if not self.bot.is_ready():
            logger.info("デバッグ: /status_toggle: ボットがまだ準備できていません。準備できるまで待機します。")
            await self.bot.wait_until_ready()
            logger.info("デバッグ: /status_toggle: ボットが準備できました。")
        
        # 準備完了後、さらに短い時間待機して内部状態の安定を待つ
        await asyncio.sleep(1) # 遅延時間を延長（前回の修正から変更なし）
        logger.info("デバッグ: /status_toggle: wait_until_ready() 後に短い遅延を追加しました。")


        # main.py の bot.is_maintenance_mode を直接更新する
        if self.bot.is_maintenance_mode: # 現在メンテナンスモードが有効なら無効に
            self.bot.is_maintenance_mode = False
            save_maintenance_status(False)
            status_message = "オンライン"
            logger.info(f"デバッグ: /status_toggle によりメンテナンスモードが無効になりました。")
        else: # 現在メンテナンスモードが無効なら有効に
            self.bot.is_maintenance_mode = True
            save_maintenance_status(True)
            status_message = "取り込み中"
            logger.info(f"デバッグ: /status_toggle によりメンテナンスモードが有効になりました。")

        # ここではステータス変更を直接行わず、maintenance_status_loopに任せる
        # ただし、即座にメッセージを返すために、念のため現在のステータス情報を取得
        # (これは表示のためだけであり、実際のステータス変更はループが行う)
        current_bot_status = interaction.guild.me.status if interaction.guild and interaction.guild.me else discord.Status.unknown
        current_activity_name = interaction.guild.me.activity.name if interaction.guild and interaction.guild.me and interaction.guild.me.activity else ""

        await interaction.followup.send(
            f"ボットのステータスを **{status_message}** に変更するよう要求しました。\n"
            f"メンテナンスモードは**{'有効' if self.bot.is_maintenance_mode else '無効'}**になりました。\n"
            f"(現在のボットの状態: {current_bot_status.name}, 活動: {current_activity_name})", # デバッグ情報として現在の状態を追加
            ephemeral=True
        )
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /status_toggle コマンドを使用しました。メンテモード: {'有効' if self.bot.is_maintenance_mode else '無効'}")


# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))