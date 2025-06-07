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
    logging.warning("RANKMATCH_RESULT_CHANNEL_ID environment variable is not set. Rankmatch results will not be posted to a dedicated channel.")
    RANKMATCH_RESULT_CHANNEL_ID = 0
else:
    try:
        RANKMATCH_RESULT_CHANNEL_ID = int(_rankmatch_channel_id_str)
    except ValueError:
        logging.critical(f"RANKMATCH_RESULT_CHANNEL_ID environment variable '{_rankmatch_channel_id_str}' is not a valid integer.")
        RANKMATCH_RESULT_CHANNEL_ID = 0

# ★修正: SONGS_FILE を Python モジュールとして指定★
SONGS_FILE = "data.songs" # data/songs.py をモジュールとしてインポート

# グローバル変数としてJSTを設定
JST = timezone(timedelta(hours=9))

# 管理者モードのフラグ（初期値）
ADMIN_MODE = False

# ボットオーナーであるかをチェックする関数
def is_bot_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == OWNER_ID:
            logging.info(f"Owner {interaction.user.name} (ID: {interaction.user.id}) bypassed admin mode check.")
            return True
        await interaction.response.send_message("このコマンドはボットの製作者のみが使用できます。", ephemeral=True)
        logging.warning(f"Non-owner {interaction.user.name} (ID: {interaction.user.id}) attempted to use owner-only command.")
        return False
    return app_commands.check(predicate)

# 非オーナーに対して管理者モードが有効な場合にコマンド実行をブロックする関数
def is_not_admin_mode_for_non_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == OWNER_ID:
            return True
        
        if ADMIN_MODE:
            await interaction.response.send_message(
                "現在、ボットはメンテナンスのための**管理者モード**です。一時的にコマンドの使用が制限されています。",
                ephemeral=True
            )
            logging.info(f"Command blocked for non-owner {interaction.user.name} (ID: {interaction.user.id}) due to admin mode.")
            return False
        
        return True
    return app_commands.check(predicate)

