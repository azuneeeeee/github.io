import discord
from discord.ext import commands
import logging
import asyncio # asyncio.sleep を追加

# commands.is_owner() を直接使用するため、main からは何もインポートしない

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class DebugCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logging.info("DebugCommands Cog initialized.")

    @commands.command(name="sync", description="スラッシュコマンドをDiscordと同期します (オーナー限定)。")
    @commands.is_owner() # ここで組み込みのオーナーチェックを使用
    async def sync_commands(self, ctx: commands.Context): # interaction ではなく ctx を受け取る
        # 応答がタイムアウトしないように、最初にメッセージを送信
        try:
            await ctx.send("スラッシュコマンドの同期を開始します...")
        except Exception as e:
            logging.error(f"Failed to send initial message for !sync: {e}", exc_info=True)
            
        sync_status_message = ""
        target_guild_id = self.bot.GUILD_ID # ボットインスタンスからGUILD_IDを取得

        if target_guild_id != 0:
            try:
                guild_obj = discord.Object(id=target_guild_id)
                
                # ギルドのコマンドを一度完全にクリア (古い定義を排除)
                logging.info(f"Clearing ALL commands for guild {target_guild_id} via !sync command...")
                self.bot.tree.clear_commands(guild=guild_obj)
                await self.bot.tree.sync(guild=guild_obj) # クリアを反映させるために同期
                
                # 短い遅延を挿入してAPIの負荷を軽減
                await asyncio.sleep(1) 
                
                # ボットの内部ツリーにある全コマンドを、そのギルドにコピーして同期
                self.bot.tree.copy_global_to(guild=guild_obj) 
                synced_commands = await self.bot.tree.sync(guild=guild_obj)
                
                sync_status_message += f"このギルド ({target_guild_id}) のコマンドを再同期しました: {len(synced_commands)}個"
                logging.info(f"Re-synced {len(synced_commands)} commands to support guild {target_guild_id} via !sync command.")
            except Exception as e:
                sync_status_message += f"ギルドコマンドの同期に失敗しました: {e}"
                logging.error(f"Failed to guild sync commands via !sync command: {e}", exc_info=True)
        else:
            sync_status_message += "GUILD_ID が設定されていないため、ギルドコマンドの同期はできません。グローバル同期はできません。"
            logging.warning("GUILD_ID not set, skipping guild command sync via !sync command.")
        
        # 処理結果を送信
        try:
            await ctx.send(sync_status_message)
        except Exception as e:
            logging.error(f"Failed to send final message for !sync: {e}", exc_info=True)


async def setup(bot):
    cog = DebugCommands(bot)
    await bot.add_cog(cog)
    logging.info("DebugCommands Cog loaded.")
