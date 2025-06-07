import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import logging
import sys
import asyncio
import resource # <-- 追加: リソース監視用
import gc       # <-- 追加: ガベージコレクション監視用
import time     # <-- 追加: 時間計測用

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

# --- メモリとGCの状態をログに出力するヘルパー関数 ---
def log_resource_usage(stage: str):
    try:
        # メモリ使用量 (RSS: Resident Set Size, KB単位)
        # Linux環境で動作することを前提
        mem_info_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        # ガベージコレクションの状態
        gc_counts = gc.get_count() # (generation0, generation1, generation2)
        
        logging.debug(f"[{stage}] リソース使用状況: メモリ (RSS)={mem_info_rss} KB, GC Counts={gc_counts}")
    except Exception as e:
        logging.warning(f"リソース使用状況のログ取得中にエラー: {e}")

# --- on_readyイベントハンドラ (究極のシンプル版) ---
@bot.event
async def on_ready():
    """ボットがDiscordに接続した際に実行される処理"""
    log_resource_usage("on_ready_start") # <-- on_ready開始時のリソースログ
    print("--- on_ready イベント開始 (リソース監視デバッグ版) ---", file=sys.stdout)
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

        log_resource_usage("on_ready_end") # <-- on_ready終了時のリソースログ
        print("--- on_ready イベント終了 (リソース監視デバッグ版) ---", file=sys.stdout)

    except Exception as e:
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# --- ボットの起動処理 ---
async def main():
    print("デバッグ: メイン非同期関数 'main()' 開始。", file=sys.stdout)
    log_resource_usage("main_start") # <-- main関数開始時のリソースログ
    try:
        # discord.pyのログイン処理を直接実行
        print("デバッグ: bot.login() を呼び出し中...", file=sys.stdout)
        await bot.login(os.getenv('DISCORD_BOT_TOKEN'))
        print("デバッグ: bot.login() 完了。ゲートウェイ接続待機中...", file=sys.stdout)
        log_resource_usage("after_bot_login") # <-- bot.login()後のリソースログ

        # ゲートウェイ接続が完了するまで待つ (on_ready発火前)
        # 短い遅延を導入することで、リソーススパイクを回避できないか試す
        await asyncio.sleep(2) # <-- ここで2秒待機

        print("デバッグ: bot.connect() を呼び出し中...", file=sys.stdout)
        await bot.connect() # ゲートウェイに接続し、イベントループを開始
        log_resource_usage("after_bot_connect") # <-- bot.connect()後のリソースログ


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
    log_resource_usage("script_start") # <-- スクリプト開始時のリソースログ
    try:
        # bot.run() の代わりに、より低レベルな制御をするために main() を実行
        asyncio.run(main())
    except Exception as e:
        print(f"デバッグ: asyncio.run(main()) 呼び出し中に致命的なエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    log_resource_usage("script_end") # <-- スクリプト終了時のリソースログ (到達すれば)
    print("デバッグ: asyncio.run(main()) 呼び出し後（ここまで来たらボットプロセスが意図せず終了）", file=sys.stdout)