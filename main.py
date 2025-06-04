import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import traceback
import asyncio
import logging # logging モジュールをインポート

# ロギング設定
# INFOレベルで基本的な情報を出力。より詳細なデバッグが必要な場合は DEBUG に変更
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
# discord.py の内部ログをより詳細に見たい場合は、以下の行のコメントを外す
# logging.getLogger('discord').setLevel(logging.DEBUG)
# logging.getLogger('discord.http').setLevel(logging.INFO) # HTTPリクエストはINFOで十分

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID')) if os.getenv('OWNER_ID') else None

SUPPORT_GUILD_ID = 1376551581423767582 

class MyBot(commands.Bot):
    def __init__(self):
        logging.info("MyBot.__init__ started.")
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.presences = True

        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            owner_id=OWNER_ID
        )

        self.initial_extensions = [
            'cogs.pjsk_ap_fc_rate',      
            'cogs.proseka_general',      
            'cogs.help_command',
            'cogs.proseka_rankmatch',
            'cogs.pjsk_rankmatch_result',
            'cogs.pjsk_record_result'    
        ]

        self.total_songs = 0
        self.total_charts = 0
        self.proseka_songs_data = [] # 楽曲データをここに保持
        self.valid_difficulties_data = [] # 難易度データをここに保持
        self.is_bot_ready = False # ボットがコマンドを受け付ける準備ができたかどうかのフラグ
        logging.info("MyBot.__init__ completed. is_bot_ready set to False.")

    async def _load_songs_data_async(self):
        """data/songs.py から楽曲データを非同期で読み込む"""
        songs_file_path = 'data/songs.py'
        logging.info(f"Attempting to load songs data from {songs_file_path} asynchronously.")
        try:
            loop = asyncio.get_running_loop()
            with open(songs_file_path, 'r', encoding='utf-8') as f:
                file_content = await loop.run_in_executor(None, f.read)
            
            _globals = {}
            await loop.run_in_executor(None, exec, file_content, _globals)

            self.proseka_songs_data = _globals.get('proseka_songs', [])
            self.valid_difficulties_data = _globals.get('VALID_DIFFICULTIES', ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"])
            
            if not isinstance(self.proseka_songs_data, list):
                logging.error(f"proseka_songs in {songs_file_path} is not a list. Type: {type(self.proseka_songs_data)}. Using empty list.")
                self.proseka_songs_data = []

            if not isinstance(self.valid_difficulties_data, list):
                logging.error(f"VALID_DIFFICULTIES in {songs_file_path} is not a list. Type: {type(self.valid_difficulties_data)}. Using default list.")
                self.valid_difficulties_data = ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"]

            logging.info(f"{songs_file_path} から {len(self.proseka_songs_data)} 曲の楽曲データを非同期で正常に読み込みました。")

        except FileNotFoundError:
            logging.critical(f"{songs_file_path} が見つかりません。'data'フォルダにあることを確認してください。")
            self.proseka_songs_data = []
            self.valid_difficulties_data = ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"]
        except Exception as e:
            logging.critical(f"Error executing {songs_file_path} or converting data: {e}", exc_info=True)
            self.proseka_songs_data = []
            self.valid_difficulties_data = ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"]

    async def setup_hook(self) -> None:
        logging.info("Running setup_hook...")
        await self._load_songs_data_async()

        logging.info("Starting extension loading loop.")
        for extension in self.initial_extensions:
            logging.info(f"Attempting to load {extension}...")
            try:
                # ★重要: load_extension に songs_data や valid_difficulties を渡さない
                await self.load_extension(extension)
                logging.info(f"Successfully loaded {extension}")
            except Exception as e:
                logging.error(f"Failed to load {extension}: {e}", exc_info=True)

        logging.info("Attempting to set cog references and song data.")
        try:
            proseka_general_cog = self.get_cog("ProsekaGeneralCommands")
            if proseka_general_cog:
                proseka_general_cog.songs_data = self.proseka_songs_data
                proseka_general_cog.valid_difficulties = self.valid_difficulties_data
                logging.info("Set songs_data and valid_difficulties in ProsekaGeneralCommands.")
            else:
                logging.warning("ProsekaGeneralCommands cog not found after loading.")

            rankmatch_cog = self.get_cog("ProsekaRankMatchCommands")
            if rankmatch_cog:
                rankmatch_cog.songs_data = self.proseka_songs_data
                rankmatch_cog.valid_difficulties = self.valid_difficulties_data
                logging.info("Set songs_data and valid_difficulties in ProsekaRankMatchCommands.")
            else:
                logging.warning("ProsekaRankMatchCommands cog not found after loading.")

            ap_fc_rate_cog = self.get_cog("PjskApFcRateCommands") 
            if proseka_general_cog and ap_fc_rate_cog:
                proseka_general_cog.ap_fc_rate_cog = ap_fc_rate_cog
                logging.info("Set ap_fc_rate_cog reference in ProsekaGeneralCommands.")
            else:
                logging.warning("Could not get ProsekaGeneralCommands or PjskApFcRateCommands cog for linking. Check cog names or load order.")

            if rankmatch_cog and ap_fc_rate_cog:
                rankmatch_cog.ap_fc_rate_cog = ap_fc_rate_cog
                logging.info("Set ap_fc_rate_cog reference in ProsekaRankMatchCommands.")
            else:
                logging.warning("Could not get ProsekaRankMatchCommands or PjskApFcRateCommands cog for linking. Check cog names or load order.")

        except Exception as e:
            logging.error(f"Failed to link cogs or set song data: {e}", exc_info=True)


        logging.info("Attempting to sync commands...")
        try:
            global_synced = await self.tree.sync()
            logging.info(f"Synced {len(global_synced)} global commands.")
            # for cmd in global_synced: # デバッグログが多すぎる場合があるのでコメントアウト
            #     logging.debug(f"  - Synced global command: {cmd.name}")

            support_guild = discord.Object(id=SUPPORT_GUILD_ID)
            guild_synced = await self.tree.sync(guild=support_guild)
            logging.info(f"Synced {len(guild_synced)} commands to support guild {SUPPORT_GUILD_ID}.")
            # for cmd in guild_synced: # デバッグログが多すぎる場合があるのでコメントアウト
            #     logging.debug(f"  - Synced guild command: {cmd.name}")

        except Exception as e:
            logging.critical(f"Failed to sync commands: {e}", exc_info=True)

    async def on_ready(self):
        logging.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logging.info('------')

        self.total_songs = len(self.proseka_songs_data)
        self.total_charts = 0
        for song in self.proseka_songs_data:
            chart_count_for_song = 0
            for diff_key in self.valid_difficulties_data:
                if song.get(diff_key.lower()) is not None:
                    chart_count_for_song += 1
            self.total_charts += chart_count_for_song

        activity_name = f"{self.total_songs}曲/{self.total_charts}譜面が登録済み"
        await self.change_presence(activity=discord.Game(name=activity_name))
        logging.info(f"Status set to: {activity_name}")
        
        self.is_bot_ready = True
        logging.info("Bot is fully ready and accepting commands.")

        # logging.debug("\nChecking commands after on_ready:") # デバッグログが多すぎる場合があるのでコメントアウト
        # all_commands_in_tree = self.tree.get_commands()
        # if all_commands_in_tree:
        #     logging.debug(f"Found {len(all_commands_in_tree)} total commands in bot.tree (global/guild):")
        #     for cmd in all_commands_in_tree:
        #         guild_status = f"Guilds: {cmd.guild_ids}" if hasattr(cmd, 'guild_ids') and cmd.guild_ids else \
        #                        f"Guild: {cmd.guild.id}" if hasattr(cmd, 'guild') and cmd.guild else "Global"
        #         cmd_type_str = str(cmd.type) if hasattr(cmd, 'type') else "Unknown Type"
        #         logging.debug(f"  - Name: {cmd.name}, Type: {cmd_type_str}, {guild_status}")
        # else:
        #     logging.debug(f"No commands found in bot.tree at all.")

        # guild_commands_in_tree = self.tree.get_commands(guild=discord.Object(id=SUPPORT_GUILD_ID))
        # if guild_commands_in_tree:
        #     logging.debug(f"Found {len(guild_commands_in_tree)} commands in bot.tree for guild {SUPPORT_GUILD_ID}:")
        #     for cmd in guild_commands_in_tree:
        #         logging.debug(f"  - {cmd.name}")
        # else:
        #     logging.debug(f"No commands explicitly found for guild {SUPPORT_GUILD_ID} in bot.tree.")

    # ★追加: グローバルエラーハンドラー
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        logging.error(f"Caught an AppCommandError for command '{interaction.command.name}' by user '{interaction.user.name}'.")
        if isinstance(error, app_commands.CommandInvokeError):
            original_error = error.original
            if isinstance(original_error, discord.errors.NotFound) and original_error.code == 10062:
                logging.error(f"Specific error: Unknown interaction (10062). Details: {original_error}")
                if not interaction.response.is_done():
                    try:
                        await interaction.response.send_message(
                            "ボットの起動中または一時的な通信エラーにより、コマンドを処理できませんでした。しばらく待ってからもう一度お試しください。",
                            ephemeral=True
                        )
                        logging.info("Sent 'temporary error' message to user.")
                    except discord.errors.InteractionResponded:
                        logging.warning("Tried to send 'temporary error' message but interaction was already responded to.")
                    except Exception as e:
                        logging.critical(f"Failed to send error message for Unknown interaction: {e}", exc_info=True)
                else:
                    logging.debug("Interaction already responded to, cannot send error message for Unknown interaction.")
            else:
                logging.error(f"Unhandled CommandInvokeError in command '{interaction.command.name}': {original_error}", exc_info=True)
                if not interaction.response.is_done():
                    try:
                        await interaction.response.send_message(
                            f"コマンドの実行中に予期せぬエラーが発生しました: `{original_error}`",
                            ephemeral=True
                        )
                    except discord.errors.InteractionResponded:
                        pass
                    except Exception as e:
                        logging.critical(f"Failed to send generic error message: {e}", exc_info=True)
        else:
            logging.error(f"Unhandled AppCommandError in command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(
                        f"コマンドの実行中にエラーが発生しました: `{error}`",
                        ephemeral=True
                    )
                except discord.errors.InteractionResponded:
                    pass
                except Exception as e:
                    logging.critical(f"Failed to send generic error message: {e}", exc_info=True)

    # ★追加: 診断用pingコマンド
    @app_commands.command(name="ping", description="ボットの応答性をテストします。")
    async def ping(self, interaction: discord.Interaction):
        logging.info(f"/ping command invoked by {interaction.user.name}.")
        start_time = discord.utils.utcnow()
        try:
            await interaction.response.defer(ephemeral=True) # ephemeralで応答
            latency = (discord.utils.utcnow() - start_time).total_seconds() * 1000
            await interaction.followup.send(f"Pong! 🏓\nボットのレイテンシ: {self.latency * 1000:.2f}ms\n応答までの時間: {latency:.2f}ms", ephemeral=True)
            logging.info(f"/ping command successful for {interaction.user.name}. Latency: {self.latency * 1000:.2f}ms, Response time: {latency:.2f}ms.")
        except Exception as e:
            logging.error(f"Error processing /ping command for {interaction.user.name}: {e}", exc_info=True)
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message("Pingコマンドの処理中にエラーが発生しました。", ephemeral=True)
                except discord.errors.InteractionResponded:
                    pass


bot = MyBot()

if TOKEN:
    bot.run(TOKEN)
else:
    logging.critical("DISCORD_BOT_TOKEN environment variable not set. Please check your .env file.")
