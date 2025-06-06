import discord
from discord.ext import commands
import logging
import asyncio # asyncio.sleep をインポート

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
        sync_status_message = "スラッシュコマンドの同期を開始します...\n"
        # 送信されたメッセージオブジェクトを保存し、後で編集できるようにする
        status_message_obj = await ctx.send(sync_status_message)

        target_guild_id = self.bot.GUILD_ID # ボットインスタンスからGUILD_IDを取得

        try:
            # 1. グローバルコマンドのクリア
            sync_status_message += "- グローバルコマンドをクリア中...\n"
            await status_message_obj.edit(content=sync_status_message) # メッセージを更新
            logging.info("Clearing ALL global commands...")
            self.bot.tree.clear_commands(guild=None) # グローバルコマンドをクリア
            await self.bot.tree.sync(guild=None) # グローバル同期を適用し、クリアを確定
            logging.info("Global commands cleared and synced.")
            await asyncio.sleep(1) # API負荷軽減のための遅延

            # 2. ギルド固有のコマンドのクリアと同期
            if target_guild_id != 0:
                guild_obj = discord.Object(id=target_guild_id)
                sync_status_message += f"- ギルド({target_guild_id})のコマンドをクリア中...\n"
                await status_message_obj.edit(content=sync_status_message) # メッセージを更新
                logging.info(f"Clearing ALL commands for guild {target_guild_id}...")
                self.bot.tree.clear_commands(guild=guild_obj) # 指定ギルドのコマンドをクリア
                await self.bot.tree.sync(guild=guild_obj) # ギルド同期を適用し、クリアを確定
                logging.info(f"Guild commands for {target_guild_id} cleared and synced.")
                await asyncio.sleep(1) # API負荷軽減のための遅延

                # 3. ボットの内部ツリーにある全てのコマンドを対象ギルドにコピーし、最終同期
                # これにより、全ての登録済みコマンドが指定ギルドに反映されることを意図
                sync_status_message += f"- ギルド({target_guild_id})にコマンドをコピーして最終同期中...\n"
                await status_message_obj.edit(content=sync_status_message) # メッセージを更新
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
                await status_message_obj.edit(content=sync_status_message) # メッセージを更新
                logging.info("Performing final global sync (GUILD_ID not set)...")
                synced_commands = await self.bot.tree.sync() # グローバル同期
                sync_status_message += f"✅ {len(synced_commands)} 個のグローバルコマンドを同期しました。\n"
                logging.info(f"Final global sync completed with {len(synced_commands)} commands.")

            sync_status_message += "\n--- 重要: Discordクライアントのキャッシュをクリアしてください ---"
            sync_status_message += "\n1. **ボットをサーバーからキック（削除）**し、再度招待してください。"
            sync_status_message += "\n2. **Discordアプリを完全に終了**し、再起動してください (Ctrl+Rでも可)。"
            sync_status_message += "\nこれらはDiscordのキャッシュをクリアし、コマンドの表示を正常にするために不可欠です。"

        except Exception as e:
            sync_status_message += f"\n❌ コマンド同期中にエラーが発生しました: {e}\n"
            logging.error(f"!sync コマンドの実行中にエラーが発生しました: {e}", exc_info=True)
        
        # 最終結果を送信または更新
        try:
            await status_message_obj.edit(content=sync_status_message) # 既存のメッセージを更新
        except Exception as e:
            logging.error(f"!sync コマンドの最終メッセージ更新に失敗しました: {e}", exc_info=True)
            # 既存メッセージの更新に失敗した場合は、新しいメッセージとして送信
            try:
                await ctx.send(sync_status_message) 
            except Exception as e_new:
                logging.error(f"!sync コマンドの新規メッセージ送信にも失敗しました: {e_new}", exc_info=True)


async def setup(bot):
    cog = DebugCommands(bot)
    await bot.add_cog(cog)
    logging.info("DebugCommands Cog loaded.")
