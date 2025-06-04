import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import json # ★追加: JSONファイルを扱うために必要

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# OWNER_IDの読み込みとint()変換の堅牢化
_owner_id_str = os.getenv('OWNER_ID')
if _owner_id_str is None:
    print("CRITICAL ERROR: OWNER_ID environment variable is not set. Bot owner commands may not function.")
    OWNER_ID = None # Noneのままにして、owner_id=NoneでBotを初期化
else:
    try:
        OWNER_ID = int(_owner_id_str)
    except ValueError:
        print(f"CRITICAL ERROR: OWNER_ID environment variable '{_owner_id_str}' is not a valid integer. Bot owner commands may not function.")
        OWNER_ID = None

# SUPPORT_GUILD_IDは環境変数から読み込むことを推奨しますが、ここではハードコードされた値を使用します
SUPPORT_GUILD_ID = 1376551581423767582

# ★変更: data/songs.json からデータを読み込む
proseka_songs = []
VALID_DIFFICULTIES = ["EASY", "NORMAL", "HARD", "EXPERT", "MASTER", "APPEND"] # デフォルト値

try:
    with open('data/songs.json', 'r', encoding='utf-8') as f:
        loaded_data = json.load(f)
    
    # songs.jsonが直接リストの場合と、{"proseka_songs": [...], "VALID_DIFFICULTIES": [...]} のオブジェクトの場合に対応
    if isinstance(loaded_data, dict):
        proseka_songs = loaded_data.get('proseka_songs', [])
        VALID_DIFFICULTIES = loaded_data.get('VALID_DIFFICULTIES', VALID_DIFFICULTIES) # デフォルト値とマージ
    elif isinstance(loaded_data, list):
        proseka_songs = loaded_data
        # VALID_DIFFICULTIESは既にデフォルト値が設定されているので、ここでは変更しない
    else:
        print(f"ERROR: Unexpected data format in data/songs.json. Expected dict or list. Type: {type(loaded_data)}. Using empty song list.")

    print("DEBUG: Loaded songs data from data/songs.json in main.py.")
except FileNotFoundError:
    print("CRITICAL ERROR: data/songs.json not found in main.py. Ensure it's in the 'data' folder. Using empty song list.")
except json.JSONDecodeError as e:
    print(f"CRITICAL ERROR: Error decoding JSON from data/songs.json in main.py: {e}. Check JSON format. Using empty song list.")
    traceback.print_exc()
except Exception as e:
    print(f"CRITICAL ERROR: Unexpected error loading songs data in main.py: {e}. Using empty song list.")
    traceback.print_exc()


class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.presences = True

        super().__init__(
            command_prefix=commands.when_mentioned_or("!"),
            intents=intents,
            owner_id=OWNER_ID # OWNER_IDがNoneの場合でも問題なく動作します
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

    async def setup_hook(self) -> None:
        print("Running setup_hook...")
        for extension in self.initial_extensions:
            print(f"DEBUG: Attempting to load {extension}...")
            try:
                await self.load_extension(extension)
                print(f"DEBUG: Successfully loaded {extension}")
            except Exception as e:
                print(f"ERROR: Failed to load {extension}: {e}")
                traceback.print_exc()

        try:
            proseka_general_cog = self.get_cog("ProsekaGeneralCommands")
            ap_fc_rate_cog = self.get_cog("PjskApFcRateCommands") 
            rankmatch_cog = self.get_cog("ProsekaRankMatchCommands")

            print(f"DEBUG: setup_hook - After loading cogs. proseka_general_cog: {proseka_general_cog}, ap_fc_rate_cog: {ap_fc_rate_cog}, rankmatch_cog: {rankmatch_cog}") 

            if proseka_general_cog and ap_fc_rate_cog:
                proseka_general_cog.ap_fc_rate_cog = ap_fc_rate_cog
                print("DEBUG: Set ap_fc_rate_cog reference in ProsekaGeneralCommands.")
            else:
                print("WARNING: Could not get ProsekaGeneralCommands or PjskApFcRateCommands cog for linking. Check cog names or load order.")

            if rankmatch_cog and ap_fc_rate_cog:
                rankmatch_cog.ap_fc_rate_cog = ap_fc_rate_cog
                print("DEBUG: Set ap_fc_rate_cog reference in ProsekaRankMatchCommands.")
            else:
                print("WARNING: Could not get ProsekaRankMatchCommands or PjskApFcRateCommands cog for linking. Check cog names or load order.")

        except Exception as e:
            print(f"ERROR: Failed to link cogs: {e}")
            traceback.print_exc()

        print("DEBUG: Attempting to sync commands...")
        try:
            global_synced = await self.tree.sync()
            print(f"DEBUG: Synced {len(global_synced)} global commands.")
            for cmd in global_synced:
                print(f"DEBUG:   - Synced global command: {cmd.name}")

            support_guild = discord.Object(id=SUPPORT_GUILD_ID)
            guild_synced = await self.tree.sync(guild=support_guild)
            print(f"DEBUG: Synced {len(guild_synced)} commands to support guild {SUPPORT_GUILD_ID}.")
            for cmd in guild_synced:
                print(f"DEBUG:   - Synced guild command: {cmd.name}")

        except Exception as e:
            print(f"CRITICAL ERROR: Failed to sync commands: {e}")
            traceback.print_exc()

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')

        # proseka_songsとVALID_DIFFICULTIESはグローバル変数として既に読み込まれている
        self.total_songs = len(proseka_songs)
        self.total_charts = 0
        for song in proseka_songs:
            chart_count_for_song = 0
            for diff_key in VALID_DIFFICULTIES:
                if song.get(diff_key.lower()) is not None:
                    chart_count_for_song += 1
            self.total_charts += chart_count_for_song

        activity_name = f"{self.total_songs}曲/{self.total_charts}譜面が登録済み"
        await self.change_presence(activity=discord.Game(name=activity_name))
        print(f"Status set to: {activity_name}")

        print("\nDEBUG (main.py): Checking commands after on_ready:")
        all_commands_in_tree = self.tree.get_commands()
        if all_commands_in_tree:
            print(f"DEBUG (main.py): Found {len(all_commands_in_tree)} total commands in bot.tree (global/guild):")
            for cmd in all_commands_in_tree:
                if hasattr(cmd, 'guild_ids') and cmd.guild_ids:
                    guild_status = f"Guilds: {cmd.guild_ids}"
                elif hasattr(cmd, 'guild') and cmd.guild:
                    guild_status = f"Guild: {cmd.guild.id}"
                else:
                    guild_status = "Global"

                cmd_type_str = str(cmd.type) if hasattr(cmd, 'type') else "Unknown Type"
                print(f"DEBUG (main.py):   - Name: {cmd.name}, Type: {cmd_type_str}, {guild_status}")
        else:
            print(f"DEBUG (main.py): No commands found in bot.tree at all.")

        guild_commands_in_tree = self.tree.get_commands(guild=discord.Object(id=SUPPORT_GUILD_ID))
        if guild_commands_in_tree:
            print(f"DEBUG (main.py): Found {len(guild_commands_in_tree)} commands in bot.tree for guild {SUPPORT_GUILD_ID}:")
            for cmd in guild_commands_in_tree:
                print(f"DEBUG (main.py):   - {cmd.name}")
        else:
            print(f"DEBUG (main.py): No commands explicitly found for guild {SUPPORT_GUILD_ID} in bot.tree.")


bot = MyBot()

if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_BOT_TOKEN environment variable not set. Please check your .env file.")
