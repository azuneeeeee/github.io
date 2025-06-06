import discord
from discord.ext import commands
import logging
import asyncio

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class DebugCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logging.info("DebugCommands Cog initialized.")

    @commands.command(name="sync", description="スラッシュコマンドをDiscordと同期します (オーナー限定)。")
    @commands.is_owner()
    async def sync_commands(self, ctx: commands.Context):
        sync_status_message = "スラッシュコマンドの同期を開始します...\n"
        status_message_obj = await ctx.send(sync_status_message)

        target_guild_id = self.bot.GUILD_ID

        try:
            # 1. グローバルコマンドのクリア
            sync_status_message += "- グローバルコマンドをクリア中...\n"
            await status_message_obj.edit(content=sync_status_message)
            logging.info("Clearing ALL global commands...")
            self.bot.tree.clear_commands(guild=None) # グローバルコマンドをクリア
            await self.bot.tree.sync(guild=None) # グローバル同期を適用し、クリアを確定
            logging.info("Global commands cleared and synced.")
            await asyncio.sleep(1)

            # 2. ギルド固有のコマンドのクリアと同期
            if target_guild_id != 0:
                guild_obj = discord.Object(id=target_guild_id)
                sync_status_message += f"- ギルド({target_guild_id})のコマンドをクリア中...\n"
                await status_message_obj.edit(content=sync_status_message)
                logging.info(f"Clearing ALL commands for guild {target_guild_id}...")
                self.bot.tree.clear_commands(guild=guild_obj) # 指定ギルドのコマンドをクリア
                await self.bot.tree.sync(guild=guild_obj) # ギルド同期を適用し、クリアを確定
                logging.info(f"Guild commands for {target_guild_id} cleared and synced.")
                await asyncio.sleep(1)

                # 3. ボットの内部ツリーにある全てのコマンドを対象ギルドにコピーし、最終同期
                sync_status_message += f"- ギルド({target_guild_id})にコマンドをコピーして最終同期中...\n"
                await status_message_obj.edit(content=sync_status_message)
                logging.info(f"Copying ALL internal commands to guild {target_guild_id} for final sync...")
                
                # ボットのtreeに登録されている全コマンドを対象ギルドにコピー
                # これは、app_commands.command(guilds=[...]) で登録されたコマンドも、
                # グローバルとして定義されたがguildにコピーしたいコマンドも含む
                self.bot.tree.copy_global_to(guild=guild_obj) 
                synced_commands = await self.bot.tree.sync(guild=guild_obj)
                
                sync_status_message += f"✅ このギルド ({target_guild_id}) に {len(synced_commands)} 個のコマンドを同期しました。\n"
                logging.info(f"Final sync completed for guild {target_guild_id} with {len(synced_commands)} commands.")
            else:
                # GUILD_ID が設定されていない場合は、グローバル同期のみを行う
                sync_status_message += "- GUILD_ID が設定されていないため、グローバルコマンドを最終同期中...\n"
                await status_message_obj.edit(content=sync_status_message)
                logging.info("Performing final global sync (GUILD_ID not set)...")
                synced_commands = await self.bot.tree.sync() # グローバル同期
                sync_status_message += f"✅ {len(synced_commands)} 個のグローバルコマンドを同期しました。\n"
                logging.info(f"Final global sync completed with {len(synced_commands)} commands.")
            
            # ボットの内部に存在するコマンド数も表示
            global_commands_internal = self.bot.tree.get_commands(guild=None)
            guild_commands_internal = self.bot.tree.get_commands(guild=discord.Object(id=target_guild_id)) if target_guild_id != 0 else []
            
            sync_status_message += f"\n--- ボット内部認識コマンド ---"
            sync_status_message += f"\nグローバル: {len(global_commands_internal)} 個"
            sync_status_message += f"\nギルド({target_guild_id}): {len(guild_commands_internal)} 個"
            
            sync_status_message += "\n\n--- 重要: Discordクライアントのキャッシュをクリアしてください ---"
            sync_status_message += "\n1. **ボットをサーバーからキック（削除）**し、再度招待してください。"
            sync_status_message += "\n2. **Discordアプリを完全に終了**し、再起動してください (Ctrl+Rでも可)。"
            sync_status_message += "\nこれらはDiscordのキャッシュをクリアし、コマンドの表示を正常にするために不可欠です。"

        except Exception as e:
            sync_status_message += f"\n❌ コマンド同期中にエラーが発生しました: {e}\n"
            logging.error(f"!sync コマンドの実行中にエラーが発生しました: {e}", exc_info=True)
        
        # 最終結果を送信または更新
        try:
            await status_message_obj.edit(content=sync_status_message)
        except Exception as e:
            logging.error(f"!sync コマンドの最終メッセージ更新に失敗しました: {e}", exc_info=True)
            try:
                await ctx.send(sync_status_message)
            except Exception as e_new:
                logging.error(f"!sync コマンドの新規メッセージ送信にも失敗しました: {e_new}", exc_info=True)

    @commands.command(name="check_local_commands", description="ボットが内部で認識しているスラッシュコマンドを表示します (オーナー限定)。")
    @commands.is_owner()
    async def check_local_commands(self, ctx: commands.Context):
        await ctx.defer(ephemeral=True) # 即座に応答してタイムアウトを防ぐ
        
        global_commands = self.bot.tree.get_commands(guild=None)
        guild_commands = []
        target_guild_id = self.bot.GUILD_ID
        if target_guild_id != 0:
            guild_commands = self.bot.tree.get_commands(guild=discord.Object(id=target_guild_id))

        message = "### ボットが内部で認識しているスラッシュコマンド:\n\n"
        
        message += "#### グローバルコマンド:\n"
        if global_commands:
            for cmd in global_commands:
                message += f"- `/{cmd.name}` (グローバル)\n"
        else:
            message += "認識しているグローバルコマンドはありません。\n"

        if target_guild_id != 0:
            message += f"\n#### ギルド({target_guild_id})コマンド:\n"
            if guild_commands:
                for cmd in guild_commands:
                    message += f"- `/{cmd.name}` (ギルド)\n"
            else:
                message += f"認識しているギルド({target_guild_id})コマンドはありません。\n"
        else:
            message += "\nGUILD_IDが設定されていないため、ギルド固有コマンドは認識されません。\n"

        if len(message) > 2000:
            # メッセージが長すぎる場合は分割して送信
            await ctx.followup.send(message[:1990] + "...", ephemeral=True)
            # 必要に応じてさらに分割送信するロジックを追加可能
        else:
            await ctx.followup.send(message, ephemeral=True)

async def setup(bot):
    cog = DebugCommands(bot)
    await bot.add_cog(cog)
    logging.info("DebugCommands Cog loaded.")
