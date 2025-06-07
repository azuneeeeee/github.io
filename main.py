# main.py の修正箇所

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import random
import unicodedata
import re

# FlaskはRenderの無料Web Serviceで24時間稼働を試みる場合にのみ必要です。
from flask import Flask
import threading

from admin_commands import not_in_maintenance, setup as setup_admin_commands_cog, OWNER_ID, is_maintenance_mode

load_dotenv()

from songs import proseka_songs, VALID_DIFFICULTIES

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# ここを修正！ commands.Bot の初期化
# application_command_prefix を設定することで、スラッシュコマンドの機能を明示的に有効にします。
bot = commands.Bot(command_prefix='!', intents=intents, application_command_prefix='!') # <-- ここに注目！

# Flaskアプリのインスタンスを作成
app = Flask(__name__)

@app.route('/')
def home():
    return "プロセカBotは稼働中です！"

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print('------')

    global OWNER_ID
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

    if is_maintenance_mode:
        await bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
    else:
        await bot.change_presence(activity=discord.Game(name="プロセカ！ | !help_proseka"))

    try:
        await bot.load_extension('admin_commands')
        print("admin_commands コグをロードしました。")
        # グローバルコマンドをDiscordに同期します
        # これが非常に重要で、スラッシュコマンドをDiscordに登録します
        await bot.sync_commands() # <-- ここを追加！
        print("スラッシュコマンドをDiscordに同期しました。")
    except Exception as e:
        print(f"admin_commands コグのロード中またはコマンド同期中にエラーが発生しました: {e}")

# ... (中略、help_proseka, song, random_song, difficulty_list コマンドはそのまま) ...

if __name__ == '__main__':
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
        print("Flaskサーバーは起動しません。Discord Botを単独で実行します。")
        bot.run(os.getenv('DISCORD_BOT_TOKEN'))