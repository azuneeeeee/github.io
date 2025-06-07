import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
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

# Discordクライアントのインテント設定
# 基本的なログインに絞るため、最低限のインテントのみ
intents = discord.Intents.default()
# intents.message_content = True # デバッグのため一時的にコメントアウト
# intents.members = True       # デバッグのため一時的にコメントアウト

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
    print("--- on_ready イベント開始 (最終デバッグ版) ---") # <-- デバッグ用
    try:
        print(f'Logged in as {bot.user.name}')
        print(f'Bot ID: {bot.user.id}')
        print('------')
        print("ボットは正常に起動し、Discordに接続しました！")
        # ここに到達すれば、on_readyイベント内での問題ではない可能性が高い
        print("--- on_ready イベント終了 (最終デバッグ版) ---") # <-- デバッグ用

        # 通常のコードに戻す際にここから下のコメントアウトを解除
        # global OWNER_ID
        # print("--- OWNER_ID 読み込み前 ---")
        # if os.getenv('DISCORD_OWNER_ID'):
        #     try:
        #         OWNER_ID = int(os.getenv('DISCORD_OWNER_ID'))
        #         print(f"製作者IDが環境変数から {OWNER_ID} に設定されました。")
        #     except ValueError:
        #         print("警告: 環境変数 DISCORD_OWNER_ID が無効な数値です。製作者IDは設定されません。")
        #         OWNER_ID = None
        # else:
        #     print("警告: 環境変数 DISCORD_OWNER_ID が設定されていません。製作者専用コマンドは機能しません。")
        #     OWNER_ID = None
        # print("--- OWNER_ID 読み込み後 ---")

        # if is_maintenance_mode:
        #     await bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
        # else:
        #     await bot.change_presence(activity=discord.Game(name="プロセカ！ | !help_proseka"))
        # print("--- ステータス変更後 ---")

        # try:
        #     await bot.load_extension('admin_commands')
        #     print("admin_commands コグをロードしました。")
        #     await bot.sync_commands()
        #     print("スラッシュコマンドをDiscordに同期しました。")
        # except Exception as e:
        #     print(f"admin_commands コグのロード中またはコマンド同期中にエラーが発生しました: {e}")

    except Exception as e:
        # on_ready 内で発生するエラーを捕捉
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}")
        import traceback
        traceback.print_exc() # 完全なTracebackを出力