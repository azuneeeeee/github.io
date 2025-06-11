import discord
from discord.ext import commands
import discord.app_commands
import os
from dotenv import load_dotenv
import logging
import sys
import json
import asyncio # asyncioをインポート

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

        # bot.is_ready() が False の場合、準備できるまで待機
        if not self.bot.is_ready():
            logger.info("デバッグ: /status_toggle: ボットがまだ準備できていません。準備できるまで待機します。")
            await self.bot.wait_until_ready()
            logger.info("デバッグ: /status_toggle: ボットが準備できました。")
        
        # 準備完了後、さらに短い時間待機して内部状態の安定を待つ
        await asyncio.sleep(1) # 遅延時間を0.5秒から1秒に延長
        logger.info("デバッグ: /status_toggle: wait_until_ready() 後に短い遅延を追加しました。")


        current_status = interaction.guild.me.status

        if current_status == discord.Status.online: # 起動モード（オンライン）から切り替える場合
            new_status = discord.Status.dnd # 取り込み中に変更
            status_message = "取り込み中"

            self.bot.is_maintenance_mode = True
            save_maintenance_status(True)
            logger.info(f"デバッグ: /status_toggle によりメンテナンスモードが有効になりました。")

            # maintenance_status_loop がまだ実行中でない場合に開始
            if not main.maintenance_status_loop.is_running():
                try:
                    main.maintenance_status_loop.start()
                    logger.info("デバッグ: maintenance_status_loop を開始しました。")
                except RuntimeError as e:
                    logger.error(f"エラー: maintenance_status_loop の開始に失敗しました: {e}")
                    await interaction.followup.send("エラー: メンテナンスステータスループの開始に失敗しました。", ephemeral=True)
                    return
            else:
                logger.info("デバッグ: maintenance_status_loop はすでに実行中です。")

            # ステータス変更とメッセージ送信
            await self.bot.change_presence(status=new_status)
            await interaction.followup.send(f"ボットのステータスを **{status_message}** に変更しました。\nメンテナンスモードは**{'有効' if self.bot.is_maintenance_mode else '無効'}**になりました。", ephemeral=True)
            logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /status_toggle コマンドを使用しました。ステータス: {status_message}, メンテモード: {'有効' if self.bot.is_maintenance_mode else '無効'}")

        else: # current_status == discord.Status.dnd （取り込み中）から切り替える場合
            new_status = discord.Status.online # オンラインに変更
            status_message = "オンライン"

            self.bot.is_maintenance_mode = False
            save_maintenance_status(False)
            logger.info(f"デバッグ: /status_toggle によりメンテナンスモードが無効になりました。")

            # maintenance_status_loop が実行中なら停止させる
            if main.maintenance_status_loop.is_running():
                main.maintenance_status_loop.cancel()
                logger.info("デバッグ: maintenance_status_loop を停止しました。")

            # ループ停止後、元のカスタムステータスに戻す
            await self.bot.change_presence(activity=discord.CustomActivity(name=self.bot.original_status_message), status=new_status)
            await interaction.followup.send(f"ボットのステータスを **{status_message}** に変更しました。\nメンテナンスモードは**{'有効' if self.bot.is_maintenance_mode else '無効'}**になりました。", ephemeral=True)
            logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /status_toggle コマンドを使用しました。ステータス: {status_message}, メンテモード: {'有効' if self.bot.is_maintenance_mode else '無効'}")

# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))