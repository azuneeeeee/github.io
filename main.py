import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import traceback
import logging
import asyncio

print("DEBUG: main.py execution started - Initializing Discord bot.", file=sys.__stdout__) # Start of script execution

# Load environment variables from .env file
load_dotenv()
print("DEBUG: Environment variables loaded.", file=sys.__stdout__) # Env variables loaded

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO, # Set to INFO for more detailed Discord.py logs
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.__stdout__)

logging.getLogger('discord').setLevel(logging.INFO) # Discord logging to INFO
logging.getLogger('websockets').setLevel(logging.WARNING)
logging.getLogger('discord.app_commands.tree').setLevel(logging.WARNING)
print("DEBUG: Logging configured.", file=sys.__stdout__) # Logging setup

# --- Asyncio Unhandled Exception Handler ---
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"Async unhandled exception occurred: {msg}", file=sys.__stderr__)
    if "exception" in context:
        logging.error("Traceback:", exc_info=context["exception"], file=sys.__stderr__)
print("DEBUG: Asyncio exception handler set.", file=sys.__stdout__) # Exception handler set

# --- Discord Client Intents Configuration ---
intents = discord.Intents.all() # Ensure all intents are enabled
print("DEBUG: Intents configured (discord.Intents.all()).", file=sys.__stdout__) # Intents set

# --- Bot Instance Creation ---
try:
    bot = commands.Bot(command_prefix='!', intents=intents)
    print("DEBUG: Bot instance created.", file=sys.__stdout__) # Bot instance created
except Exception as e:
    print(f"FATAL ERROR: Failed to create bot instance: {e}", file=sys.__stderr__) # Bot instance creation failed
    sys.exit(1)

# --- on_ready Event Handler ---
@bot.event
async def on_ready():
    print("DEBUG: on_ready event started!", file=sys.__stdout__) # Event handler started
    try:
        print(f'DEBUG: on_ready: Logged in as {bot.user.name} (ID: {bot.user.id})', file=sys.__stdout__) # Logged in info
        print('------', file=sys.__stdout__) # Separator
        print("DEBUG: on_ready: Bot successfully connected to Discord!", file=sys.__stdout__) # Connection confirmation

        # Minimal status change
        print("DEBUG: on_ready: Setting bot status...", file=sys.__stdout__) # Status change initiation
        await asyncio.sleep(1)
        await bot.change_presence(activity=discord.Game(name="Online!"), status=discord.Status.online)
        print("DEBUG: on_ready: Status set to 'Online!'.", file=sys.__stdout__) # Status set

        print("DEBUG: on_ready event finished. Bot fully operational.", file=sys.__stdout__) # Event handler finished

    except Exception as e:
        print(f"FATAL ERROR: Unexpected error occurred within on_ready event: {e}", file=sys.__stderr__) # Error in on_ready
        traceback.print_exc(file=sys.__stderr__)
print("DEBUG: on_ready event handler defined.", file=sys.__stdout__) # on_ready handler definition

# --- Bot Startup Process ---
async def main():
    print("DEBUG: Main async function 'main()' started.", file=sys.__stdout__) # Main function start
    try:
        print("DEBUG: Calling bot.login()...", file=sys.__stdout__) # Login call
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            print("FATAL ERROR: 'DISCORD_BOT_TOKEN' environment variable is not set.", file=sys.__stderr__) # Token not set
            sys.exit(1)
        await bot.login(token)
        print("DEBUG: bot.login() completed. Waiting for gateway connection...", file=sys.__stdout__) # Login completed

        print("DEBUG: Calling bot.connect()...", file=sys.__stdout__) # Connect call
        await bot.connect()
        print("DEBUG: bot.connect() completed. Bot should be online now.", file=sys.__stdout__) # Connect completed

        print("DEBUG: main() function reached end of bot.connect() call. This process should now be managed by discord.py's event loop.", file=sys.__stdout__)

    except discord.LoginFailure:
        print("FATAL ERROR: Token authentication failed. Please check DISCORD_BOT_TOKEN.", file=sys.__stderr__) # Login failure
        sys.exit(1)
    except Exception as e:
        print(f"FATAL ERROR: Unexpected error occurred in main async function: {e}", file=sys.__stderr__) # Error in main func
        traceback.print_exc(file=sys.__stderr__)
        sys.exit(1)
print("DEBUG: Main async function 'main' defined.", file=sys.__stdout__) # Main func definition

# --- Program Entry Point ---
if __name__ == '__main__':
    print("DEBUG: Entering program entry point.", file=sys.__stdout__) # Entry point
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    print("DEBUG: Event loop configured.", file=sys.__stdout__) # Event loop config

    print("DEBUG: Starting Discord Bot.", file=sys.__stdout__) # Bot start
    try:
        asyncio.run(main())
        print("DEBUG: asyncio.run(main()) completed.", file=sys.__stdout__) # asyncio.run completed
    except Exception as e:
        print(f"FATAL ERROR: A critical error occurred during asyncio.run(main()): {e}", file=sys.__stdout__) # Error during asyncio.run
        traceback.print_exc(file=sys.__stdout__)
    print("DEBUG: After asyncio.run(main()) call (process may have terminated unexpectedly here).", file=sys.__stdout__) # After asyncio.run