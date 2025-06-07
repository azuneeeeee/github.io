import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import logging
import sys
import asyncio

# admin_commands コグをインポート
# OWNER_ID と is_maintenance_mode は admin_commands.py から共有されます
from admin_commands import is_maintenance_mode # OWNER_IDはadmin_commands.pyで直接読み込むため、ここでは不要

load_dotenv()

# --- ロギング設定 ---
# 全体のロギングレベルをINFOに設定 (本番運用向け、デバッグはDEBUG)
# デバッグが必要な場合は level=logging.DEBUG に変更してください
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.stdout)

# discord.pyとwebsocketsのロガーもINFOレベルに設定 (本番運用向け)
logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('websockets').setLevel(logging.INFO)

# --- asyncioの未捕捉例外ハンドラ ---
def handle_exception(loop, context):
    """asyncioの未捕捉例外を処理するハンドラ"""
    msg = context.get("exception", context["message"])
    logging.error(f"非同期処理で未捕捉の例外が発生しました: {msg}")
    if "exception" in context:
        logging.error("トレースバック:", exc_info=context["exception"])

# --- Discordクライアントのインテント設定 ---
# 本番運用時は必要なインテントのみに絞ることを推奨します。
# 例: intents = discord.Intents.default()
# intents.message_content = True
# intents.members = True
intents = discord.Intents.all() # デバッグ・テストのため、当面は all() のままにしておく

# --- ボットのインスタンス作成 ---
bot = commands.Bot(command_prefix='!', intents=intents)

# --- on_readyイベントハンドラ ---
@bot.event
async def on_ready():
    """ボットがDiscordに接続した際に実行される処理"""
    print("--- on_ready イベント開始 ---", file=sys.stdout) # ログはstdoutへ統一
    try:
        print(f'Logged in as {bot.user.name}', file=sys.stdout)
        print(f'Bot ID: {bot.user.id}', file=sys.stdout)
        print('------', file=sys.stdout)
        print("ボットは正常に起動し、Discordに接続しました！", file=sys.stdout)

        # ステータス変更処理
        if is_maintenance_mode:
            await bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
        else:
            await bot.change_presence(activity=discord.Game(name="プロセカ！ | !help_proseka"))
        print("--- ステータス設定後 ---", file=sys.stdout)

        # admin_commands コグのロードとスラッシュコマンドの同期
        try:
            await bot.load_extension('admin_commands')
            print("admin_commands コグをロードしました。", file=sys.stdout)
            # スラッシュコマンドをDiscordに同期
            await bot.tree.sync()
            print("スラッシュコマンドをDiscordに同期しました。", file=sys.stdout)
        except Exception as e:
            # コグのロードやコマンド同期中のエラーはstderrへ
            print(f"!!! admin_commands コグのロード中またはコマンド同期中にエラーが発生しました: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

        print("--- on_ready イベント終了 ---", file=sys.stdout)

    except Exception as e:
        # on_ready イベント内で発生する予期せぬエラーを捕捉
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# --- ボットの起動処理 ---
if __name__ == '__main__':
    # asyncioのイベントループに未捕捉例外ハンドラを設定
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

    print("デバッグ: Flaskは無効。Discord Botを単独で実行します。", file=sys.stdout)
    try:
        print("デバッグ: bot.run() を呼び出し中...", file=sys.stdout)
        bot.run(os.getenv('DISCORD_BOT_TOKEN'))
    except Exception as e:
        # bot.run() 自体で発生する致命的なエラーを捕捉
        print(f"デバッグ: Discord Botの実行中に致命的なエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    print("デバッグ: bot.run() 呼び出し後（ここまで来たらボットプロセスが意図せず終了）", file=sys.stdout)