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

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))
OWNER_ID = int(os.getenv('OWNER_ID'))

# 楽曲データファイルのパス
SONGS_FILE = 'data/songs.json'

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # メッセージ内容のインテントを有効にする
        intents.members = True # メンバー情報を取得するために必要

        super().__init__(
            command_prefix=commands.when_mentioned_or('!'), # プレフィックスコマンドも考慮する場合
            intents=intents,
            application_id=int(os.getenv('APPLICATION_ID')) if os.getenv('APPLICATION_ID') else None
        )
        self.initial_extensions = [
            'cogs.proseka_general',
            'cogs.proseka_rankmatch',
            'cogs.pjsk_ap_fc_rate',
            'cogs.pjsk_record_result'
        ]
        self.proseka_songs_data = [] # 楽曲データをボットインスタンスに保持
        self.is_bot_ready = False # ボットの準備状態を管理するフラグ

        # コグ参照のための属性を初期化
        self.proseka_general_cog = None
        self.proseka_rankmatch_cog = None
        self.pjsk_ap_fc_rate_cog = None

        logging.info("Bot instance created.")

    async def setup_hook(self):
        logging.info("Starting setup_hook...")
        
        # 楽曲データの読み込み
        logging.info(f"Attempting to load songs from {SONGS_FILE}...")
        try:
            with open(SONGS_FILE, 'r', encoding='utf-8') as f:
                self.proseka_songs_data = json.load(f)
            logging.info(f"Successfully loaded {len(self.proseka_songs_data)} songs.")
        except FileNotFoundError:
            logging.error(f"Songs data file not found: {SONGS_FILE}. Please ensure it exists.")
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from {SONGS_FILE}. Check file format.", exc_info=True)
        except Exception as e:
            logging.error(f"An unexpected error occurred while loading songs: {e}", exc_info=True)

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


        if self.proseka_general_cog:
            self.proseka_general_cog.songs_data = self.proseka_songs_data
            # ProsekaGeneralCommandsのvalid_difficultiesも更新（もしあれば）
            # self.proseka_general_cog.valid_difficulties = ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"]
            logging.info("Set songs_data and valid_difficulties in ProsekaGeneralCommands.")
        else:
            logging.warning("ProsekaGeneralCommands cog not found after loading.")

        if self.proseka_rankmatch_cog:
            self.proseka_rankmatch_cog.songs_data = self.proseka_songs_data
            logging.info("Set songs_data in ProsekaRankMatchCommands.")
        else:
            logging.warning("ProsekaRankMatchCommands cog not found after loading.")

        if self.pjsk_record_result_cog:
            # PjskRecordResult cogにsongs_dataを渡し、内部でSONG_DATA_MAPを再構築させる
            self.pjsk_record_result_cog.songs_data = self.proseka_songs_data
            self.pjsk_record_result_cog.SONG_DATA_MAP = _create_song_data_map(self.proseka_songs_data)
            logging.info("Set songs_data and updated SONG_DATA_MAP in PjskRecordResult cog.")
        else:
            logging.warning("PjskRecordResult cog not found after loading.")


        # 相互参照の設定 (AP/FCレートの自動更新のため)
        if self.proseka_general_cog and self.pjsk_ap_fc_rate_cog:
            self.proseka_general_cog.ap_fc_rate_cog = self.pjsk_ap_fc_rate_cog
            logging.info("Set ap_fc_rate_cog reference in ProsekaGeneralCommands.")
        if self.proseka_rankmatch_cog and self.pjsk_ap_fc_rate_cog:
            self.proseka_rankmatch_cog.ap_fc_rate_cog = self.pjsk_ap_fc_rate_cog
            logging.info("Set ap_fc_rate_cog reference in ProsekaRankMatchCommands.")
        
        if not self.proseka_rankmatch_cog or not self.pjsk_ap_fc_rate_cog:
            logging.warning("Could not get ProsekaRankMatchCommands or PjskApFcRateCommands cog for linking. Check cog names or load order.")


        # コマンドの同期
        logging.info("Attempting to sync commands...")
        try:
            # グローバルコマンドを同期
            synced = await self.tree.sync()
            logging.info(f"Synced {len(synced)} global commands.")

            # 特定のギルドコマンドを同期 (もしあれば)
            support_guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=support_guild)
            synced_guild_commands = await self.tree.sync(guild=support_guild)
            logging.info(f"Synced {len(synced_guild_commands)} commands to support guild {GUILD_ID}.")

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
            total_charts += sum(1 for diff in ["easy", "normal", "hard", "expert", "master", "append"] if diff in song and song[diff] is not None)
        
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


# _create_song_data_map 関数は pjsk_record_result.py に移動済みのため、ここでは定義しない
# ただし、main.py内でPjskRecordResultのSONG_DATA_MAPを更新するために参照する必要がある
# そのため、pjsk_record_result.py からこの関数をインポートするか、
# または pjsk_record_result.py のsetup_hookでSONG_DATA_MAPを初期化する形にする。
# 現状では、main.pyで呼び出されているため、pjsk_record_result.pyからインポートする形が望ましい。

# ここでは、pjsk_record_result.py にある _create_song_data_map を明示的にインポートする
# もし循環参照の問題が発生する場合は、この関数を main.py に移し、songs_data を引数として渡すなどの対応が必要
from cogs.pjsk_record_result import _create_song_data_map


def run_bot():
    bot = MyBot()
    if TOKEN:
        bot.run(TOKEN)
    else:
        logging.critical("DISCORD_BOT_TOKEN is not set. Please set it in Render's Environment settings or .env file.")

if __name__ == '__main__':
    run_bot()
