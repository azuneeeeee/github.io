import os
import discord
from discord.ext import commands
import json
import asyncio
import traceback
import logging
from discord import app_commands # app_commands.CheckFailure のために必要

# ロギング設定
logging.basicConfig(level=logging.INFO,
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
    except ValueError:
        logging.critical(f"APPLICATION_ID environment variable '{_application_id_str}' is not a valid integer. Using default 0.", exc_info=True)
        APPLICATION_ID = 0
else:
    logging.critical("APPLICATION_ID environment variable is not set. Using default 0. Please set it in Render's Environment settings or .env file.")
    APPLICATION_ID = 0

SONGS_FILE = 'data/songs.py'

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # メッセージ内容のインテントを有効にする
        intents.members = True # メンバー情報を取得するために必要
        intents.guilds = True # ギルド情報（ロールなど）を取得するために必要

        super().__init__(
            command_prefix=commands.when_mentioned_or('!'), 
            intents=intents,
            application_id=APPLICATION_ID 
        )
        self.initial_extensions = [
            'cogs.pjsk_ap_fc_rate',      
            'cogs.proseka_general',      
            'cogs.help_command',         
            'cogs.proseka_rankmatch',    
            'cogs.pjsk_rankmatch_result',
            'cogs.pjsk_record_result',   
            'cogs.premium_features'      
        ]
        self.proseka_songs_data = [] 
        self.valid_difficulties_data = ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"] 
        self.is_bot_ready = False 

        # コグ参照のための属性を初期化
        self.proseka_general_cog = None
        self.proseka_rankmatch_cog = None
        self.pjsk_ap_fc_rate_cog = None
        self.pjsk_record_result_cog = None
        self.help_command_cog = None
        self.pjsk_rankmatch_result_cog = None 
        self.premium_manager_cog = None 

        # ボットインスタンスにオーナーIDとギルドIDを保存
        self.OWNER_ID = OWNER_ID
        self.GUILD_ID = GUILD_ID # グローバルチェックで使用するため bot オブジェクトに設定

        logging.info("Bot instance created.")

    async def _load_songs_data_async(self):
        """data/songs.py から楽曲データを非同期で読み込む"""
        logging.info(f"Attempting to load songs data from {SONGS_FILE} asynchronously.")
        try:
            loop = asyncio.get_running_loop()
            with open(SONGS_FILE, 'r', encoding='utf-8') as f:
                file_content = await loop.run_in_executor(None, f.read)
            
            _globals = {}
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
        logging.info("Starting setup_hook...")
        
        await self._load_songs_data_async()

        for extension in self.initial_extensions:
            try:
                logging.info(f"Loading extension: {extension}...")
                await self.load_extension(extension)
                logging.info(f"Successfully loaded {extension}.")
            except commands.ExtensionNotFound:
                logging.error(f"Extension '{extension}' not found. Check file name and path.", exc_info=True)
            except commands.ExtensionFailed as e:
                logging.error(f"Extension '{extension}' failed to load due to an internal error. Check the cog's code.", exc_info=True)
            except commands.NoEntryPointError:
                logging.error(f"Extension '{extension}' has no 'setup' function. Make sure 'async def setup(bot):' is defined.", exc_info=True)
            except commands.ExtensionAlreadyLoaded:
                logging.warning(f"Extension '{extension}' is already loaded. Skipping.")
            except Exception as e:
                logging.error(f"An unexpected error occurred while loading extension '{extension}': {e}", exc_info=True)

        # 全てのコグがロードされた後に、コグ参照を設定
        logging.info("Attempting to set cog references and song data.")
        self.proseka_general_cog = self.get_cog("ProsekaGeneralCommands")
        self.proseka_rankmatch_cog = self.get_cog("ProsekaRankMatchCommands")
        self.pjsk_ap_fc_rate_cog = self.get_cog("PjskApFcRateCommands")
        self.pjsk_record_result_cog = self.get_cog("PjskRecordResult")
        self.help_command_cog = self.get_cog("HelpCommand")
        self.pjsk_rankmatch_result_cog = self.get_cog("ProsekaRankmatchResult") 
        self.premium_manager_cog = self.get_cog("PremiumManagerCog") 

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
            logging.warning("PremiumManagerCog not found after loading.")

        # 相互参照の設定 (AP/FCレートの自動更新のため)
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
            
        # コマンドの同期 (既存のコード)
        logging.info("Attempting to sync commands...")
        try:
            # まずグローバルコマンドを同期
            # setup_hookで一度グローバル同期を試みることで、"/sync" コマンド自体も登録されることを期待する
            synced_global = await self.tree.sync() 
            logging.info(f"Synced {len(synced_global)} global commands.")

            if self.GUILD_ID != 0: 
                support_guild = discord.Object(id=self.GUILD_ID)
                # グローバルコマンドをギルドにコピーしてから同期（重要）
                # これにより、ギルドコマンドとして登録されたものも更新される
                self.tree.copy_global_to(guild=support_guild) 
                synced_guild_commands = await self.tree.sync(guild=support_guild)
                logging.info(f"Synced {len(synced_guild_commands)} commands to support guild {self.GUILD_ID}.")
            else:
                logging.warning("GUILD_ID is not set or invalid (0). Skipping guild command sync.")

        except Exception as e:
            logging.error(f"Failed to sync commands: {e}", exc_info=True)

        logging.info("setup_hook completed.")

    # on_app_command イベントハンドラ
    async def on_app_command(self, interaction: discord.Interaction):
        # ボットの現在のステータスが「取り込み中 (Do Not Disturb)」であるか確認
        if interaction.client.user.status == discord.Status.dnd:
            # もしボットが「取り込み中」で、かつコマンド実行者がオーナーではない場合
            if interaction.user.id != self.OWNER_ID: 
                await interaction.response.send_message(
                    "現在、ボットは管理者モードです。全てのコマンドは製作者のみが利用できます。",
                    ephemeral=True # 他のユーザーには見えないメッセージ
                )
                return # ここで処理を終了し、コマンド実行を停止
        
        # オーナーであるか、ボットが「取り込み中」でない場合は、通常のコマンド処理を続行
        # ここには何も書かないことで、discord.py の内部が引き続きコマンドをディスパッチします。

    async def on_ready(self):
        logging.info(f"Logged in as {self.user.name} (ID: {self.user.id})")
        logging.info("------")
        
        self.is_bot_ready = True 
        
        total_songs = len(self.proseka_songs_data)
        total_charts = 0
        for song in self.proseka_songs_data:
            total_charts += sum(1 for diff in self.valid_difficulties_data if diff.lower() in song and song[diff.lower()] is not None)
        
        activity_message = f"{total_songs}曲/{total_charts}譜面が登録済み"
        await self.change_presence(activity=discord.Game(name=activity_message))
        logging.info(f"Status set to: {activity_message}")
        logging.info("Bot is fully ready and accepting commands.")

        # PremiumManagerCog のタスクを起動
        # コグへの参照が設定され、かつコグのセットアップが完了していることを確認
        if self.premium_manager_cog and hasattr(self.premium_manager_cog, 'is_setup_complete') and self.premium_manager_cog.is_setup_complete: 
            if hasattr(self.premium_manager_cog, 'patreon_sync_task') and not self.premium_manager_cog.patreon_sync_task.is_running():
                logging.info("Starting Patreon sync task in PremiumManagerCog.")
                self.premium_manager_cog.patreon_sync_task.start()
            else:
                logging.warning("Patreon sync task already running or not found in PremiumManagerCog on_ready.")
        else:
            logging.warning("PremiumManagerCog not found or not fully set up, cannot start Patreon sync task on_ready.")


    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return 
        logging.error(f"An error occurred in command {ctx.command}: {error}", exc_info=True)
        await ctx.send(f"エラーが発生しました: {error}")

    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        if interaction.response.is_done():
            logging.error(f"App command error (interaction already responded): {error}", exc_info=True)
            return

        if isinstance(error, discord.errors.NotFound) and error.code == 10062:
            logging.error(f"Unknown interaction (404 Not Found) for command '{interaction.command.name}' by user {interaction.user.id}. Interaction might have timed out before defer/response.", exc_info=True)
            try:
                await interaction.followup.send("申し訳ありません、操作がタイムアウトしたか、無効になりました。もう一度お試しください。", ephemeral=True)
            except Exception as e:
                logging.error(f"Failed to send follow-up for Unknown interaction error: {e}", exc_info=True)
            return
            
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
            
        logging.error(f"An unexpected error occurred during app command '{interaction.command.name}' by {interaction.user.id}: {error}", exc_info=True)
        try:
            if interaction.is_acknowledged():
                await interaction.followup.send(f"コマンドの実行中に予期せぬエラーが発生しました: `{error}`", ephemeral=True)
            else:
                await interaction.response.send_message(f"コマンドの実行中に予期せぬエラーが発生しました: `{error}`", ephemeral=True)
        except discord.errors.InteractionResponded:
            pass
        except Exception as e:
            logging.error(f"Failed to send error message to user: {e}", exc_info=True)

    # オーナー判定デコレータ
    def is_bot_owner():
        async def predicate(interaction: discord.Interaction):
            if hasattr(interaction.client, 'OWNER_ID') and interaction.user.id == interaction.client.OWNER_ID:
                return True
            await interaction.response.send_message("このコマンドはボットのオーナーのみが実行できます。", ephemeral=True)
            return False
        return app_commands.check(predicate)

    # デバッグ用の同期コマンド
    @app_commands.command(name="sync", description="スラッシュコマンドをDiscordと同期します (オーナー限定)。")
    @is_bot_owner()
    @app_commands.guilds(discord.Object(id=GUILD_ID)) # GUILD_ID は MyBot の属性としてアクセス
    async def sync_commands(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        sync_status_message = ""
        try:
            # グローバルコマンドを同期
            synced_global = await self.tree.sync()
            sync_status_message += f"グローバルコマンドを同期しました: {len(synced_global)}個\n"
            logging.info(f"Globally synced {len(synced_global)} commands via /sync.")
        except Exception as e:
            sync_status_message += f"グローバルコマンドの同期に失敗しました: {e}\n"
            logging.error(f"Failed to global sync commands via /sync: {e}", exc_info=True)

        if self.GUILD_ID != 0:
            try:
                guild_obj = discord.Object(id=self.GUILD_ID)
                # グローバルコマンドをギルドにコピーしてから同期
                self.tree.copy_global_to(guild=guild_obj)
                synced_guild_commands = await self.tree.sync(guild=guild_obj)
                sync_status_message += f"このギルド ({self.GUILD_ID}) のコマンドを同期しました: {len(synced_guild_commands)}個"
                logging.info(f"Guild ({self.GUILD_ID}) synced {len(synced_guild_commands)} commands via /sync.")
            except Exception as e:
                sync_status_message += f"ギルドコマンドの同期に失敗しました: {e}"
                logging.error(f"Failed to guild sync commands via /sync: {e}", exc_info=True)
        else:
            sync_status_message += "GUILD_ID が設定されていないため、ギルドコマンドの同期はできません。"
            logging.warning("GUILD_ID not set, skipping guild command sync via /sync.")
        
        await interaction.followup.send(sync_status_message, ephemeral=True)


from cogs.pjsk_record_result import _create_song_data_map

def run_bot():
    bot = MyBot()

    if TOKEN:
        bot.run(TOKEN)
    else:
        logging.critical("DISCORD_BOT_TOKEN is not set. Please set it in Render's Environment settings or .env file.")

if __name__ == '__main__':
    run_bot()
