import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import traceback
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import json

# .envファイルから環境変数を読み込む
load_dotenv()

# ロギング設定
if not logging.root.handlers:
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')

# 環境変数からオーナーIDを読み込む
_owner_id_str = os.getenv('OWNER_ID')
if _owner_id_str is None:
    logging.critical("OWNER_ID environment variable is not set. Please set it in Render's Environment settings.")
    OWNER_ID = -1
else:
    try:
        OWNER_ID = int(_owner_id_str)
    except ValueError:
        logging.critical(f"OWNER_ID environment variable '{_owner_id_str}' is not a valid integer. Please check Render's Environment settings.")
        OWNER_ID = -1

# 環境変数からギルドIDを読み込む
_guild_id_str = os.getenv('GUILD_ID')
if _guild_id_str is None:
    logging.warning("GUILD_ID environment variable is not set. Some commands might not be registered correctly.")
    GUILD_ID = 0
else:
    try:
        GUILD_ID = int(_guild_id_str)
    except ValueError:
        logging.critical(f"GUILD_ID environment variable '{_guild_id_str}' is not a valid integer. Please check Render's Environment settings.")
        GUILD_ID = 0

# ランクマッチ結果を投稿するためのDiscordチャンネルID
_rankmatch_channel_id_str = os.getenv('RANKMATCH_RESULT_CHANNEL_ID')
if _rankmatch_channel_id_str is None:
    # RANKMATCH_RESULT_CHANNEL_IDに関する警告メッセージを削除済み
    RANKMATCH_RESULT_CHANNEL_ID = 0
else:
    try:
        RANKMATCH_RESULT_CHANNEL_ID = int(_rankmatch_channel_id_str)
    except ValueError:
        logging.critical(f"RANKMATCH_RESULT_CHANNEL_ID environment variable '{_rankmatch_channel_id_str}' is not a valid integer.")
        RANKMATCH_RESULT_CHANNEL_ID = 0

# SONGS_FILE を Python モジュールとして指定 (data/songs.py)
SONGS_FILE = "data.songs"

# グローバル変数としてJSTを設定
JST = timezone(timedelta(hours=9))

# 管理者モードのフラグ（初期値）
ADMIN_MODE = False

# ボットオーナーであるかをチェックする関数 (is_owner_global として使用)
def is_bot_owner_check(): # 名前を is_owner_global と区別するために変更
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == OWNER_ID:
            logging.info(f"Owner {interaction.user.name} (ID: {interaction.user.id}) bypassed admin mode check.")
            return True
        await interaction.response.send_message("このコマンドはボットの製作者のみが使用できます。", ephemeral=True)
        logging.warning(f"Non-owner {interaction.user.name} (ID: {interaction.user.id}) attempted to use owner-only command.")
        return False
    return app_commands.check(predicate)

# is_owner_global は StatusCommands cog にて参照される
# bot.is_admin_mode_active が StatusCommands から参照される
is_owner_global = is_bot_owner_check

# 非オーナーに対して管理者モードが有効な場合にコマンド実行をブロックする関数
def is_not_admin_mode_for_non_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == OWNER_ID:
            return True
        
        # MyBotインスタンスからADMIN_MODEの状態を取得
        if hasattr(interaction.client, 'is_admin_mode_active') and interaction.client.is_admin_mode_active:
            await interaction.response.send_message(
                "現在、ボットはメンテナンスのための**管理者モード**です。一時的にコマンドの使用が制限されています。",
                ephemeral=True
            )
            logging.info(f"Command blocked for non-owner {interaction.user.name} (ID: {interaction.user.id}) due to admin mode.")
            return False
        
        return True
    return app_commands.check(predicate)

