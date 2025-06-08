import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import traceback
import logging
import asyncio

# --- ロギング設定 ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.__stdout__)

logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('websockets').setLevel(logging.WARNING)
logging.getLogger('discord.app_commands.tree').setLevel(logging.WARNING)

# .env ファイルから環境変数をロード
load_dotenv()

# --- asyncioの未捕捉例外ハンドラ ---
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"Async unhandled exception occurred: {msg}", file=sys.__stderr__)
    if "exception" in context:
        logging.error("Traceback:", exc_info=context["exception"], file=sys.__stderr__)

# --- Discordクライアントのインテント設定 ---
intents = discord.Intents.all()

# --- ボットのインスタンス作成 ---
bot = commands.Bot(command_prefix='!', intents=intents)


# --- on_readyイベントハンドラ ---
@bot.event
async def on_ready():
    print("DEBUG: === on_ready event fired! ===", file=sys.__stdout__) # Event handler started
    try:
        print(f'DEBUG: on_ready: Logged in as {bot.user.name} ({bot.user.id})', file=sys.__stdout__)

        await asyncio.sleep(1)
        await bot.change_presence(activity=discord.Game(name="Online!"), status=discord.Status.online)
        print("DEBUG: on_ready: Status changed to 'Online!'.", file=sys.__stdout__)

        print("DEBUG: === on_ready event finished. Bot fully operational. ===", file=sys.__stdout__) # Event handler finished

    except Exception as e:
        print(f"FATAL ERROR: Unexpected error in on_ready event: {e}", file=sys.__stderr__)
        traceback.print_exc(file=sys.__stderr__)


# --- ボットの起動処理 ---
async def main():
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("FATAL ERROR: 'DISCORD_BOT_TOKEN' environment variable is not set.", file=sys.__stderr__)
        sys.exit(1)

    await bot.login(token)
    await bot.connect()

# --- プログラムのエントリポイント ---
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"FATAL ERROR: An error occurred during asyncio.run(main()): {e}", file=sys.__stdout__)
        traceback.print_exc(file=sys.__stdout__)