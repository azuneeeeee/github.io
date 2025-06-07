import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import logging
import sys
import asyncio

# admin_commands コグをインポート
# is_maintenance_mode は admin_commands.py から共有されます
from admin_commands import is_maintenance_mode 

load_dotenv()

# --- ロギング設定 ---
# 全体のロギングレベルをDEBUGに設定 (詳細なログを確認するため)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.stdout)

logging.getLogger('discord').setLevel(logging.DEBUG)
logging.getLogger('websockets').setLevel(logging.DEBUG)

# --- asyncioの未捕捉例外ハンドラ ---
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"非同期処理で未捕捉の例外が発生しました: {msg}")
    if "exception" in context:
        logging.error("トレースバック:", exc_info=context["exception"])

# --- Discordクライアントのインテント設定 ---
intents = discord.Intents.all() 

# --- ボットのインスタンス作成 ---
bot = commands.Bot(command_prefix='!', intents=intents)

# --- on_readyイベントハンドラ ---
@bot.event
async def on_ready():
    # on_ready が発火したことを示す最も重要なログ
    print("--- on_ready イベント開始 --- (段階的起動アプローチ)", file=sys.stdout)
    try:
        print(f'Logged in as {bot.user.name}', file=sys.stdout)
        print(f'Bot ID: {bot.user.id}', file=sys.stdout)
        print('------', file=sys.stdout)
        print("ボットは正常に起動し、Discordに接続しました！", file=sys.stdout)

        # ステータス変更処理 (この前に少し遅延)
        await asyncio.sleep(0.5) # ステータス変更前の短い遅延
        if is_maintenance_mode:
            await bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
        else:
            await bot.change_presence(activity=discord.Game(name="プロセka！ | !help_proseka"))
        print("--- ステータス設定後 ---", file=sys.stdout)

        # コグのロードとスラッシュコマンドの同期 (この前に少し遅延)
        await asyncio.sleep(1) # コグロード前の遅延
        try:
            await bot.load_extension('admin_commands')
            print("admin_commands コグをロードしました。", file=sys.stdout)
            await asyncio.sleep(0.5) # コマンド同期前の短い遅延
            await bot.tree.sync() # スラッシュコマンドをDiscordに同期
            print("スラッシュコマンドをDiscordに同期しました。", file=sys.stdout)
        except Exception as e:
            print(f"!!! admin_commands コグのロード中またはコマンド同期中にエラーが発生しました: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

        await asyncio.sleep(0.5) # on_ready 終了前の短い遅延
        print("--- on_ready イベント終了 --- (段階的起動アプローチ)", file=sys.stdout)

    except Exception as e:
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# --- ボットの起動処理 (段階的起動) ---
async def main():
    print("デバッグ: メイン非同期関数 'main()' 開始。", file=sys.stdout)
    try:
        print("デバッグ: bot.login() を呼び出し中...", file=sys.stdout)
        await bot.login(os.getenv('DISCORD_BOT_TOKEN'))
        print("デバッグ: bot.login() 完了。ゲートウェイ接続待機中...", file=sys.stdout)

        # ログイン後、ゲートウェイ接続前の重要な遅延
        await asyncio.sleep(3) # <-- ここで3秒の遅延 (以前の2秒より長く)

        print("デバッグ: bot.connect() を呼び出し中...", file=sys.stdout)
        await bot.connect() # ゲートウェイに接続し、イベントループを開始

    except discord.LoginFailure:
        print("致命的エラー: トークン認証に失敗しました。環境変数 DISCORD_BOT_TOKEN を確認してください。", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"致命的エラー: メイン非同期関数内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

    print("デバッグ: Discord Botを起動します。", file=sys.stdout)
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"デバッグ: asyncio.run(main()) 呼び出し中に致命的なエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    print("デバッグ: asyncio.run(main()) 呼び出し後（ここまで来たらボットプロセスが意図せず終了）", file=sys.stdout)