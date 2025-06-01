import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
from data.songs import proseka_songs, VALID_DIFFICULTIES

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
OWNER_ID = int(os.getenv('OWNER_ID')) if os.getenv('OWNER_ID') else None

SUPPORT_GUILD_ID = 1376551581423767582 

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
            owner_id=OWNER_ID
        )

        self.initial_extensions = [
            'cogs.pjsk_ap_fc_rate',      
            'cogs.proseka_general',      
            'cogs.help_command',
            'cogs.proseka_rankmatch', # このコグ
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
            rankmatch_cog = self.get_cog("ProsekaRankMatchCommands") # ★ ProsekaRankMatchCommands を取得

            print(f"DEBUG: setup_hook - After loading cogs. proseka_general_cog: {proseka_general_cog}, ap_fc_rate_cog: {ap_fc_rate_cog}, rankmatch_cog: {rankmatch_cog}") 

            if proseka_general_cog and ap_fc_rate_cog:
                proseka_general_cog.ap_fc_rate_cog = ap_fc_rate_cog
                print("DEBUG: Set ap_fc_rate_cog reference in ProsekaGeneralCommands.")
            else:
                print("WARNING: Could not get ProsekaGeneralCommands or PjskApFcRateCommands cog for linking. Check cog names or load order.")

            # ★ ここにPjskRankMatchCommands への参照設定を追加します
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