# 楽曲データをPythonファイルから読み込む関数
async def load_songs_data():
    try:
        songs_module = __import__(SONGS_FILE, fromlist=['proseka_songs', 'VALID_DIFFICULTIES'])
        songs = getattr(songs_module, 'proseka_songs', [])
        global VALID_DIFFICULTIES_FOR_COUNT
        VALID_DIFFICULTIES_FOR_COUNT = getattr(songs_module, 'VALID_DIFFICULTIES', ['EASY', 'NORMAL', 'HARD', 'EXPERT', 'MASTER', 'APPEND'])
        logging.info(f"Loaded {len(songs)} songs from {SONGS_FILE}.")
        return songs
    except ImportError as e:
        logging.critical(f"Error importing songs data from {SONGS_FILE}. Please ensure data/songs.py exists and contains a 'proseka_songs' variable: {e}")
        return []
    except AttributeError:
        logging.critical(f"'{SONGS_FILE}' module does not contain 'proseka_songs' or 'VALID_DIFFICULTIES' variable. Please define your song data in 'data/songs.py' as 'proseka_songs = [...]' and 'VALID_DIFFICULTIES = [...]'.")
        VALID_DIFFICULTIES_FOR_COUNT = ['EASY', 'NORMAL', 'HARD', 'EXPERT', 'MASTER', 'APPEND'] # フォールバック
        return []
    except Exception as e:
        logging.critical(f"Unexpected error loading songs data from {SONGS_FILE}: {e}", exc_info=True)
        return []

