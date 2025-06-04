import discord
from discord.ext import commands
import os
import json
import asyncio
import traceback
import logging

# ロギング設定
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# 環境変数の読み込み
from dotenv import load_dotenv
load_dotenv()

# 環境変数を安全に読み込む
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# GUILD_ID はサポートギルドIDとして使用されるため、必須。設定されていない場合はエラーログを出力し、デフォルト値を使用。
_guild_id_str = os.getenv('GUILD_ID')
if _guild_id_str: # Noneや空文字列でないことを確認
    try:
        GUILD_ID = int(_guild_id_str)
    except ValueError:
        logging.critical(f"GUILD_ID environment variable '{_guild_id_str}' is not a valid integer. Using default 0.", exc_info=True)
        GUILD_ID = 0
else:
    logging.critical("GUILD_ID environment variable is not set. Using default 0. Please set it in Render's Environment settings or .env file.")
    GUILD_ID = 0

# OWNER_ID はボットのオーナーIDとして使用されるため、必須。設定されていない場合はエラーログを出力し、デフォルト値を使用。
_owner_id_str = os.getenv('OWNER_ID')
if _owner_id_str: # Noneや空文字列でないことを確認
    try:
        OWNER_ID = int(_owner_id_str)
    except ValueError:
        logging.critical(f"OWNER_ID environment variable '{_owner_id_str}' is not a valid integer. Using default 0.", exc_info=True)
        OWNER_ID = 0
else:
    logging.critical("OWNER_ID environment variable is not set. Using default 0. Please set it in Render's Environment settings or .env file.")
    OWNER_ID = 0

# APPLICATION_ID はボットのアプリケーションIDとして使用されるため、必須。設定されていない場合はエラーログを出力し、デフォルト値を使用。
_application_id_str = os.getenv('APPLICATION_ID')
if _application_id_str: # Noneや空文字列でないことを確認
    try:
        APPLICATION_ID = int(_application_id_str)
    except ValueError:
        logging.critical(f"APPLICATION_ID environment variable '{_application_id_str}' is not a valid integer. Using default 0.", exc_info=True)
        APPLICATION_ID = 0
else:
    logging.critical("APPLICATION_ID environment variable is not set. Using default 0. Please set it in Render's Environment settings or .env file.")
    APPLICATION_ID = 0


