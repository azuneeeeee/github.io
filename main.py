import os
import discord
from discord.ext import commands
import json
import asyncio
import traceback
import logging
from datetime import datetime, timedelta, timezone
from discord import app_commands

# ロギング設定
logging.basicConfig(level=logging.INFO, # INFOレベルでログを出力
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv()

# 環境変数を安全に読み込む
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

_guild_id_str = os.getenv('GUILD_ID')
if _guild_id_str:
    try:
        GUILD_ID = int(_guild_id_str)
        if GUILD_ID == 0:
            logging.critical("GUILD_ID environment variable is set to 0. This is usually unintended for guild-specific commands. Please ensure it's a valid guild ID.")
    except ValueError:
        logging.critical(f"GUILD_ID environment variable '{_guild_id_str}' is not a valid integer. Using default 0.", exc_info=True)
        GUILD_ID = 0
else:
    logging.critical("GUILD_ID environment variable is not set. Using default 0. Please set it in Render's Environment settings or .env file.")
    GUILD_ID = 0

_owner_id_str = os.getenv('OWNER_ID')
if _owner_id_str:
    try:
        OWNER_ID = int(_owner_id_str)
        if OWNER_ID == 0:
            logging.critical("OWNER_ID environment variable is set to 0. This is usually unintended. Please ensure it's a valid user ID.")
    except ValueError:
        logging.critical(f"OWNER_ID environment variable '{_owner_id_str}' is not a valid integer. Using default 0.", exc_info=True)
        OWNER_ID = 0
else:
    logging.critical("OWNER_ID environment variable is not set. Using default 0. Please set it in Render's Environment settings or .env file.")
    OWNER_ID = 0

_application_id_str = os.getenv('APPLICATION_ID')
if _application_id_str:
    try:
        APPLICATION_ID = int(_application_id_str)
        if APPLICATION_ID == 0:
            logging.critical("APPLICATION_ID environment variable is set to 0. Global slash commands will not register correctly. Please ensure it's a valid application ID.")
    except ValueError:
        logging.critical(f"APPLICATION_ID environment variable '{_application_id_str}' is not a valid integer. Using default 0.", exc_info=True)
        APPLICATION_ID = 0
else:
    logging.critical("APPLICATION_ID environment variable is not set. Using default 0. Global slash commands will not register correctly. Please set it in Render's Environment settings or .env file.")
    APPLICATION_ID = 0

SONGS_FILE = 'data/songs.py'

# グローバルなオーナー判定デコレータ関数 (スラッシュコマンド用)
def is_bot_owner():
    """
    Checks if the slash command was executed by the bot's owner.
    """
    async def predicate(interaction: discord.Interaction):
        # Use bot.owner_id if set, otherwise use the OWNER_ID environment variable.
        # (bot.owner_id should always be set via super().__init__ if OWNER_ID is provided)
        actual_owner_id = interaction.client.owner_id if interaction.client.owner_id else interaction.client.OWNER_ID
        if interaction.user.id == actual_owner_id:
            return True
        await interaction.response.send_message("このコマンドはボットのオーナーのみが実行できます。", ephemeral=True)
        return False
    return app_commands.check(predicate)

class MyBot(commands.Bot):
    """
    Custom Discord bot class. Manages cogs and defines event handlers.
    """
    def __init__(self):
        # Set default intents and enable message content, members, and guild intents.
        intents = discord.Intents.default()
        intents.message_content = True  # Enable message content intent
        intents.members = True # Required to fetch member information
        intents.guilds = True # Required to fetch guild information (e.g., roles)

        super().__init__(
            command_prefix=commands.when_mentioned_or('!'), # Command prefix (e.g., !help)
            intents=intents,
            application_id=APPLICATION_ID, # Required for slash command synchronization
            owner_id=OWNER_ID # Required for commands.is_owner() decorator
        )
        # List of cogs to load
        self.initial_extensions = [
            'cogs.pjsk_ap_fc_rate',
            'cogs.proseka_general',
            'cogs.help_command',
            'cogs.proseka_rankmatch',
            'cogs.pjsk_rankmatch_result',
            'cogs.pjsk_record_result',
            'cogs.premium_features',
            'cogs.debug_commands', # Debug cog
            'cogs.status_commands' # Status command cog
        ]
        self.proseka_songs_data = [] # Project SEKAI song data
        self.valid_difficulties_data = ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"] # List of valid difficulties
        self.is_bot_ready = False # Flag to indicate if the bot is ready
        self.is_admin_mode_active = False # ★追加: 管理者モードの状態を保持するフラグ

        # Initialize attributes for cog references (will be set after cogs are loaded)
        self.proseka_general_cog = None
        self.proseka_rankmatch_cog = None
        self.pjsk_ap_fc_rate_cog = None
        self.pjsk_record_result_cog = None
        self.help_command_cog = None
        self.pjsk_rankmatch_result_cog = None
        self.premium_manager_cog = None
        self.debug_commands_cog = None
        self.status_commands_cog = None

        # Store OWNER_ID and GUILD_ID in the bot instance
        self.OWNER_ID = OWNER_ID 
        self.GUILD_ID = GUILD_ID 

        logging.info("Bot instance created.")

    async def _load_songs_data_async(self):
        """Loads song data from data/songs.py asynchronously."""
        logging.info(f"Attempting to load songs data from {SONGS_FILE} asynchronously.")
        try:
            loop = asyncio.get_running_loop()
            with open(SONGS_FILE, 'r', encoding='utf-8') as f:
                file_content = await loop.run_in_executor(None, f.read)

            _globals = {}
            # Execute the file content to get proseka_songs and VALID_DIFFICULTIES
            await loop.run_in_executor(None, exec, file_content, _globals)

            self.proseka_songs_data = _globals.get('proseka_songs', [])
            self.valid_difficulties_data = _globals.get('VALID_DIFFICULTIES', ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"])
            
            if not isinstance(self.proseka_songs_data, list):
                logging.error(f"proseka_songs in {SONGS_FILE} is not a list. Type: {type(self.proseka_songs_data)}. Using empty list.")
                self.proseka_songs_data = []

            if not isinstance(self.valid_difficulties_data, list):
                logging.error(f"VALID_DIFFICULTIES in {SONGS_FILE} is not a list. Type: {type(self.valid_difficulties_data)}. Using default list.")
                self.valid_difficulties_data = ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"]

            logging.info(f"{SONGS_FILE} から {len(self.proseka_songs_data)} 曲の楽曲データを非同期で正常に読み込みました。")

        except FileNotFoundError:
            logging.critical(f"{SONGS_FILE} が見つかりません。'data'フォルダにあることを確認してください。", exc_info=True)
            self.proseka_songs_data = []
            self.valid_difficulties_data = ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"]
        except Exception as e:
            logging.critical(f"Error executing {SONGS_FILE} or converting data: {e}", exc_info=True)
            self.proseka_songs_data = []
            self.valid_difficulties_data = ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"]


    async def setup_hook(self):
        """Called when the bot is starting up to load cogs and synchronize slash commands."""
        logging.info("Starting setup_hook...")

        await self._load_songs_data_async() # Load song data asynchronously

        # Load all initial extensions (cogs)
        for extension in self.initial_extensions:
            try:
                logging.info(f"Attempting to load extension: {extension}...")
                await self.load_extension(extension)
                logging.info(f"Successfully loaded extension: {extension}.")
            except commands.ExtensionNotFound:
                logging.error(f"ExtensionNotFound: Extension '{extension}' not found. Check file name and path.", exc_info=True)
            except commands.ExtensionFailed as e:
                logging.error(f"ExtensionFailed: Extension '{extension}' failed to load due to an internal error. Check the cog's code. Error: {e}", exc_info=True)
            except commands.NoEntryPointError:
                logging.error(f"NoEntryPointError: Extension '{extension}' has no 'setup' function. Make sure 'async def setup(bot):' is defined.", exc_info=True)
            except commands.ExtensionAlreadyLoaded:
                logging.warning(f"ExtensionAlreadyLoaded: Extension '{extension}' is already loaded. Skipping.")
            except Exception as e:
                logging.error(f"An unexpected error occurred while loading extension '{extension}': {e}", exc_info=True)

        # --- DEBUG: Check bot.tree state after all cogs are loaded ---
        logging.info("--- DEBUG: Checking bot.tree after all cogs are loaded ---")
        global_commands_after_load = self.tree.get_commands(guild=None)
        logging.info(f"Global commands in bot.tree after loading cogs: {[cmd.name for cmd in global_commands_after_load]}")
        logging.info(f"Total global commands in bot.tree after loading cogs: {len(global_commands_after_load)}")

        if self.GUILD_ID != 0:
            guild_obj_for_debug = discord.Object(id=self.GUILD_ID)
            guild_commands_after_load = self.tree.get_commands(guild=guild_obj_for_debug)
            logging.info(f"Guild commands in bot.tree for GUILD_ID {self.GUILD_ID} after loading cogs: {[cmd.name for cmd in guild_commands_after_load]}")
            logging.info(f"Total guild commands in bot.tree for GUILD_ID {self.GUILD_ID} after loading cogs: {len(guild_commands_after_load)}")
        else:
            logging.info("GUILD_ID is 0, skipping guild command check in bot.tree after loading cogs.")
        logging.info("--- END DEBUG: bot.tree check ---")
        
        # After all cogs are loaded, set cog references
        logging.info("Attempting to set cog references and song data.")
        self.proseka_general_cog = self.get_cog("ProsekaGeneralCommands")
        self.proseka_rankmatch_cog = self.get_cog("ProsekaRankMatchCommands")
        self.pjsk_ap_fc_rate_cog = self.get_cog("PjskApFcRateCommands")
        self.pjsk_record_result_cog = self.get_cog("PjskRecordResult")
        self.help_command_cog = self.get_cog("HelpCommand")
        self.pjsk_rankmatch_result_cog = self.get_cog("ProsekaRankmatchResult")
        self.premium_manager_cog = self.get_cog("PremiumManagerCog")
        self.debug_commands_cog = self.get_cog("DebugCommands")
        self.status_commands_cog = self.get_cog("StatusCommands")

        # Set song data and difficulty data in relevant cogs
        if self.proseka_general_cog:
            self.proseka_general_cog.songs_data = self.proseka_songs_data
            self.proseka_general_cog.valid_difficulties = self.valid_difficulties_data
            logging.info("Set songs_data and valid_difficulties in ProsekaGeneralCommands.")
        else:
            logging.warning("ProsekaGeneralCommands cog not found after loading.")

        if self.proseka_rankmatch_cog:
            self.proseka_rankmatch_cog.songs_data = self.proseka_songs_data
            self.proseka_rankmatch_cog.valid_difficulties = self.valid_difficulties_data
            logging.info("Set songs_data and valid_difficulties in ProsekaRankMatchCommands.")
        else:
            logging.warning("ProsekaRankMatchCommands cog not found after loading.")

        if self.pjsk_record_result_cog:
            self.pjsk_record_result_cog.songs_data = self.proseka_songs_data
            # Import _create_song_data_map from the pjsk_record_result cog itself
            from cogs.pjsk_record_result import _create_song_data_map
            self.pjsk_record_result_cog.SONG_DATA_MAP = _create_song_data_map(self.proseka_songs_data)
            logging.info("Set songs_data and updated SONG_DATA_MAP in PjskRecordResult cog.")
        else:
            logging.warning("PjskRecordResult cog not found after loading.")

        if self.pjsk_rankmatch_result_cog:
            logging.info("PjskRankMatchResult cog found.")
        else:
            logging.warning("PjskRankMatchResult cog not found after loading.")

        if self.premium_manager_cog:
            self.premium_manager_cog.is_setup_complete = True
            logging.info("PremiumManagerCog found and setup complete flag set.")
        else:
            logging.warning("PremiumManagerCog not found or not fully set up, cannot start Patreon sync task on_ready.")
        
        if self.debug_commands_cog:
            logging.info("DebugCommands cog found.")
        else:
            logging.warning("DebugCommands cog not found after loading.")

        if self.status_commands_cog:
            logging.info("StatusCommands cog found.")
        else:
            logging.warning("StatusCommands cog not found after loading.")

        # Set cross-references (e.g., for automatic AP/FC rate updates)
        if self.proseka_general_cog and self.pjsk_ap_fc_rate_cog:
            self.proseka_general_cog.ap_fc_rate_cog = self.pjsk_ap_fc_rate_cog
            logging.info("Set ap_fc_rate_cog reference in ProsekaGeneralCommands.")
        else:
            logging.warning("Could not link ProsekaGeneralCommands and PjskApFcRateCommands cog.")

        if self.proseka_rankmatch_cog and self.pjsk_ap_fc_rate_cog:
            self.proseka_rankmatch_cog.ap_fc_rate_cog = self.pjsk_ap_fc_rate_cog
            logging.info("Set ap_fc_rate_cog reference in ProsekaRankMatchCommands.")
        else:
            logging.warning("Could not link ProsekaRankMatchCommands and PjskApFcRateCommands cog.")
            
        # Synchronize commands
        logging.info("Attempting to sync commands during setup_hook...")
        try:
            if self.GUILD_ID != 0:
                support_guild = discord.Object(id=self.GUILD_ID)
                
                # Synchronize all commands in the bot's internal tree to the specified guild.
                # This will copy global commands to the guild if they are not already there.
                self.tree.copy_global_to(guild=support_guild) # Ensure global commands are copied to guild
                synced_guild_commands = await self.tree.sync(guild=support_guild)
                logging.info(f"Synced {len(synced_guild_commands)} commands to support guild {self.GUILD_ID} during setup_hook.")
                
                # Debugging: check commands registered in bot's internal tree for the guild
                registered_commands_internal = [cmd.name for cmd in self.tree.get_commands(guild=support_guild)]
                logging.info(f"Commands registered in bot's internal tree for guild {self.GUILD_ID} after setup_hook sync: {registered_commands_internal}")
            else:
                logging.warning("GUILD_ID is not set or invalid (0). Skipping guild command sync during setup_hook.")
                # If GUILD_ID is not set, attempt global synchronization.
                synced_global = await self.tree.sync()
                logging.info(f"Synced {len(synced_global)} global commands (GUILD_ID not set) during setup_hook.")

        except Exception as e:
            logging.error(f"Failed to sync commands during setup_hook: {e}", exc_info=True)

        logging.info("setup_hook completed.")

    # on_app_command event handler
    async def on_app_command(self, interaction: discord.Interaction):
        """Handles slash command invocations, checking bot status for admin mode."""
        # コマンドが呼び出された際のログ出力
        logging.info(f"on_app_command triggered by user {interaction.user.name} (ID: {interaction.user.id}) for command /{interaction.command.name}. Bot's internal admin mode flag: {self.is_admin_mode_active}")

        # 管理者モードが有効になっているか、およびコマンド実行者がオーナーではないかチェック
        if self.is_admin_mode_active and interaction.user.id != self.OWNER_ID:
            logging.info(f"Non-owner user {interaction.user.name} (ID: {interaction.user.id}) attempted command /{interaction.command.name} while bot is in admin mode. Blocking.")
            
            # 既にレスポンス済みの場合、追加のレスポンスはできないためログのみ
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "現在、ボットは管理者モードです。全てのコマンドは製作者のみが利用できます。",
                    ephemeral=True # メッセージはコマンド実行者のみに見える
                )
            return # コマンドの実行をここで停止
        
        # オーナーである場合、または管理者モードではない場合は、
        # 通常のコマンド処理（discord.py の内部ディスパッチャーが処理）を続行します。

    async def on_ready(self):
        """Called when the bot connects to Discord and is ready."""
        logging.info(f"Logged in as {self.user.name} (ID: {self.user.id})")
        logging.info("------")
        
        self.is_bot_ready = True # Set bot ready flag
        
        # Set bot's status based on song data
        total_songs = len(self.proseka_songs_data)
        total_charts = 0
        for song in self.proseka_songs_data:
            total_charts += sum(1 for diff in self.valid_difficulties_data if diff.lower() in song and song[diff.lower()] is not None)
        
        activity_message = f"{total_songs}曲/{total_charts}譜面が登録済み"
        # Use custom activity
        activity = discord.CustomActivity(name=activity_message) 
        # 初期状態では通常オンラインに設定し、管理者モードフラグはFalse
        await self.change_presence(activity=activity, status=discord.Status.online) 
        self.is_admin_mode_active = False # ボット起動時は管理者モードを無効化
        
        logging.info(f"Status set to: {activity_message}")
        logging.info("Bot is fully ready and accepting commands.")

        # Start PremiumManagerCog's task
        # Ensure the cog reference is set and the cog's setup is complete
        if self.premium_manager_cog and hasattr(self.premium_manager_cog, 'is_setup_complete') and self.premium_manager_cog.is_setup_complete:
            if hasattr(self.premium_manager_cog, 'patreon_sync_task') and not self.premium_manager_cog.patreon_sync_task.is_running():
                logging.info("Starting Patreon sync task in PremiumManagerCog.")
                self.premium_manager_cog.patreon_sync_task.start()
            else:
                logging.warning("Patreon sync task already running or not found in PremiumManagerCog on_ready.")
        else:
            logging.warning("PremiumManagerCog not found or not fully set up, cannot start Patreon sync task on_ready.")

    async def on_command_error(self, ctx, error):
        """Handles prefix command errors."""
        if isinstance(error, commands.CommandNotFound):
            return # Ignore if command is not found
        logging.error(f"An error occurred in command {ctx.command}: {error}", exc_info=True)
        await ctx.send(f"エラーが発生しました: {error}")

    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        """Handles slash command errors."""
        # If interaction already responded, ignore error
        if interaction.response.is_done():
            logging.error(f"App command error (interaction already responded): {error}", exc_info=True)
            return

        # Discord API timeout error (Unknown interaction)
        if isinstance(error, discord.errors.NotFound) and error.code == 10062:
            logging.error(f"Unknown interaction (404 Not Found) for command '{interaction.command.name}' by user {interaction.user.id}. Interaction might have timed out before defer/response.", exc_info=True)
            try:
                await interaction.followup.send("申し訳ありません、操作がタイムアウトしたか、無効になりました。もう一度お試しください。", ephemeral=True)
            except Exception as e:
                logging.error(f"Failed to send follow-up for Unknown interaction error: {e}", exc_info=True)
            return
            
        # Other app_commands.CheckFailure errors (missing role, cooldown, etc.)
        if isinstance(error, app_commands.CheckFailure):
            if isinstance(error, app_commands.MissingRole):
                logging.warning(f"Missing role for user {interaction.user.id} on command '{interaction.command.name}'. Role ID: {error.missing_role}")
                await interaction.response.send_message(f"このコマンドを実行するには、必要なロールがありません。", ephemeral=True)
            elif isinstance(error, app_commands.NoPrivateMessage):
                logging.warning(f"Private message usage for command '{interaction.command.name}' by user {interaction.user.id}.")
                await interaction.response.send_message("このコマンドはDMでは実行できません。", ephemeral=True)
            elif isinstance(error, app_commands.CommandOnCooldown):
                logging.warning(f"Command '{interaction.command.name}' on cooldown for user {interaction.user.id}. Retry after {error.retry_after:.2f}s.")
                await interaction.response.send_message(f"このコマンドはクールダウン中です。{error.retry_after:.2f}秒後に再試行してください。", ephemeral=True)
            elif isinstance(error, app_commands.MissingPermissions):
                logging.warning(f"Missing permissions for user {interaction.user.id} on command '{interaction.command.name}'. Permissions: {error.missing_permissions}")
                await interaction.response.send_message(f"このコマンドを実行するための権限がありません。", ephemeral=True)
            else:
                logging.warning(f"Generic CheckFailure for command '{interaction.command.name}' by user {interaction.user.id}: {error}")
                await interaction.response.send_message(f"このコマンドを実行できませんでした（権限エラーなど）。", ephemeral=True)
            return
            
        # Unexpected errors
        logging.error(f"An unexpected error occurred during app command '{interaction.command.name}' by {interaction.user.id}: {error}", exc_info=True)
        try:
            if interaction.is_acknowledged():
                await interaction.followup.send(f"コマンドの実行中に予期せぬエラーが発生しました: `{error}`", ephemeral=True)
            else:
                await interaction.response.send_message(f"コマンドの実行中に予期せぬエラーが発生しました: `{error}`", ephemeral=True)
        except discord.errors.InteractionResponded:
            pass # Already responded, so ignore
        except Exception as e:
            logging.error(f"Failed to send error message to user: {e}", exc_info=True)

# Import _create_song_data_map from cogs.pjsk_record_result
# This is used in setup_hook to initialize song data for the cog.
from cogs.pjsk_record_result import _create_song_data_map

def run_bot():
    """Initializes and runs the bot."""
    bot = MyBot()

    if TOKEN:
        bot.run(TOKEN)
    else:
        logging.critical("DISCORD_BOT_TOKEN is not set. Please set it in Render's Environment settings or .env file.")

if __name__ == '__main__':
    run_bot()
