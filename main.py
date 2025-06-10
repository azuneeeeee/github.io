import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import traceback
import logging
import asyncio

print("DEBUG: main.py execution started - Initializing Discord bot.", file=sys.__stdout__)

# Load environment variables from .env file
load_dotenv()
print("DEBUG: Environment variables loaded.", file=sys.__stdout__)

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.__stdout__)

logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('websockets').setLevel(logging.WARNING)
logging.getLogger('discord.app_commands.tree').setLevel(logging.WARNING)
print("DEBUG: Logging configured.", file=sys.__stdout__)

# --- Asyncio Unhandled Exception Handler ---
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"Async unhandled exception occurred: {msg}", file=sys.__stderr__)
    if "exception" in context:
        logging.error("Traceback:", exc_info=context["exception"], file=sys.__stderr__)
print("DEBUG: Asyncio exception handler set.", file=sys.__stdout__)

# --- Discord Client Intents Configuration ---
intents = discord.Intents.all()
print("DEBUG: Intents configured (discord.Intents.all()).", file=sys.__stdout__)

# --- Bot Instance Creation ---
try:
    bot = commands.Bot(command_prefix='!', intents=intents)
    print("DEBUG: Bot instance created.", file=sys.__stdout__)
except Exception as e:
    print(f"FATAL ERROR: Failed to create bot instance: {e}", file=sys.__stderr__)
    sys.exit(1)

# --- on_ready Event Handler ---
@bot.event
async def on_ready():
    print("DEBUG: on_ready event started!", file=sys.__stdout__)
    try:
        print(f'DEBUG: on_ready: Logged in as {bot.user.name} (ID: {bot.user.id})', file=sys.__stdout__)
        print('------', file=sys.__stdout__)
        print("DEBUG: on_ready: Bot successfully connected to Discord and is READY!", file=sys.__stdout__)

        # Minimal status change
        print("DEBUG: on_ready: Setting bot status...", file=sys.__stdout__)
        await asyncio.sleep(1)
        await bot.change_presence(activity=discord.Game(name="Online!"), status=discord.Status.online)
        print("DEBUG: on_ready: Status set to 'Online!'.", file=sys.__stdout__)

        print("DEBUG: on_ready event finished. Bot fully operational.", file=sys.__stdout__)

    except Exception as e:
        print(f"FATAL ERROR: Unexpected error occurred within on_ready event: {e}", file=sys.__stderr__)
        traceback.print_exc(file=sys.__stderr__)
print("DEBUG: on_ready event handler defined.", file=sys.__stdout__)

# --- Bot Startup Process ---
async def main():
    print("DEBUG: Main async function 'main()' started.", file=sys.__stdout__)
    try:
        print("DEBUG: Calling bot.login()...", file=sys.__stdout__)
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            print("FATAL ERROR: 'DISCORD_BOT_TOKEN' environment variable is not set.", file=sys.__stderr__)
            sys.exit(1)
        await bot.login(token)
        print("DEBUG: bot.login() completed. Waiting for gateway connection...", file=sys.__stdout__)

        print("DEBUG: Calling bot.connect()...", file=sys.__stdout__)
        # bot.connect() はバックグラウンドで接続を確立し、on_ready を発火させる
        await bot.connect() # このコルーチンは、イベントループをブロックせず、バックグラウンドで動作を続けます。
        print("DEBUG: bot.connect() call returned. Now waiting for bot.wait_until_ready() (on_ready to fire).", file=sys.__stdout__)

        # ここから追加/変更
        # ボットが完全に準備できるまで待機するが、タイムアウトも設定する
        timeout_seconds = 60 # 60秒待機
        try:
            print(f"DEBUG: Waiting for bot to be ready (on_ready event) for up to {timeout_seconds} seconds...", file=sys.__stdout__)
            await asyncio.wait_for(bot.wait_until_ready(), timeout=timeout_seconds)
            print("DEBUG: bot.wait_until_ready() completed successfully! Bot is READY.", file=sys.__stdout__)
        except asyncio.TimeoutError:
            print(f"FATAL ERROR: bot.wait_until_ready() timed out after {timeout_seconds} seconds. on_ready did not fire.", file=sys.__stderr__)
            print("FATAL ERROR: The bot did not become ready within the expected timeframe. Exiting.", file=sys.__stderr__)
            sys.exit(1) # タイムアウトしたら強制終了

        print("DEBUG: main() function reached end of bot startup logic. Bot should now be fully operational.", file=sys.__stdout__)

    except discord.LoginFailure:
        print("FATAL ERROR: Token authentication failed. Please check DISCORD_BOT_TOKEN.", file=sys.__stderr__)
        sys.exit(1)
    except Exception as e:
        print(f"FATAL ERROR: Unexpected error occurred in main async function: {e}", file=sys.__stderr__)
        traceback.print_exc(file=sys.__stderr__)
        sys.exit(1)
print("DEBUG: Main async function 'main' defined.", file=sys.__stdout__)

# --- Program Entry Point ---
if __name__ == '__main__':
    print("DEBUG: Entering program entry point.", file=sys.__stdout__)
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    print("DEBUG: Event loop configured.", file=sys.__stdout__)

    print("DEBUG: Starting Discord Bot.", file=sys.__stdout__)
    try:
        # main() コルーチンを実行し、イベントループが終了するまで待機
        asyncio.run(main())
        print("DEBUG: asyncio.run(main()) completed (this line should only be reached if main() somehow completes after bot is ready).", file=sys.__stdout__)
    except Exception as e:
        print(f"FATAL ERROR: A critical error occurred during asyncio.run(main()): {e}", file=sys.__stdout__)
        traceback.print_exc(file=sys.__stdout__)
    print("DEBUG: After asyncio.run(main()) call (process may have terminated unexpectedly here).", file=sys.__stdout__)