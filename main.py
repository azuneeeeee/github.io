import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
import asyncio

# === Configuration & Setup ===
# ロギング設定をシンプルにする
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.__stdout__)
logging.getLogger('discord').setLevel(logging.INFO) # Discord loggingをINFOに設定

# 環境変数のロード
load_dotenv()
print("DEBUG: Environment variables loaded.", file=sys.__stdout__)

# インテントの設定 (必須)
intents = discord.Intents.all()
print("DEBUG: Intents configured (discord.Intents.all()).", file=sys.__stdout__)

# ボットインスタンスの作成
bot = commands.Bot(command_prefix='!', intents=intents)
print("DEBUG: Bot instance created.", file=sys.__stdout__)

# === on_ready Event Handler ===
@bot.event
async def on_ready():
    print("DEBUG: on_ready event started!", file=sys.__stdout__) # on_readyの先頭ログ
    try:
        if bot.user:
            print(f'DEBUG: on_ready: Logged in as {bot.user.name} (ID: {bot.user.id})', file=sys.__stdout__)
        else:
            print("DEBUG: on_ready: Bot user is None after ready event.", file=sys.__stdout__)
        print("DEBUG: on_ready: Bot successfully connected to Discord and is READY!", file=sys.__stdout__)

        # 最小限のステータス変更（必須ではないが、動作確認のため）
        await asyncio.sleep(1) # 念のため非同期処理を挟む
        await bot.change_presence(activity=discord.Game(name="Online!"), status=discord.Status.online)
        print("DEBUG: on_ready: Status set to 'Online!'.", file=sys.__stdout__)

        print("DEBUG: on_ready event finished. Bot fully operational.", file=sys.__stdout__)

    except Exception as e:
        print(f"FATAL ERROR: Unexpected error occurred within on_ready event: {e}", file=sys.__stderr__)
        traceback.print_exc(file=sys.__stderr__)
print("DEBUG: on_ready event handler defined.", file=sys.__stdout__)

# === Bot Startup ===
# bot.start() は、ログイン、接続、そしてイベントループを管理する高レベルな関数
async def start_bot():
    print("DEBUG: Starting bot via bot.start()...", file=sys.__stdout__)
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("FATAL ERROR: 'DISCORD_BOT_TOKEN' environment variable is not set. Exiting.", file=sys.__stderr__)
        sys.exit(1)
    
    try:
        await bot.start(token)
        # この行は、ボットが正常に停止しない限り到達しない
        print("DEBUG: bot.start() returned. This indicates the bot has disconnected/stopped.", file=sys.__stdout__)
    except discord.LoginFailure:
        print("FATAL ERROR: Token authentication failed. Please check DISCORD_BOT_TOKEN.", file=sys.__stderr__)
        sys.exit(1)
    except Exception as e:
        print(f"FATAL ERROR: An unexpected error occurred during bot startup: {e}", file=sys.__stderr__)
        traceback.print_exc(file=sys.__stderr__)
        sys.exit(1)

# === Program Entry Point ===
if __name__ == '__main__':
    print("DEBUG: Entering program entry point.", file=sys.__stdout__)
    try:
        asyncio.run(start_bot())
        print("DEBUG: asyncio.run(start_bot()) completed.", file=sys.__stdout__)
    except Exception as e:
        print(f"FATAL ERROR: A critical error occurred during asyncio.run(): {e}", file=sys.__stdout__)
        traceback.print_exc(file=sys.__stdout__)
    print("DEBUG: Program execution finished.", file=sys.__stdout__)