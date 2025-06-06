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
        sync_status_message = "スラッシュコマンドの同期を開始します...\n"
        await ctx.send(sync_status_message) # まず初期メッセージを送信

        target_guild_id = self.bot.GUILD_ID # ボットインスタンスからGUILD_IDを取得

        try:
            # -----------------------------------------------------
            # 強制的な同期ロジック
            # 1. まずグローバルコマンドをクリアし、同期 (Discordの古いグローバルキャッシュをリセット)
            sync_status_message += "- グローバルコマンドをクリア中...\n"
            await ctx.edit(content=sync_status_message) # メッセージを更新
            logging.info("Clearing ALL global commands...")
            self.bot.tree.clear_commands(guild=None) # グローバルコマンドをクリア
            await self.bot.tree.sync(guild=None) # グローバル同期を適用
            logging.info("Global commands cleared and synced.")
            await asyncio.sleep(1) # API負荷軽減のための遅延

            # 2. 指定されたギルドのコマンドをクリアし、同期 (Discordの古いギルドキャッシュをリセット)
            if target_guild_id != 0:
                guild_obj = discord.Object(id=target_guild_id)
                sync_status_message += f"- ギルド({target_guild_id})のコマンドをクリア中...\n"
                await ctx.edit(content=sync_status_message) # メッセージを更新
                logging.info(f"Clearing ALL commands for guild {target_guild_id}...")
                self.bot.tree.clear_commands(guild=guild_obj) # 指定ギルドのコマンドをクリア
                await self.bot.tree.sync(guild=guild_obj) # 指定ギルドの同期を適用
                logging.info(f"Guild commands for {target_guild_id} cleared and synced.")
                await asyncio.sleep(1) # API負荷軽減のための遅延
            else:
                sync_status_message += "- GUILD_ID が設定されていないため、ギルドコマンドのクリアはスキップされました。\n"
                await ctx.edit(content=sync_status_message) # メッセージを更新

            # 3. ボットに登録されている全てのコマンドを対象ギルドにコピーし、最終的な同期
            # これには、各コグで @app_commands.command として定義されたコマンドも含まれる
            if target_guild_id != 0:
                sync_status_message += f"- ギルド({target_guild_id})にコマンドをコピーして再同期中...\n"
                await ctx.edit(content=sync_status_message) # メッセージを更新
                logging.info(f"Copying global commands to guild {target_guild_id} and syncing...")
                self.bot.tree.copy_global_to(guild=guild_obj) 
                synced_commands = await self.bot.tree.sync(guild=guild_obj)
                sync_status_message += f"✅ このギルド ({target_guild_id}) に {len(synced_commands)} 個のコマンドを再同期しました。\n"
                logging.info(f"Re-synced {len(synced_commands)} commands to guild {target_guild_id}.")
            else:
                # GUILD_ID が設定されていない場合は、グローバル同期のみを行う
                sync_status_message += "- GUILD_ID が設定されていないため、グローバルコマンドを同期中...\n"
                await ctx.edit(content=sync_status_message) # メッセージを更新
                logging.info("Performing global sync (GUILD_ID not set)...")
                synced_commands = await self.bot.tree.sync() # グローバル同期
                sync_status_message += f"✅ GUILD_ID が設定されていないため、{len(synced_commands)} 個のグローバルコマンドを同期しました。\n"
                logging.info(f"Synced {len(synced_commands)} global commands.")

            sync_status_message += "\nDiscordクライアントを再起動すると、変更が反映されます。"

        except Exception as e:
            sync_status_message += f"\n❌ コマンド同期中にエラーが発生しました: {e}\n"
            logging.error(f"!sync コマンドの実行中にエラーが発生しました: {e}", exc_info=True)
        
        # 最終結果を送信または更新
        try:
            await ctx.edit(content=sync_status_message) # 既存のメッセージを更新
        except Exception as e:
            logging.error(f"!sync コマンドの最終メッセージ更新に失敗しました: {e}", exc_info=True)
            try:
                await ctx.send(sync_status_message) # 更新できなかった場合は新規送信
            except Exception as e_new:
                logging.error(f"!sync コマンドの新規メッセージ送信にも失敗しました: {e_new}", exc_info=True)


async def setup(bot):
    cog = DebugCommands(bot)
    await bot.add_cog(cog)
    logging.info("DebugCommands Cog loaded.")
