import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import logging
import sys
import asyncio

# admin_commands コグは一時的にインポートしない
# from admin_commands import is_maintenance_mode

load_dotenv()

# --- ロギング設定 ---
# 全体のロギングレベルをDEBUGに設定 (詳細なログを確認するため)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.stdout)

# discord.pyとwebsocketsのロガーもDEBUGレベルに設定
logging.getLogger('discord').setLevel(logging.DEBUG)
logging.getLogger('websockets').setLevel(logging.DEBUG)

# --- asyncioの未捕捉例外ハンドラ ---
def handle_exception(loop, context):
    """asyncioの未捕捉例外を処理するハンドラ"""
    msg = context.get("exception", context["message"])
    logging.error(f"非同期処理で未捕捉の例外が発生しました: {msg}")
    if "exception" in context:
        logging.error("トレースバック:", exc_info=context["exception"])

# --- Discordクライアントのインテント設定 ---
# 全てのインテントを有効化
intents = discord.Intents.all()

# --- ボットのインスタンス作成 ---
bot = commands.Bot(command_prefix='!', intents=intents)

# --- on_readyイベントハンドラ (究極のシンプル版) ---
@bot.event
async def on_ready():
    """ボットがDiscordに接続した際に実行される処理"""
    print("--- on_ready イベント開始 (究極のシンプル版) ---", file=sys.stdout)
    try:
        print(f'Logged in as {bot.user.name}', file=sys.stdout)
        print(f'Bot ID: {bot.user.id}', file=sys.stdout)
        print('------', file=sys.stdout)
        print("ボットは正常に起動し、Discordに接続しました！", file=sys.stdout)
        
        # ここから下の全ての処理はコメントアウトするか、削除する
        # global OWNER_ID はもう参照しない
        # is_maintenance_mode の参照も削除
        # ステータス変更処理も削除
        # admin_commands コグのロードも削除
        # スラッシュコマンドの同期も削除

        print("--- on_ready イベント終了 (究極のシンプル版) ---", file=sys.stdout)

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