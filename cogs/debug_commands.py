import discord
from discord.ext import commands
import logging
import asyncio

# main.pyからis_bot_ownerをインポート (既にcommands.is_owner()が使われているが、念のため)
from main import is_bot_owner

# ロギング設定は main.py で一元的に行われるため、ここでのbasicConfigは不要です。

class DebugCommands(commands.Cog):
    """
    ボットのデバッグおよび管理コマンドを提供します。
    これらのコマンドはオーナーのみが利用可能です。
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logging.info("DebugCommands Cog initialized.")

    @commands.command(name="sync", description="スラッシュコマンドをDiscordと同期します (オーナー限定)。")
    @commands.is_owner() # オーナー限定のため、is_not_admin_mode_for_non_ownerは不要
    async def sync_commands(self, ctx: commands.Context):
        """
        ボットのスラッシュコマンドをDiscord APIと同期します。
        主に開発中に新しいコマンドや変更を適用するために使用されます。
        """
        sync_status_message = "スラッシュコマンドの同期を開始します...\n"
        status_message_obj = await ctx.send(sync_status_message)

        target_guild_id = self.bot.GUILD_ID

        try:
            # 同期前にボットが内部で認識しているコマンド数を報告
            global_commands_before_sync = self.bot.tree.get_commands(guild=None)
            guild_commands_before_sync = self.bot.tree.get_commands(guild=discord.Object(id=target_guild_id)) if target_guild_id != 0 else []

            sync_status_message += f"- ボット内部で認識されているグローバルコマンド: {len(global_commands_before_sync)}個\n"
            sync_status_message += f"- ボット内部で認識されているギルド({target_guild_id})コマンド: {len(guild_commands_before_sync)}個\n"
            await status_message_obj.edit(content=sync_status_message)
            
            synced_count = 0
            if target_guild_id != 0:
                guild_obj = discord.Object(id=target_guild_id)
                sync_status_message += f"- ギルド({target_guild_id})にコマンドを同期中...\n"
                await status_message_obj.edit(content=sync_status_message)
                
                # グローバルコマンドをギルドにコピー (ギルド固有のコマンドも維持される)
                self.bot.tree.copy_global_to(guild=guild_obj)
                
                # その後、このギルドのすべてのコマンドを同期（コピーされたグローバルコマンドと既存のギルドコマンドを含む）
                synced_commands = await self.bot.tree.sync(guild=guild_obj)
                synced_count = len(synced_commands)
                
                sync_status_message += f"✅ このギルド ({target_guild_id}) に {synced_count} 個のコマンドを同期しました。\n"
                logging.info(f"Synced {synced_count} commands to guild {target_guild_id}.")
            else:
                # GUILD_ID が設定されていない場合は、グローバル同期のみを行う
                sync_status_message += "- GUILD_ID が設定されていないため、グローバルコマンドを同期中...\n"
                await status_message_obj.edit(content=sync_status_message)
                synced_commands = await self.bot.tree.sync() # グローバル同期
                synced_count = len(synced_commands)
                sync_status_message += f"✅ {synced_count} 個のグローバルコマンドを同期しました。\n"
                logging.info(f"Synced {synced_count} global commands.")

            # 同期後、ボット内部のツリーは変更されないはずなので、再度確認して表示
            global_commands_after_sync = self.bot.tree.get_commands(guild=None)
            guild_commands_after_sync = self.bot.tree.get_commands(guild=discord.Object(id=target_guild_id)) if target_guild_id != 0 else []

            sync_status_message += f"\n--- ボット内部認識コマンド (同期後も同じはず) ---"
            sync_status_message += f"\nグローバル: {len(global_commands_after_sync)} 個"
            sync_status_message += f"\nギルド({target_guild_id}): {len(guild_commands_after_sync)} 個"
            
            sync_status_message += "\n\n--- 重要: Discordクライアントのキャッシュをクリアしてください ---"
            sync_status_message += "\n1. **ボットをサーバーからキック（削除）**し、再度招待してください。"
            sync_status_message += "\n2. **Discordアプリを完全に終了**し、再起動してください (Ctrl+Rでも可)。"
            sync_status_message += "\nこれらはDiscordのキャッシュをクリアし、コマンドの表示を正常にするために不可欠です。"

        except Exception as e:
            sync_status_message += f"\n❌ コマンド同期中にエラーが発生しました: {e}\n"
            logging.error(f"!sync コマンドの実行中にエラーが発生しました: {e}", exc_info=True)
        
        try:
            await status_message_obj.edit(content=sync_status_message)
        except Exception as e:
            logging.error(f"!sync コマンドの最終メッセージ更新に失敗しました: {e}", exc_info=True)
            try:
                await ctx.send(sync_status_message)
            except Exception as e_new:
                logging.error(f"!sync コマンドの新規メッセージ送信にも失敗しました: {e_new}", exc_info=True)

    @commands.command(name="check_local_commands", description="ボットが内部で認識しているスラッシュコマンドを表示します (オーナー限定)。")
    @commands.is_owner() # オーナー限定のため、is_not_admin_mode_for_non_ownerは不要
    async def check_local_commands(self, ctx: commands.Context):
        """
        ボットが現在内部で認識しているスラッシュコマンドのリストを表示します。
        グローバルコマンドとギルド固有コマンドの両方を含みます。
        """
        global_commands = self.bot.tree.get_commands(guild=None)
        guild_commands = []
        target_guild_id = self.bot.GUILD_ID
        if target_guild_id != 0:
            guild_commands = self.bot.tree.get_commands(guild=discord.Object(id=target_guild_id))

        message_parts = []
        message_parts.append("### ボットが内部で認識しているスラッシュコマンド:\n\n")
        
        message_parts.append("#### グローバルコマンド:\n")
        if global_commands:
            for cmd in global_commands:
                message_parts.append(f"- `/{cmd.name}` (グローバル)\n")
        else:
            message_parts.append("認識しているグローバルコマンドはありません。\n")

        if target_guild_id != 0:
            message_parts.append(f"\n#### ギルド({target_guild_id})コマンド:\n")
            if guild_commands:
                for cmd in guild_commands:
                    message_parts.append(f"- `/{cmd.name}` (ギルド)\n")
            else:
                message_parts.append(f"認識しているギルド({target_guild_id})コマンドはありません。\n")
        else:
            message_parts.append("\nGUILD_IDが設定されていないため、ギルド固有コマンドは認識されません。\n")

        full_message = "".join(message_parts)

        # Discordのメッセージ文字数制限 (2000文字) に対応
        if len(full_message) > 2000:
            chunks = [full_message[i:i+1990] for i in range(0, len(full_message), 1990)]
            for chunk in chunks:
                await ctx.send(chunk)
        else:
            await ctx.send(full_message)

async def setup(bot):
    """DebugCommandsコグをボットにロードします。"""
    cog = DebugCommands(bot)
    await bot.add_cog(cog)
    logging.info("DebugCommands Cog loaded.")
