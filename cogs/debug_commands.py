import discord
from discord.ext import commands
from discord import app_commands
import logging

# main.py から is_bot_owner ヘルパー関数をインポート
# ボットの OWNER_ID は main.py のボットインスタンスから取得される
from main import is_bot_owner

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class DebugCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logging.info("DebugCommands Cog initialized.")

    @app_commands.command(name="sync", description="スラッシュコマンドをDiscordと同期します (オーナー限定)。")
    @is_bot_owner() # グローバルからインポートしたヘルパー関数を使用
    async def sync_commands(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        sync_status_message = ""
        guild_id = self.bot.GUILD_ID # ボットインスタンスからGUILD_IDを取得
        
        if guild_id != 0:
            try:
                guild_obj = discord.Object(id=guild_id)
                
                # ギルドのコマンドを一度完全にクリア (古い定義を排除)
                logging.info(f"Clearing ALL commands for guild {guild_id} via /sync command...")
                self.bot.tree.clear_commands(guild=guild_obj)
                await self.bot.tree.sync(guild=guild_obj) # クリアを反映させるために同期
                
                # ボットの内部ツリーにある全コマンドを、そのギルドにコピーして同期
                self.bot.tree.copy_global_to(guild=guild_obj) # グローバルコマンドをギルドにコピー
                synced_guild_commands = await self.bot.tree.sync(guild=guild_obj)
                
                sync_status_message += f"このギルド ({guild_id}) のコマンドを再同期しました: {len(synced_guild_commands)}個"
                logging.info(f"Re-synced {len(synced_guild_commands)} commands to support guild {guild_id} via /sync command.")
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
