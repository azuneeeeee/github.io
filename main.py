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
    # 緊急脱出: ここでプロセスを終了させてみる（状況悪化の可能性もあるので注意）
    # sys.exit(1)

# --- Discordクライアントのインテント設定 ---
# 全てのインテントを有効化
intents = discord.Intents.all()

# --- ボットのインスタンス作成 ---
bot = commands.Bot(command_prefix='!', intents=intents)

# --- on_readyイベントハンドラ (究極のシンプル版) ---
@bot.event
async def on_ready():
    """ボットがDiscordに接続した際に実行される処理"""
    print("--- on_ready イベント開始 (アグレッシブデバッグ版) ---", file=sys.stdout)
    try:
        print(f'Logged in as {bot.user.name}', file=sys.stdout)
        print(f'Bot ID: {bot.user.id}', file=sys.stdout)
        print('------', file=sys.stdout)
        print("ボットは正常に起動し、Discordに接続しました！", file=sys.stdout)
        
        print("--- on_ready イベント終了 (アグレッシブデバッグ版) ---", file=sys.stdout)

    except Exception as e:
        # on_ready イベント内で発生する予期せぬエラーを捕捉
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# --- ボットの起動処理 ---
async def main():
    print("デバッグ: メイン非同期関数 'main()' 開始。", file=sys.stdout)
    try:
        # discord.pyのログイン処理を直接実行
        print("デバッグ: bot.login() を呼び出し中...", file=sys.stdout)
        await bot.login(os.getenv('DISCORD_BOT_TOKEN'))
        print("デバッグ: bot.login() 完了。ゲートウェイ接続待機中...", file=sys.stdout)

        # ゲートウェイ接続が完了するまで待つ (on_ready発火前)
        # 短い遅延を導入することで、リソーススパイクを回避できないか試す
        await asyncio.sleep(2) # <-- ここで2秒待機

        print("デバッグ: bot.connect() を呼び出し中...", file=sys.stdout)
        await bot.connect() # ゲートウェイに接続し、イベントループを開始

    except discord.LoginFailure:
        print("デバッグ: トークン認証に失敗しました。環境変数 DISCORD_BOT_TOKEN を確認してください。", file=sys.stderr)
        sys.exit(1) # 強制終了
    except Exception as e:
        print(f"デバッグ: メイン非同期関数内で致命的なエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1) # 強制終了

if __name__ == '__main__':
    # asyncioのイベントループに未捕捉例外ハンドラを設定
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

    print("デバッグ: Flaskは無効。Discord Botを単独で実行します。", file=sys.stdout)
    print("デバッグ: asyncio.run(main()) を呼び出し中...", file=sys.stdout)
    try:
        # bot.run() の代わりに、より低レベルな制御をするために main() を実行
        asyncio.run(main())
    except Exception as e:
        print(f"デバッグ: asyncio.run(main()) 呼び出し中に致命的なエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    print("デバッグ: asyncio.run(main()) 呼び出し後（ここまで来たらボットプロセスが意図せず終了）", file=sys.stdout)