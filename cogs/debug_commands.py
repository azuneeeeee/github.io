import discord
from discord.ext import commands
from discord import app_commands
import logging

# main.py から is_bot_owner ヘルパー関数と GUILD_ID をインポート
from main import is_bot_owner, GUILD_ID

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class DebugCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logging.info("DebugCommands Cog initialized.")

    @app_commands.command(name="sync", description="スラッシュコマンドをDiscordと同期します (オーナー限定)。")
    @is_bot_owner() # グローバルからインポートしたヘルパー関数を使用
    @app_commands.guilds(discord.Object(id=GUILD_ID)) # main からインポートした GUILD_ID を使用
    async def sync_commands(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        sync_status_message = ""
        target_guild_id = self.bot.GUILD_ID # ボットインスタンスからGUILD_IDを取得

        if target_guild_id != 0:
            try:
                guild_obj = discord.Object(id=target_guild_id)
                
                # ボットの内部ツリーにある全コマンドを、そのギルドに同期
                # これにより、コグから追加されたコマンドと、MyBotクラスに直接定義された /sync コマンドも含まれる
                synced_commands = await self.bot.tree.sync(guild=guild_obj) # tree.sync() を呼び出す

                sync_status_message += f"このギルド ({target_guild_id}) のコマンドを再同期しました: {len(synced_commands)}個"
                logging.info(f"Re-synced {len(synced_commands)} commands to support guild {target_guild_id} via /sync command.")
            except Exception as e:
                sync_status_message += f"ギルドコマンドの同期に失敗しました: {e}"
                logging.error(f"Failed to guild sync commands via /sync command: {e}", exc_info=True)
        else:
            sync_status_message += "GUILD_ID が設定されていないため、ギルドコマンドの同期はできません。グローバル同期はできません。"
            logging.warning("GUILD_ID not set, skipping guild command sync via /sync command.")
        
        await interaction.followup.send(sync_status_message, ephemeral=True)

async def setup(bot):
    cog = DebugCommands(bot)
    await bot.add_cog(cog)
    logging.info("DebugCommands Cog loaded.")
