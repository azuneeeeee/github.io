import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# Flask, admin_commands などはデバッグのため一時的に削除
# from flask import Flask
# import threading
# from admin_commands import not_in_maintenance, setup as setup_admin_commands_cog, OWNER_ID, is_maintenance_mode

load_dotenv()

# ボットがログインするのに最低限必要なインテント
intents = discord.Intents.default()
# intents.message_content = True # 基本的なログインには不要
# intents.members = True       # 基本的なログインには不要

# ボットのインスタンスを作成（最もシンプルな形）
bot = commands.Bot(command_prefix='!', intents=intents) # <-- ここをシンプルにしました

@bot.event
async def on_ready():
    """ボットがDiscordに接続した際に実行される処理"""
    print("--- on_ready イベント開始 (デバッグ用シンプル版) ---")
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    print('------')
    print("ボットは正常に起動し、Discordに接続しました！")
    print("--- on_ready イベント終了 (デバッグ用シンプル版) ---")

# ボットの起動処理
if __name__ == '__main__':
    # Flaskサーバーの起動処理も一時的に削除
    # if os.getenv('FLASK_ENABLED', 'False').lower() == 'true':
    #     def run_discord_bot():
    #         try:
    #             bot.run(os.getenv('DISCORD_BOT_TOKEN'))
    #         except Exception as e:
    #             print(f"Discord Botの実行中にエラーが発生しました: {e}")

    #     discord_thread = threading.Thread(target=run_discord_bot)
    #     discord_thread.start()

    #     port = int(os.environ.get('PORT', 10000))
    #     print(f"Flaskサーバーをポート {port} で起動します。")
    #     app.run(host='0.0.0.0', port=port)
    # else:
    print("Flaskサーバーは起動しません。Discord Botを単独で実行します。")
    try:
        bot.run(os.getenv('DISCORD_BOT_TOKEN'))
    except Exception as e:
        print(f"Discord Botの実行中に致命的なエラーが発生しました: {e}")