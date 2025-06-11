import discord
from discord.ext import commands
import discord.app_commands
import os
from dotenv import load_dotenv
import logging
import sys
import json
import asyncio # <-- 追加

# main モジュールをインポートして、bot オブジェクトと maintenance_status_loop にアクセスできるようにする
import main 

# ロガーの取得
logger = logging.getLogger(__name__)

# === グローバル変数（ファイルからのロードに切り替え） ===
MAINTENANCE_FILE = "maintenance_status.json"

# メンテナンスモードの状態をファイルからロードする関数
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

# メンテナンスモードの状態をファイルに保存する関数
def save_maintenance_status(status: bool):
    try:
        with open(MAINTENANCE_FILE, 'w') as f:
            json.dump({'is_maintenance_mode': status}, f)
        logger.info(f"デバッグ: メンテナンスモードの状態を {MAINTENANCE_FILE} に保存しました: {status}")
    except Exception as e:
        logger.error(f"エラー: メンテナンスモードの状態を {MAINTENANCE_FILE} に保存できませんでした: {e}")

# 初期ロードされたメンテナンスモードの状態を保持する（on_readyでbotオブジェクトに引き継がれる）
_is_maintenance_mode = load_maintenance_status() # これはファイルロード時の初期値。直接参照はしない。

load_dotenv()

OWNER_ID = int(os.getenv('DISCORD_OWNER_ID')) if os.getenv('DISCORD_OWNER_ID') else None


# === チェック関数 ===
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

        # bot オブジェクトの属性を参照する
        if not interaction.client.is_bot_ready_for_commands:
            await interaction.followup.send(
                "現在ボットは起動準備中のため、このコマンドは使用できません。\n"
                "しばらく時間をおいてから再度お試しください。",
                ephemeral=True
            )
            logger.info("デバッグ: not_in_maintenanceチェック: bot.is_bot_ready_for_commands が False のため失敗。")
            return False

        # bot オブジェクトの属性を参照する
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

        current_status = interaction.guild.me.status
        
        # 新しいステータスに基づいてメンテナンスモードを切り替える
        if current_status == discord.Status.online: # 起動モード（オンライン）から切り替える場合
            new_status = discord.Status.dnd # 取り込み中に変更
            status_message = "取り込み中"
            
            # ステータスが「取り込み中」になるので、メンテナンスモードを有効にする
            self.bot.is_maintenance_mode = True
            save_maintenance_status(True) # ファイルにも保存
            logger.info(f"デバッグ: /status_toggle によりメンテナンスモードが有効になりました。")
            
            # ステータス変更が反映されるのを少し待つ
            await asyncio.sleep(0.5) # <-- 追加
            
            # メンテナンスステータスループを開始
            # before_loop でのチェックがあるため、bot.is_maintenance_mode が確実にTrueになってからstart()を呼び出す
            if not main.maintenance_status_loop.is_running():
                try:
                    main.maintenance_status_loop.start() 
                    logger.info("デバッグ: maintenance_status_loop を開始しました。")
                except RuntimeError as e:
                    logger.error(f"エラー: maintenance_status_loop の開始に失敗しました: {e}")
                    # ここでループが開始できなかった場合の追加処理（例えば、元のステータスに戻すなど）
                    # 今回は特に何もしないが、ログで把握できるようにする

        else: # current_status == discord.Status.dnd （取り込み中）から切り替える場合
            new_status = discord.Status.online # オンラインに変更
            status_message = "オンライン"

            # ステータスが「オンライン」になるので、メンテナンスモードを無効にする
            self.bot.is_maintenance_mode = False
            save_maintenance_status(False) # ファイルにも保存
            logger.info(f"デバッグ: /status_toggle によりメンテナンスモードが無効になりました。")

            # メンテナンスステータスループを停止
            if main.maintenance_status_loop.is_running():
                main.maintenance_status_loop.cancel()
                logger.info("デバッグ: maintenance_status_loop を停止しました。")
            
            # ループ停止後、元のカスタムステータスに戻す
            await self.bot.change_presence(activity=discord.CustomActivity(name=self.bot.original_status_message), status=new_status)
            await interaction.followup.send(f"ボットのステータスを **{status_message}** に変更しました。\nメンテナンスモードは**{'有効' if self.bot.is_maintenance_mode else '無効'}**になりました。", ephemeral=True)
            logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /status_toggle コマンドを使用しました。ステータス: {status_message}, メンテモード: {'有効' if self.bot.is_maintenance_mode else '無効'}")
            return # ステータス変更とメッセージ送信がここで行われるため、重複を防ぐ

        # ステータス変更とメッセージ送信（オンラインへの切り替え時以外）
        # ここでは、メンテナンスモード中に切り替わる場合にのみ実行される
        # maintenance_status_loop.before_loop が最初にDNDステータスを設定するため、
        # ここでは activity の変更は不要だが、念のため status の変更は残す
        await self.bot.change_presence(status=new_status) # activity はループに任せる
        await interaction.followup.send(f"ボットのステータスを **{status_message}** に変更しました。\nメンテナンスモードは**{'有効' if self.bot.is_maintenance_mode else '無効'}**になりました。", ephemeral=True)
        logger.warning(f"ユーザー: {interaction.user.name}({interaction.user.id}) が /status_toggle コマンドを使用しました。ステータス: {status_message}, メンテモード: {'有効' if self.bot.is_maintenance_mode else '無効'}")
        

# コグをボットにセットアップするための関数
async def setup(bot):
    await bot.add_cog(AdminCommands(bot))