# ★修正: 楽曲データをPythonファイルから読み込む関数★
async def load_songs_data():
    try:
        # SONGS_FILE (data.songs) をモジュールとしてインポート
        # __import__ を使用すると、動的にモジュールをインポートできる
        # fromlist=['SONGS'] は SONGS という名前のオブジェクトをインポートすることを示す
        songs_module = __import__(SONGS_FILE, fromlist=['SONGS'])
        songs = getattr(songs_module, 'SONGS', []) # SONGS 変数を取得。なければ空リスト
        logging.info(f"Loaded {len(songs)} songs from {SONGS_FILE}.")
        return songs
    except ImportError as e:
        logging.critical(f"Error importing songs data from {SONGS_FILE}. Please ensure data/songs.py exists and contains a 'SONGS' variable: {e}")
        return []
    except AttributeError:
        logging.critical(f"'{SONGS_FILE}' module does not contain a 'SONGS' variable. Please define your song data in 'data/songs.py' as 'SONGS = [...]'.")
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
            # "cogs.ap_fc_rate", # ファイル未提供のため、引き続きコメントアウト
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
        ap_fc_rate_cog = self.get_cog('ApFcRate') # コメントアウトされていればNoneになる

        # 各コグが存在することを確認してから参照を設定
        if general_cog and ap_fc_rate_cog:
            general_cog.ap_fc_rate_cog = ap_fc_rate_cog
            logging.info("Set general_cog.ap_fc_rate_cog.")
        
        if rankmatch_cog and ap_fc_rate_cog:
            rankmatch_cog.ap_fc_rate_cog = ap_fc_rate_cog
            logging.info("Set rankmatch_cog.ap_fc_rate_cog.")

        if ap_fc_rate_cog and record_cog:
            ap_fc_rate_cog.record_cog = record_cog
            logging.info("Set ap_fc_rate_cog.record_cog.")
        
        # すべてのコグが存在する場合のみクロス参照設定完了と判断
        if general_cog and record_cog and rankmatch_cog and premium_cog: # ap_fc_rate_cog はオプションのため除外
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

        if premium_cog and not premium_cog.patreon_sync_task.is_running():
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
        if owner and ADMIN_MODE: 
            try:
                await owner.send("ボットが起動しました。現在、**管理者モード**が有効になっています。")
                logging.info(f"Sent admin mode notification to owner {owner.name}.")
            except discord.Forbidden:
                logging.warning(f"Could not send DM to owner {owner.name}. DMs disabled.")
            except Exception as e:
                logging.error(f"Error sending DM to owner: {e}", exc_info=True)

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

    @app_commands.command(name="set_status", description="ボットのステータスを設定し、管理者モードを切り替えます (オーナー限定)。")
    @app_commands.describe(
        status="ボットのステータス (online, idle, dnd, invisible)",
        activity_type="アクティビティタイプ (playing, streaming, listening, watching)",
        activity_name="アクティビティ名",
        bot_mode="ボットの動作モード (normal, admin)"
    )
    @is_bot_owner()
    async def set_status(self, interaction: discord.Interaction, 
                         status: str = None, 
                         activity_type: str = None, 
                         activity_name: str = None,
                         bot_mode: str = None):
        logging.info(f"Command '/set_status' invoked by {interaction.user.name} (ID: {interaction.user.id}).")
        
        global ADMIN_MODE 

        await interaction.response.defer(ephemeral=True)

        if status:
            _status_map = {
                "online": discord.Status.online,
                "idle": discord.Status.idle,
                "dnd": discord.Status.dnd,
                "invisible": discord.Status.invisible
            }
            new_status = _status_map.get(status.lower())
            if new_status:
                await self.change_presence(status=new_status)
                logging.info(f"Bot status changed to {status}.")
            else:
                await interaction.followup.send("無効なステータスです。`online`, `idle`, `dnd`, `invisible` から選択してください。", ephemeral=True)
                return

        new_activity = None
        if activity_type and activity_name:
            _activity_type_map = {
                "playing": discord.ActivityType.playing,
                "streaming": discord.ActivityType.streaming,
                "listening": discord.ActivityType.listening,
                "watching": discord.ActivityType.watching
            }
            _type = _activity_type_map.get(activity_type.lower())
            if _type:
                new_activity = discord.Activity(type=_type, name=activity_name)
                await self.change_presence(activity=new_activity)
                logging.info(f"Bot activity set to {activity_type}: {activity_name}.")
            else:
                await interaction.followup.send("無効なアクティビティタイプです。`playing`, `streaming`, `listening`, `watching` から選択してください。", ephemeral=True)
                return

        if bot_mode:
            if bot_mode.lower() == "admin":
                ADMIN_MODE = True 
                logging.warning("Bot entered ADMIN MODE.")
                await interaction.followup.send("ボットは**管理者モード**になりました。オーナー以外のユーザーからのほとんどのコマンドはブロックされます。", ephemeral=True)
            elif bot_mode.lower() == "normal":
                ADMIN_MODE = False 
                logging.info("Bot entered NORMAL MODE.")
                await interaction.followup.send("ボットは**通常モード**になりました。", ephemeral=True)
            else:
                await interaction.followup.send("無効なボットモードです。`normal` または `admin` を選択してください。", ephemeral=True)
                return

        if not status and not activity_type and not activity_name and not bot_mode:
            await interaction.followup.send("ステータス、アクティビティ、またはボットモードのいずれかを指定してください。", ephemeral=True)
        else:
            current_status = status if status else self.status.name
            current_activity = f"{activity_type}: {activity_name}" if activity_type and activity_name else "なし"
            current_mode = "管理者モード" if ADMIN_MODE else "通常モード" 
            
            await interaction.followup.send(
                f"ボットの設定を更新しました。\n"
                f"現在のステータス: `{current_status}`\n"
                f"現在のアクティビティ: `{current_activity}`\n"
                f"現在のボットモード: `{current_mode}`",
                ephemeral=True
            )

    @app_commands.command(name="debug_status", description="ボットの現在の管理者モード状態とオーナーIDを表示します (オーナー限定)。")
    @is_bot_owner()
    async def debug_status(self, interaction: discord.Interaction):
        logging.info(f"Command '/debug_status' invoked by {interaction.user.name} (ID: {interaction.user.id}).")
        
        embed = discord.Embed(
            title="ボットデバッグ情報",
            color=discord.Color.blue()
        )
        embed.add_field(name="オーナーID", value=f"`{self.owner_id}`", inline=False)
        embed.add_field(name="GUILD_ID", value=f"`{self.GUILD_ID}`", inline=False)
        embed.add_field(name="RANKMATCH_RESULT_CHANNEL_ID", value=f"`{self.RANKMATCH_RESULT_CHANNEL_ID}`", inline=False)
        embed.add_field(name="管理者モード", value=f"`{'有効' if ADMIN_MODE else '無効'}`", inline=False) 
        embed.add_field(name="ボット準備完了", value=f"`{'はい' if self.is_bot_ready else 'いいえ'}`", inline=False)
        
        loaded_cogs = ", ".join([cog_name for cog_name in self.cogs]) if self.cogs else "なし"
        embed.add_field(name="ロード済みのコグ", value=loaded_cogs, inline=False)

        global_commands = self.tree.get_commands(guild=None)
        guild_commands = self.tree.get_commands(guild=discord.Object(id=self.GUILD_ID)) if self.GUILD_ID != 0 else []
        embed.add_field(name="認識しているグローバルコマンド数", value=f"`{len(global_commands)}`", inline=True)
        embed.add_field(name=f"認識しているギルド({self.GUILD_ID})コマンド数", value=f"`{len(guild_commands)}`", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logging.info(f"Debug status sent to {interaction.user.name}.")

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

