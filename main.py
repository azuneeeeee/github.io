import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback  # <-- エラー詳細出力用
import logging    # <-- ロギング設定用
import sys        # <-- 標準エラー出力用

# random, unicodedata, re などはデバッグのため一時的にコメントアウトを維持
# import random
# import unicodedata
# import re

# FlaskはRenderの無料Web Serviceで24時間稼働を試みる場合にのみ必要です。
# デバッグのため一時的にコメントアウト
# from flask import Flask
# import threading

# admin_commands コグはデバッグのため一時的にインポートしない
# from admin_commands import not_in_maintenance, setup as setup_admin_commands_cog, OWNER_ID, is_maintenance_mode

load_dotenv()

# songs モジュールもデバッグのため一時的にインポートしない
# from songs import proseka_songs, VALID_DIFFICULTIES

# --- ここからロギング設定を追加 ---
# 全体のロギングレベルをDEBUGに設定
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.stdout) # すべてのログを標準出力へ

# discord.pyのロガーもDEBUGレベルに設定
discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.DEBUG)

# websocketsのロガーもDEBUGレベルに設定 (Discordの内部で使われることが多い)
# これで接続の詳細が確認できる可能性
websockets_logger = logging.getLogger('websockets')
websockets_logger.setLevel(logging.DEBUG)
# --- ロギング設定ここまで ---


# Discordクライアントのインテント設定
# !!! デバッグのため、全てのインテントを一時的に有効にします !!!
# 問題解決後には、必要なインテントのみに戻すことを推奨します。
intents = discord.Intents.all() # <-- ここを all() に変更


# ボットのインスタンスを作成（最もシンプルな形）
# application_command_prefix も一時的に削除
bot = commands.Bot(command_prefix='!', intents=intents)

# Flaskアプリのインスタンスを作成（デバッグのため一時的にコメントアウト）
# app = Flask(__name__)

# @app.route('/') # デバッグのため一時的にコメントアウト
# def home():
#     """Renderのヘルスチェック用エンドポイント"""
#     return "プロセカBotは稼働中です！"

@bot.event
async def on_ready():
    """ボットがDiscordに接続した際に実行される処理"""
    print("--- on_ready イベント開始 (最終デバッグ版) ---", file=sys.stdout) # <-- デバッグ用、標準出力へ
    try:
        print(f'Logged in as {bot.user.name}', file=sys.stdout)
        print(f'Bot ID: {bot.user.id}', file=sys.stdout)
        print('------', file=sys.stdout)
        print("ボットは正常に起動し、Discordに接続しました！", file=sys.stdout)
        # ここに到達すれば、on_readyイベント内での問題ではない可能性が高い
        print("--- on_ready イベント終了 (最終デバッグ版) ---", file=sys.stdout) # <-- デバッグ用

        # 通常のコードに戻す際にここから下のコメントアウトを解除
        # global OWNER_ID
        # print("--- OWNER_ID 読み込み前 ---", file=sys.stdout)
        # if os.getenv('DISCORD_OWNER_ID'):
        #     try:
        #         OWNER_ID = int(os.getenv('DISCORD_OWNER_ID'))
        #         print(f"製作者IDが環境変数から {OWNER_ID} に設定されました。", file=sys.stdout)
        #     except ValueError:
        #         print("警告: 環境変数 DISCORD_OWNER_ID が無効な数値です。製作者IDは設定されません。", file=sys.stdout)
        #         OWNER_ID = None
        # else:
        #     print("警告: 環境変数 DISCORD_OWNER_ID が設定されていません。製作者専用コマンドは機能しません。", file=sys.stdout)
        #     OWNER_ID = None
        # print("--- OWNER_ID 読み込み後 ---", file=sys.stdout)

        # if is_maintenance_mode:
        #     await bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
        # else:
        #     await bot.change_presence(activity=discord.Game(name="プロセカ！ | !help_proseka"))
        # print("--- ステータス変更後 ---", file=sys.stdout)

        # try:
        #     await bot.load_extension('admin_commands')
        #     print("admin_commands コグをロードしました。", file=sys.stdout)
        #     await bot.sync_commands()
        #     print("スラッシュコマンドをDiscordに同期しました。", file=sys.stdout)
        # except Exception as e:
        #     print(f"admin_commands コグのロード中またはコマンド同期中にエラーが発生しました: {e}", file=sys.stderr)
        #     traceback.print_exc(file=sys.stderr)

    except Exception as e:
        # on_ready 内で発生するエラーを捕捉
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr) # 完全なTracebackを出力


# ボットの起動処理
if __name__ == '__main__':
    # Flaskサーバーの起動処理も一時的にコメントアウト
    # if os.getenv('FLASK_ENABLED', 'False').lower() == 'true':
    #     def run_discord_bot():
    #         try:
    #             bot.run(os.getenv('DISCORD_BOT_TOKEN'))
    #         except Exception as e:
    #             print(f"Discord Botの実行中にエラーが発生しました: {e}", file=sys.stderr)

    #     discord_thread = threading.Thread(target=run_discord_bot)
    #     discord_thread.start()

    #     port = int(os.environ.get('PORT', 10000))
    #     print(f"Flaskサーバーをポート {port} で起動します。", file=sys.stdout)
    #     app.run(host='0.0.0.0', port=port)
    # else:
    print("デバッグ: Flaskは無効。Discord Botを単独で実行します。", file=sys.stdout) # <-- デバッグ用
    try:
        print("デバッグ: bot.run() を呼び出し中...", file=sys.stdout) # <-- デバッグ用
        bot.run(os.getenv('DISCORD_BOT_TOKEN'))
    except Exception as e:
        # bot.run() 自体で発生するエラーを捕捉
        print(f"デバッグ: Discord Botの実行中に致命的なエラーが発生しました: {e}", file=sys.stderr) # <-- デバッグ用
        traceback.print_exc(file=sys.stderr) # <-- Tracebackを強制的に出力
    print("デバッグ: bot.run() 呼び出し後（ここまで来たらボットプロセスが意図せず終了）", file=sys.stdout) # <-- デバッグ用