# _create_song_data_map は変更なし
def _create_song_data_map(songs_list):
    """songs.pyのリストデータをタイトルをキーとする辞書に変換します。"""
    song_map = {}
    for song in songs_list:
        title = song.get("title")
        if title:
            song_map[title.lower()] = song
    logging.info(f"Created song data map with {len(song_map)} entries.")
    return song_map


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True 
        intents.members = True          
        intents.guilds = True           
        
        super().__init__(command_prefix='!', intents=intents)
        
        self.owner_id = OWNER_ID
        self.GUILD_ID = GUILD_ID
        self.RANKMATCH_RESULT_CHANNEL_ID = RANKMATCH_RESULT_CHANNEL_ID
        self.is_bot_ready = False 
        self.is_admin_mode_active = ADMIN_MODE # 新しい管理者モードフラグ

        self.proseka_songs_data = [] 
        self.SONG_DATA_MAP = {} 

        logging.info("Bot initialized.")

    async def setup_hook(self):
        logging.info("Running setup_hook...")
        
        self.proseka_songs_data = await load_songs_data()
        self.SONG_DATA_MAP = _create_song_data_map(self.proseka_songs_data) 

        cogs_to_load = [
            "cogs.proseka_general",
            "cogs.help_command",
            "cogs.proseka_rankmatch",
            "cogs.pjsk_record_result", 
            "cogs.premium_features",
            "cogs.debug_commands",
            "cogs.pjsk_ap_fc_rate",
            "cogs.status_commands", # ★追加: StatusCommands コグをロード★
        ]
        
        for cog_name in cogs_to_load:
            try:
                await self.load_extension(cog_name) 
                logging.info(f"Successfully loaded {cog_name}.")
            except Exception as e:
                logging.error(f"Failed to load cog {cog_name}: {e}", exc_info=True)
        
        # コグ間の参照設定（全てのコグがロードされた後に行う）
        general_cog = self.get_cog('ProsekaGeneralCommands')
        record_cog = self.get_cog('PjskRecordResult')
        rankmatch_cog = self.get_cog('ProsekaRankMatchCommands')
        premium_cog = self.get_cog('PremiumManagerCog')
        ap_fc_rate_cog = self.get_cog('PjskApFcRateCommands')
        status_cog = self.get_cog('StatusCommands') # StatusCommands コグのインスタンスを取得

        # 各コグが存在することを確認してから参照を設定
        if general_cog and ap_fc_rate_cog:
            general_cog.ap_fc_rate_cog = ap_fc_rate_cog
            logging.info("Set general_cog.ap_fc_rate_cog.")
        
        if rankmatch_cog and ap_fc_rate_cog:
            rankmatch_cog.ap_fc_rate_cog = ap_fc_rate_cog
            logging.info("Set rankmatch_cog.ap_fc_rate_cog.")

        if ap_fc_rate_cog and record_cog:
            record_cog.ap_fc_rate_cog = ap_fc_rate_cog
            logging.info("Set record_cog.ap_fc_rate_cog.")
        
        # すべての必須コグが存在する場合のみクロス参照設定完了と判断
        if general_cog and record_cog and rankmatch_cog and premium_cog and status_cog: # status_cogも必須に追加
             logging.info("All essential cross-cog references set.")
        else:
            logging.warning("Some cogs or their references are missing. Cross-cog functionality might be limited.")


        if self.GUILD_ID != 0:
            guild_obj = discord.Object(id=self.GUILD_ID)
            self.tree.copy_global_to(guild=guild_obj)
            synced = await self.tree.sync(guild=guild_obj)
            logging.info(f"Synced {len(synced)} commands to guild {self.GUILD_ID}.")
        else:
            synced = await self.tree.sync()
            logging.info(f"Synced {len(synced)} global commands.")

        if premium_cog and hasattr(premium_cog, 'patreon_sync_task') and not premium_cog.patreon_sync_task.is_running():
            premium_cog.patreon_sync_task.start()
            logging.info("Patreon sync task started.")
        else:
            logging.warning("PremiumManagerCog not found or Patreon sync task already running. Skipping task start.")

        self.is_bot_ready = True 
        logging.info("setup_hook completed. Bot is ready!")

    async def on_ready(self):
        logging.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logging.info(f'Bot is ready: {self.is_bot_ready}')
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print(f'Bot is ready: {self.user.id}')
        
        owner = self.get_user(self.owner_id)
        
        # 譜面数を正しく数えるロジック
        total_sheet_music_count = 0
        if 'VALID_DIFFICULTIES_FOR_COUNT' in globals():
            for song_data in self.proseka_songs_data:
                for difficulty_key in [d.lower() for d in VALID_DIFFICULTIES_FOR_COUNT]:
                    if song_data.get(difficulty_key) is not None:
                        total_sheet_music_count += 1
        else:
            logging.warning("VALID_DIFFICULTIES_FOR_COUNT not found. Cannot accurately count total sheet music.")
            for song_data in self.proseka_songs_data:
                if song_data.get('easy') is not None: total_sheet_music_count += 1
                if song_data.get('normal') is not None: total_sheet_music_count += 1
                if song_data.get('hard') is not None: total_sheet_music_count += 1
                if song_data.get('expert') is not None: total_sheet_music_count += 1
                if song_data.get('master') is not None: total_sheet_music_count += 1
                if song_data.get('append') is not None: total_sheet_music_count += 1


        # ボットのカスタムステータスを設定
        activity_name = f"{len(self.proseka_songs_data)}曲 / {total_sheet_music_count}譜面が登録済み"
        try:
            await self.change_presence(activity=discord.Game(name=activity_name))
            logging.info(f"Bot activity set to: '{activity_name}'.")
        except Exception as e:
            logging.error(f"Failed to set bot activity: {e}", exc_info=True)


        # 管理者モードが有効な場合のみオーナーにDMを送信 (StatusCommands cogがこのフラグを制御します)
        if owner and self.is_admin_mode_active: 
            try:
                await owner.send("ボットが起動しました。現在、**管理者モード**が有効になっています。")
                logging.info(f"Sent admin mode notification to owner {owner.name}.")
            except discord.Forbidden:
                logging.warning(f"Could not send DM to owner {owner.name}. DMs disabled. Skipping admin mode message.")
            except Exception as e:
                logging.error(f"Error sending admin mode DM to owner: {e}", exc_info=True)
        elif not owner and self.is_admin_mode_active: # オーナーが見つからない場合もログに通知
            logging.warning("Owner not found or could not resolve owner. Skipping admin mode DM notification.")


    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            logging.warning(f"Command not found: {ctx.message.content} by {ctx.author.name}")
        elif isinstance(error, commands.MissingRequiredArgument):
            logging.warning(f"Missing arguments for {ctx.command}: {error} by {ctx.author.name}")
            await ctx.send(f"コマンドの引数が不足しています: {error}")
        elif isinstance(error, commands.NotOwner):
            logging.warning(f"Non-owner {ctx.author.name} attempted owner-only command {ctx.command.name}.")
            await ctx.send("このコマンドはボットの製作者のみが使用できます。")
        elif isinstance(error, commands.CommandInvokeError):
            logging.error(f"Error invoking command {ctx.command}: {error.original}", exc_info=True)
            await ctx.send(f"コマンドの実行中にエラーが発生しました: `{error.original}`")
            owner = self.get_user(self.owner_id)
            if owner:
                error_msg = f"コマンドエラー: `{ctx.command.name}`\n" \
                            f"実行者: {ctx.author.name} (ID: {ctx.author.id})\n" \
                            f"ギルド: {ctx.guild.name} (ID: {ctx.guild.id}) if ctx.guild else 'DM'\n" \
                            f"エラー: ```py\n{type(error.original).__name__}: {error.original}\n" \
                            f"{''.join(traceback.format_exception(type(error.original), error.original, error.original.__traceback__))[:1500]}...```"
                try:
                    await owner.send(error_msg)
                except discord.Forbidden:
                    logging.warning(f"Could not send error DM to owner {owner.name}. DMs disabled.")
        else:
            logging.error(f"Unhandled command error: {error}", exc_info=True)
            await ctx.send(f"予期せぬエラーが発生しました: `{error}`")

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            remaining = error.retry_after
            await interaction.response.send_message(f"このコマンドはクールダウン中です。あと {remaining:.1f} 秒待ってください。", ephemeral=True)
            logging.info(f"CommandOnCooldown for {interaction.command.name} by {interaction.user.name}. Remaining: {remaining:.1f}s")
        elif isinstance(error, app_commands.MissingPermissions):
            missing_perms = ", ".join(error.missing_permissions)
            await interaction.response.send_message(f"このコマンドを実行するには、以下の権限が必要です: `{missing_perms}`", ephemeral=True)
            logging.warning(f"MissingPermissions for {interaction.command.name} by {interaction.user.name}: {missing_perms}")
        elif isinstance(error, app_commands.CheckFailure):
            logging.warning(f"AppCommand CheckFailure for {interaction.command.name} by {interaction.user.name}. Error: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "このコマンドは現在利用できません、またはあなたには実行する権限がありません。",
                    ephemeral=True
                )
        elif isinstance(error, app_commands.CommandInvokeError):
            logging.error(f"Error invoking app command {interaction.command.name}: {error.original}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(f"コマンドの実行中にエラーが発生しました: `{error.original}`", ephemeral=True)
            owner = self.get_user(self.owner_id)
            if owner:
                error_msg = f"スラッシュコマンドエラー: `{interaction.command.name}`\n" \
                            f"実行者: {interaction.user.name} (ID: {interaction.user.id})\n" \
                            f"ギルド: {interaction.guild.name} (ID: {interaction.guild.id}) if interaction.guild else 'DM'\n" \
                            f"エラー: ```py\n{type(error.original).__name__}: {error.original}\n" \
                            f"{''.join(traceback.format_exception(type(error.original), error.original, error.original.__traceback__))[:1500]}...```"
                try:
                    await owner.send(error_msg)
                except discord.Forbidden:
                    logging.warning(f"Could not send error DM to owner {owner.name}. DMs disabled.")
        else:
            logging.error(f"Unhandled app command error: {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(f"予期せぬエラーが発生しました: `{error}`", ephemeral=True)

    # set_status コマンドは cogs/status_commands.py に移動しました
    # debug_status コマンドは cogs/debug_commands.py に残ります (もし存在する場合)
    # または必要に応じてこの main.py にオーナー専用コマンドとして残すこともできます

if __name__ == "__main__":
    bot = MyBot()
    DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if DISCORD_BOT_TOKEN is None:
        logging.critical("DISCORD_BOT_TOKEN environment variable is not set. Please set it to run the bot.")
    else:
        try:
            bot.run(DISCORD_BOT_TOKEN)
        except discord.LoginFailure:
            logging.critical("Failed to login to Discord. Invalid token provided.")
        except Exception as e:
            logging.critical(f"An unexpected error occurred during bot execution: {e}", exc_info=True)
