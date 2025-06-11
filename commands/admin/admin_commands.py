import discord
from discord.ext import commands
import discord.app_commands
import os
from dotenv import load_dotenv
import logging
import sys
import json
import asyncio

# 不要になったインポートを削除
# import main # ★削除★

# === 新しいインポート ===
import utils.config_manager as config_manager_module
# ========================

logger = logging.getLogger(__name__)

load_dotenv()

# OWNER_ID の設定は、ボットの `is_owner` メソッドに任せるため、ここでの定義は不要。
# ただし、not_in_maintenance チェックで OWNER_ID を使う場合は保持。
# Discord.py v2.0 以降の Bot オブジェクトには .owner_id が自動的に設定される。
# 環境変数から取得するロジックは main.py の Bot 初期化時に適切に渡されているはずなので、ここでは必要ない。

# is_owner() プレディケートを Bot.is_owner() を使うように変更
def is_owner_check():
    async def predicate(interaction: discord.Interaction):
        # bot.is_owner() を直接利用
        is_owner = await interaction.client.is_owner(interaction.user)
        logger.info(f"デバッグ: is_ownerチェック: ユーザーID={interaction.user.id}, OWNER_ID={interaction.client.owner_id}")

        if not is_owner:
            await interaction.response.send_message("このコマンドはボットの管理者のみが使用できます。", ephemeral=True)
            logger.warning(f"警告: ユーザー: {interaction.user.name}({interaction.user.id}) が /status_toggle コマンドを使用しようとしましたが、権限がありませんでした。")
            return False
        return True
    return discord.app_commands.check(predicate)

def not_in_maintenance():
    async def predicate(interaction: discord.Interaction):
        # interaction.client は bot オブジェクトを指す
        # OWNER_ID の取得は interaction.client.owner_id を使う
        current_owner_id = interaction.client.owner_id # bot.owner_id から取得

        if not interaction.client.is_bot_ready_for_commands:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "現在ボットは起動準備中のため、このコマンドは使用できません。\n"
                    "しばらく時間をおいてから再度お試しください。",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "現在ボットは起動準備中のため、このコマンドは使用できません。\n"
                    "しばらく時間をおいてから再度お試しください。",
                    ephemeral=True
                )
            logger.info("デバッグ: not_in_maintenanceチェック: bot.is_bot_ready_for_commands が False のため失敗。")
            return False

        # OWNER_ID が設定されていない場合は警告し、メンテナンスモードチェックをスキップする
        if current_owner_id is None:
            logger.warning("警告: not_in_maintenanceチェック: ボットの製作者IDが設定されていません。環境変数をご確認ください。")
            # この場合でも、オーナー以外のユーザーはコマンドを使用できないようにする（念のため）
            if interaction.user.id != current_owner_id: # この条件は常に False になるが、コードの意図を明示
                 if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "エラー: ボットの製作者IDが設定されていないため、一部機能が制限されています。",
                        ephemeral=True
                    )
                 else:
                    await interaction.followup.send(
                        "エラー: ボットの製作者IDが設定されていないため、一部機能が制限されています。",
                        ephemeral=True
                    )
                 return False

        if interaction.client.is_maintenance_mode and interaction.user.id != current_owner_id:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "現在ボットはメンテナンス中のため、このコマンドは使用できません。",
                    ephemeral=True
                )
            else:
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
        logger.info("デバッグ: AdminCommandsコグが初期化されています。")
        # 起動時にメンテナンスモードの状態をファイルからロードする
        try:
            initial_maintenance_status = config_manager_module.load_maintenance_status()
            self.bot.is_maintenance_mode = initial_maintenance_status
            logger.info(f"デバッグ: 初期メンテナンスモード状態をロードしました: {self.bot.is_maintenance_mode}")
        except Exception as e:
            logger.error(f"エラー: メンテナンスモードの初期ロード中にエラーが発生しました: {e}", exc_info=True)


    @discord.app_commands.command(name="status_toggle", description="ボットのDiscordステータス（オンライン/取り込み中）を切り替えます。")
    @is_owner_check() # 修正したis_owner_checkを使用
    async def status_toggle(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) 
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /status_toggle コマンドを使用しました。")

        # ボットが完全に準備できるまで待機
        if not self.bot.is_ready():
            logger.info("デバッグ: /status_toggle: ボットがまだ準備できていません。準備できるまで待機します。")
            await self.bot.wait_until_ready()
            logger.info("デバッグ: /status_toggle: ボットが準備できました。")

        # 準備完了後、さらに短い時間待機して内部状態の安定を待つ
        await asyncio.sleep(1)
        logger.info("デバッグ: /status_toggle: wait_until_ready() 後に短い遅延を追加しました。")


        # main.py の bot.is_maintenance_mode を直接更新する
        if self.bot.is_maintenance_mode: # 現在メンテナンスモードが有効なら無効に
            self.bot.is_maintenance_mode = False
            config_manager_module.save_maintenance_status(False)
            status_message = "オンライン"
            logger.info(f"デバッグ: /status_toggle によりメンテナンスモードが無効になりました。")
        else: # 現在メンテナンスモードが無効なら有効に
            self.bot.is_maintenance_mode = True
            config_manager_module.save_maintenance_status(True)
            status_message = "取り込み中"
            logger.info(f"デバッグ: /status_toggle によりメンテナンスモードが有効になりました。")

        # ここではステータス変更を直接行わず、maintenance_status_loopに任せる
        current_bot_status = interaction.guild.me.status if interaction.guild and interaction.guild.me else discord.Status.unknown
        current_activity_name = interaction.guild.me.activity.name if interaction.guild and interaction.guild.me and interaction.guild.me.activity else ""

        await interaction.followup.send(
            f"ボットのステータスを **{status_message}** に変更するよう要求しました。\n"
            f"メンテナンスモードは**{'有効' if self.bot.is_maintenance_mode else '無効'}**になりました。\n"
            f"(現在のボットの状態: {current_bot_status.name}, 活動: {current_activity_name})", # デバッグ情報として現在の状態を追加
            ephemeral=True
        )
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /status_toggle コマンドを使用しました。メンテモード: {'有効' if self.bot.is_maintenance_mode else '無効'}")


    # コグのロードとアンロードイベント
    async def cog_load(self):
        logger.info("AdminCommandsコグがロードされました。")

    async def cog_unload(self):
        logger.info("AdminCommandsコグがアンロードされました。")

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))