# SONGS_FILE を songs.py に戻す
SONGS_FILE = 'data/songs.py'

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # メッセージ内容のインテントを有効にする
        intents.members = True # メンバー情報を取得するために必要

        super().__init__(
            command_prefix=commands.when_mentioned_or('!'), # プレフィックスコマンドも考慮する場合
            intents=intents,
            application_id=APPLICATION_ID # 安全に読み込んだ APPLICATION_ID を使用
        )
        # initial_extensions リストを整理し、重複がないことを確認
        self.initial_extensions = [
            'cogs.pjsk_ap_fc_rate',      # AP/FCレートコグ
            'cogs.proseka_general',      # 汎用コマンドコグ
            'cogs.help_command',         # 追加: ヘルプコマンドコグ
            'cogs.proseka_rankmatch',    # ランクマッチ選曲コグ
            'cogs.pjsk_rankmatch_result',# ★修正: ランクマッチリザルトコグのコメントを解除
            'cogs.pjsk_record_result'    # 精度記録コグ
        ]
        self.proseka_songs_data = [] # 楽曲データをボットインスタンスに保持
        self.valid_difficulties_data = ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"] # 難易度データをここに保持
        self.is_bot_ready = False # ボットの準備状態を管理するフラグ

        # コグ参照のための属性を初期化
        self.proseka_general_cog = None
        self.proseka_rankmatch_cog = None
        self.pjsk_ap_fc_rate_cog = None
        self.pjsk_record_result_cog = None
        self.help_command_cog = None
        self.pjsk_rankmatch_result_cog = None # ★追加: pjsk_rankmatch_resultコグの参照を追加

        logging.info("Bot instance created.")

    # songs.py を読み込むための非同期関数を再導入
    async def _load_songs_data_async(self):
        """data/songs.py から楽曲データを非同期で読み込む"""
        logging.info(f"Attempting to load songs data from {SONGS_FILE} asynchronously.")
        try:
            loop = asyncio.get_running_loop()
            with open(SONGS_FILE, 'r', encoding='utf-8') as f:
                file_content = await loop.run_in_executor(None, f.read)
            
            _globals = {}
            # songs.py の内容を実行し、proseka_songs と VALID_DIFFICULTIES を取得
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
        
        # songs.py から楽曲データを読み込む
        await self._load_songs_data_async()

        # コグのロード
        for extension in self.initial_extensions:
            try:
                logging.info(f"Loading extension: {extension}...")
                await self.load_extension(extension)
                logging.info(f"Successfully loaded {extension}.")
            except Exception as e:
                logging.error(f"Failed to load extension {extension}.", exc_info=True)

        # コグがロードされた後に参照を設定
        logging.info("Attempting to set cog references and song data.")
        self.proseka_general_cog = self.get_cog("ProsekaGeneralCommands")
        self.proseka_rankmatch_cog = self.get_cog("ProsekaRankMatchCommands")
        self.pjsk_ap_fc_rate_cog = self.get_cog("PjskApFcRateCommands")
        self.pjsk_record_result_cog = self.get_cog("PjskRecordResult")
        self.help_command_cog = self.get_cog("HelpCommand")
        self.pjsk_rankmatch_result_cog = self.get_cog("PjskRankMatchResult") # ★追加: pjsk_rankmatch_resultコグの参照を取得


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
            # PjskRecordResult cogにsongs_dataを渡し、内部でSONG_DATA_MAPを再構築させる
            # _create_song_data_map は pjsk_record_result.py からインポート済み
            self.pjsk_record_result_cog.songs_data = self.proseka_songs_data
            self.pjsk_record_result_cog.SONG_DATA_MAP = _create_song_data_map(self.proseka_songs_data)
            logging.info("Set songs_data and updated SONG_DATA_MAP in PjskRecordResult cog.")
        else:
            logging.warning("PjskRecordResult cog not found after loading.")

        # ★追加: pjsk_rankmatch_result_cog が存在する場合に songs_data を設定
        if self.pjsk_rankmatch_result_cog:
            self.pjsk_rankmatch_result_cog.songs_data = self.proseka_songs_data
            logging.info("Set songs_data in PjskRankMatchResult cog.")
        else:
            logging.warning("PjskRankMatchResult cog not found after loading.")


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
        
        # コマンドの同期
        logging.info("Attempting to sync commands...")
        try:
            # グローバルコマンドを同期
            # これにより、@app_commands.guilds() デコレータがないコマンドがすべて同期される
            synced_global = await self.tree.sync()
            logging.info(f"Synced {len(synced_global)} global commands.")

            # 特定のギルドコマンドを同期 (もし GUILD_ID が有効な場合のみ)
            # これにより、@app_commands.guilds(discord.Object(id=GUILD_ID)) でマークされたコマンドのみが同期される
            if GUILD_ID != 0: # GUILD_ID がデフォルト値でないことを確認
                support_guild = discord.Object(id=GUILD_ID)
                synced_guild_commands = await self.tree.sync(guild=support_guild)
                logging.info(f"Synced {len(synced_guild_commands)} commands to support guild {GUILD_ID}.")
            else:
                logging.warning("GUILD_ID is not set or invalid (0). Skipping guild command sync.")

        except Exception as e:
            logging.error(f"Failed to sync commands: {e}", exc_info=True)

        logging.info("setup_hook completed.")


    async def on_ready(self):
        logging.info(f"Logged in as {self.user.name} (ID: {self.user.id})")
        logging.info("------")
        
        self.is_bot_ready = True # ボットが準備完了したことを示すフラグを設定
        
        # 楽曲数と譜面数を計算し、ステータスに設定
        total_songs = len(self.proseka_songs_data)
        total_charts = 0
        for song in self.proseka_songs_data:
            # "easy", "normal", "hard", "expert", "master", "append" のキーを持つか確認
            # 存在すれば譜面としてカウント
            total_charts += sum(1 for diff in self.valid_difficulties_data if diff.lower() in song and song[diff.lower()] is not None)
        
        activity_message = f"{total_songs}曲/{total_charts}譜面が登録済み"
        await self.change_presence(activity=discord.Game(name=activity_message))
        logging.info(f"Status set to: {activity_message}")
        logging.info("Bot is fully ready and accepting commands.")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return # コマンドが存在しない場合は何もしない
        logging.error(f"An error occurred in command {ctx.command}: {error}", exc_info=True)
        await ctx.send(f"エラーが発生しました: {error}")

    async def on_app_command_error(self, interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
        # 既にレスポンス済みの場合、ログのみで終了
        if interaction.response.is_done():
            logging.error(f"App command error (interaction already responded): {error}", exc_info=True)
            return

        # NotFoundエラー（Unknown interaction）の具体的なハンドリング
        if isinstance(error, discord.errors.NotFound) and error.code == 10062:
            logging.error(f"Unknown interaction (404 Not Found) for command '{interaction.command.name}' by user {interaction.user.id}. Interaction might have timed out before defer/response.", exc_info=True)
            try:
                # ephemeral=True で試みるが、それでも失敗する可能性が高い
                await interaction.followup.send("申し訳ありません、操作がタイムアウトしたか、無効になりました。もう一度お試しください。", ephemeral=True)
            except Exception as e:
                logging.error(f"Failed to send follow-up for Unknown interaction error: {e}", exc_info=True)
            return
            
        # その他のCheckFailure系エラー
        if isinstance(error, discord.app_commands.CheckFailure):
            if isinstance(error, discord.app_commands.MissingRole):
                logging.warning(f"Missing role for user {interaction.user.id} on command '{interaction.command.name}'. Role ID: {error.missing_role}")
                await interaction.response.send_message(f"このコマンドを実行するには、必要なロールがありません。", ephemeral=True)
            elif isinstance(error, discord.app_commands.NoPrivateMessage):
                logging.warning(f"Private message usage for command '{interaction.command.name}' by user {interaction.user.id}.")
                await interaction.response.send_message("このコマンドはDMでは実行できません。", ephemeral=True)
            elif isinstance(error, discord.app_commands.CommandOnCooldown):
                logging.warning(f"Command '{interaction.command.name}' on cooldown for user {interaction.user.id}. Retry after {error.retry_after:.2f}s.")
                await interaction.response.send_message(f"このコマンドはクールダウン中です。{error.retry_after:.2f}秒後に再試行してください。", ephemeral=True)
            elif isinstance(error, discord.app_commands.MissingPermissions):
                logging.warning(f"Missing permissions for user {interaction.user.id} on command '{interaction.command.name}'. Permissions: {error.missing_permissions}")
                await interaction.response.send_message(f"このコマンドを実行するための権限がありません。", ephemeral=True)
            else:
                logging.warning(f"Generic CheckFailure for command '{interaction.command.name}' by user {interaction.user.id}: {error}")
                await interaction.response.send_message(f"このコマンドを実行できませんでした（権限エラーなど）。", ephemeral=True)
            return
        
        # その他の一般的なエラー
        logging.error(f"An unexpected error occurred during app command '{interaction.command.name}' by {interaction.user.id}: {error}", exc_info=True)
        try:
            # 既に defer 済みの場合、followup.send を使う
            if interaction.is_acknowledged():
                await interaction.followup.send(f"コマンドの実行中に予期せぬエラーが発生しました: `{error}`", ephemeral=True)
            else:
                await interaction.response.send_message(f"コマンドの実行中に予期せぬエラーが発生しました: `{error}`", ephemeral=True)
        except discord.errors.InteractionResponded:
            # すでにレスポンス済みのため、無視
            pass
        except Exception as e:
            logging.error(f"Failed to send error message to user: {e}", exc_info=True)


# _create_song_data_map 関数は pjsk_record_result.py にあるため、ここからインポート
# main.py の setup_hook で使用するために必要
from cogs.pjsk_record_result import _create_song_data_map


def run_bot():
    bot = MyBot()
    # botインスタンスにGUILD_IDとAPPLICATION_IDを直接設定
    # これはhelp_commandコグでbot.GUILD_IDを参照するために必要
    bot.GUILD_ID = GUILD_ID
    bot.APPLICATION_ID = APPLICATION_ID

    if TOKEN:
        bot.run(TOKEN)
    else:
        logging.critical("DISCORD_BOT_TOKEN is not set. Please set it in Render's Environment settings or .env file.")

if __name__ == '__main__':
    run_bot()
