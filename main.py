import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import traceback
import asyncio
import logging

# pjsk_record_result モジュールから _create_song_data_map をインポート
# _create_song_data_map は PjskRecordResult クラスの外に定義されているため、モジュールから直接インポートします。
from cogs.pjsk_record_result import _create_song_data_map as pjsk_record_result_create_song_data_map

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

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
            logging.critical(f"{songs_file_path} が見つかりません。'data'フォルダにあることを確認してください。", exc_info=True)
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
                # load_extension に songs_data は渡さない
                await self.load_extension(extension)
                logging.info(f"Successfully loaded {extension}")
            except Exception as e:
                logging.error(f"Failed to load {extension}: {e}", exc_info=True)

        logging.info("Attempting to set cog references and song data.")
        try:
            # ProsekaGeneralCommands コグにデータを設定
            proseka_general_cog = self.get_cog("ProsekaGeneralCommands")
            if proseka_general_cog:
                proseka_general_cog.songs_data = self.proseka_songs_data
                proseka_general_cog.valid_difficulties = self.valid_difficulties_data
                logging.info("Set songs_data and valid_difficulties in ProsekaGeneralCommands.")
            else:
                logging.warning("ProsekaGeneralCommands cog not found after loading.")

            # ProsekaRankMatchCommands コグにデータを設定
            rankmatch_cog = self.get_cog("ProsekaRankMatchCommands")
            if rankmatch_cog:
                rankmatch_cog.songs_data = self.proseka_songs_data
                rankmatch_cog.valid_difficulties = self.valid_difficulties_data
                logging.info("Set songs_data and valid_difficulties in ProsekaRankMatchCommands.")
            else:
                logging.warning("ProsekaRankMatchCommands cog not found after loading.")
            
            # PjskRecordResult コグにデータを設定
            record_result_cog = self.get_cog("PjskRecordResult")
            if record_result_cog:
                record_result_cog.songs_data = self.proseka_songs_data
                # グローバル関数としてインポートした pjsk_record_result_create_song_data_map を直接呼び出す
                record_result_cog.SONG_DATA_MAP = pjsk_record_result_create_song_data_map(self.proseka_songs_data)
                logging.info("Set songs_data and updated SONG_DATA_MAP in PjskRecordResult cog.")
            else:
                logging.warning("PjskRecordResult cog not found after loading.")


            # AP/FCレートコグの参照設定
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
            # グローバルコマンドの同期
            global_synced = await self.tree.sync()
            logging.info(f"Synced {len(global_synced)} global commands.")

            # 特定ギルドへのコマンド同期 (サポートギルドIDを使用)
            support_guild = discord.Object(id=SUPPORT_GUILD_ID)
            guild_synced = await self.tree.sync(guild=support_guild)
            logging.info(f"Synced {len(guild_synced)} commands to support guild {SUPPORT_GUILD_ID}.")

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
        elif isinstance(error, app_commands.CommandNotFound):
            logging.warning(f"Command '{interaction.command.name}' not found. This might be due to Discord cache or recent sync issues.")
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(
                        "そのコマンドは見つかりませんでした。ボットのコマンドがDiscordに同期されるまでしばらくお待ちください。",
                        ephemeral=True
                    )
                except discord.errors.InteractionResponded:
                    pass
                except Exception as e:
                    logging.critical(f"Failed to send 'command not found' message: {e}", exc_info=True)
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


bot = MyBot()

if TOKEN:
    bot.run(TOKEN)
else:
    logging.critical("DISCORD_BOT_TOKEN environment variable not set. Please check your .env file.")
