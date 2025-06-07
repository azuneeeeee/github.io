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

# discord.pyとwebsocketsのロガーもDEBUGレベルに設定
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

# --- READY イベントのフック ---
# discord.py の内部イベントを直接捕捉する (on_ready の元になるイベント)
@bot.event
async def on_socket_raw_receive(msg):
    """
    ソケットから生データを受信した際に呼び出されるイベント。
    DEBUGレベルでログ出力されないと非常に長文になる可能性があるため注意。
    """
    # msg はバイト列なのでデコードして表示
    # print(f"DEBUG: RAW Socket Receive: {msg.decode('utf-8')[:200]}...", file=sys.stdout) # 長文になるので通常は非推奨

# on_ready イベントの元となる READY イベントを処理する関数をフック
# このフックは非常に内部的なものであり、discord.py のアップデートで動作しなくなる可能性もある
_old_dispatch = bot.dispatch
def _new_dispatch(event, *args, **kwargs):
    if event == "ready":
        print("DEBUG: EVENT 'ready' がディスパッチされました！(on_ready の直前) ----", file=sys.stdout)
        # ここでさらに短い遅延を入れることも可能だが、まずはログ確認
        # await asyncio.sleep(0.1) 
    _old_dispatch(event, *args, **kwargs)

# bot.dispatch をカスタムディスパッチ関数に置き換える
# WARNING: これは非公開APIを操作しているため、推奨される方法ではありません。
# ただし、現状のデバッグ目的のために試みています。
bot.dispatch = _new_dispatch


# --- on_readyイベントハンドラ ---
@bot.event
async def on_ready():
    print("--- on_ready イベント開始 --- (フックテスト版)", file=sys.stdout)
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
            await bot.tree.sync() # スラッシュコマンドをDiscordに同期
            print("スラッシュコマンドをDiscordに同期しました。", file=sys.stdout)
        except Exception as e:
            print(f"!!! admin_commands コグのロード中またはコマンド同期中にエラーが発生しました: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

        print("--- on_ready イベント終了 --- (フックテスト版)", file=sys.stdout)

    except Exception as e:
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# --- ボットの起動処理 (低レベル制御を維持) ---
async def main():
    print("デバッグ: メイン非同期関数 'main()' 開始。", file=sys.stdout)
    try:
        print("デバッグ: bot.login() を呼び出し中...", file=sys.stdout)
        await bot.login(os.getenv('DISCORD_BOT_TOKEN'))
        print("デバッグ: bot.login() 完了。ゲートウェイ接続待機中...", file=sys.stdout)

        # 短い遅延を導入することで、リソーススパイクを回避できないか試す
        await asyncio.sleep(2) # <-- 前回効果があった遅延を維持

        print("デバッグ: bot.connect() を呼び出し中...", file=sys.stdout)
        await bot.connect() # ゲートウェイに接続し、イベントループを開始

    except discord.LoginFailure:
        print("致命的エラー: トークン認証に失敗しました。環境変数 DISCORD_BOT_TOKEN を確認してください。", file=sys.stderr)
        sys.exit(1) # 強制終了
    except Exception as e:
        print(f"致命的エラー: メイン非同期関数内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1) # 強制終了

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