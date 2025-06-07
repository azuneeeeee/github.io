import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
# random, unicodedata, re は不要になるため削除
# import random
# import unicodedata
# import re

# FlaskはRenderの無料Web Serviceで24時間稼働を試みる場合にのみ必要です。
from flask import Flask
import threading

# admin_commands コグをインポート
# OWNER_ID と is_maintenance_mode は admin_commands.py から共有される変数
from admin_commands import not_in_maintenance, setup as setup_admin_commands_cog, OWNER_ID, is_maintenance_mode

load_dotenv()

# songs モジュールは他のコマンド削除に伴い不要になるため削除
# from songs import proseka_songs, VALID_DIFFICULTIES

# Discordクライアントのインテント設定
# メッセージ内容とメンバーのインテントを有効にする
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# ボットのインスタンスを作成
# command_prefix='!' は従来のプレフィックスコマンド用
# application_command_prefix='!' はスラッシュコマンドを有効にするための設定
bot = commands.Bot(command_prefix='!', intents=intents, application_command_prefix='!')

# Flaskアプリのインスタンスを作成（Renderの24時間稼働維持用）
app = Flask(__name__)

@app.route('/')
def home():
    """Renderのヘルスチェック用エンドポイント"""
    return "プロセカBotは稼働中です！"

@bot.event
async def on_ready():
    """ボットがDiscordに接続した際に実行される処理"""
    print("--- on_ready イベント開始 ---") # <-- デバッグ用
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print('------')

    global OWNER_ID
    print("--- OWNER_ID 読み込み前 ---") # <-- デバッグ用
    if os.getenv('DISCORD_OWNER_ID'):
        try:
            OWNER_ID = int(os.getenv('DISCORD_OWNER_ID'))
            print(f"製作者IDが環境変数から {OWNER_ID} に設定されました。")
        except ValueError:
            print("警告: 環境変数 DISCORD_OWNER_ID が無効な数値です。製作者IDは設定されません。")
            OWNER_ID = None
    else:
        print("警告: 環境変数 DISCORD_OWNER_ID が設定されていません。製作者専用コマンドは機能しません。")
        OWNER_ID = None
    print("--- OWNER_ID 読み込み後 ---") # <-- デバッグ用

    # is_maintenance_mode も admin_commands.py から来ますが、まだこの時点では
    # admin_commands.py が完全にロードされていない可能性があるので、
    # 状態変更処理はコグロード後にエラーが出る場合は確認する
    if is_maintenance_mode:
        await bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
    else:
        await bot.change_presence(activity=discord.Game(name="プロセカ！ | !help_proseka"))
    print("--- ステータス変更後 ---") # <-- デバッグ用

    try:
        # コグのロードは main.py の try-except で囲む
        # admin_commands.py の setup 関数が await を含むので、main.py から呼び出す際も await が必要
        await bot.load_extension('admin_commands') # <-- ここは await で呼び出されます
        print("admin_commands コグをロードしました。")
        # グローバルスラッシュコマンドをDiscordに同期
        await bot.sync_commands()
        print("スラッシュコマンドをDiscordに同期しました。")
    except Exception as e:
        print(f"admin_commands コグのロード中またはコマンド同期中にエラーが発生しました: {e}")
    print("--- on_ready イベント終了 ---") # <-- デバッグ用


# ボットの起動処理
if __name__ == '__main__':
    # Flaskサーバーを起動し、Discordボットを別スレッドで実行
    if os.getenv('FLASK_ENABLED', 'False').lower() == 'true':
        def run_discord_bot():
            try:
                bot.run(os.getenv('DISCORD_BOT_TOKEN'))
            except Exception as e:
                print(f"Discord Botの実行中にエラーが発生しました: {e}")

        discord_thread = threading.Thread(target=run_discord_bot)
        discord_thread.start()

        port = int(os.environ.get('PORT', 10000))
        print(f"Flaskサーバーをポート {port} で起動します。")
        app.run(host='0.0.0.0', port=port)
    else:
        # Flaskを無効にしている場合はDiscordボットを直接起動
        print("Flaskサーバーは起動しません。Discord Botを単独で実行します。")
        bot.run(os.getenv('DISCORD_BOT_TOKEN'))