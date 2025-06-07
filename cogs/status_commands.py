import discord
from discord.ext import commands
from discord import app_commands
import os
import logging
# ★修正: is_bot_owner を直接インポートし、is_owner_global は使用しない★
from main import is_bot_owner 

# .envファイルから環境変数を読み込む (このファイルでは不要ですが、Pythonの規約に従い残します)
from dotenv import load_dotenv
load_dotenv()

class StatusCommands(commands.Cog):
    """
    Commands for managing the bot's status (owner only).
    ボットのカスタムステータスを設定します (オーナーのみ)。
    """
    def __init__(self, bot):
        self.bot = bot
        logging.info("StatusCommands Cog initialized.")

    @app_commands.command(name="set_status", description="ボットのステータスを設定します (オーナーのみ)")
    @app_commands.describe(
        status="設定するステータス" # 説明を簡略化
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(name="オンライン", value="online"),
            app_commands.Choice(name="取り込み中", value="dnd"), # 「取り込み中」を選択したら内部的にはdnd (赤い横棒)
        ]
    )
    # ★修正: is_bot_owner() を直接デコレータとして使用★
    @app_commands.check(is_bot_owner()) 
    async def set_status(self, interaction: discord.Interaction, status: str):
        """
        Sets the bot's Discord status and, if "dnd", sets a custom activity.
        """
        logging.info(f"Set_status command invoked by owner {interaction.user.name} (ID: {interaction.user.id}). Desired status: {status}.")
        
        defer_successful = False
        if not interaction.response.is_done():
            try:
                await interaction.response.defer(ephemeral=False) # Public defer
                defer_successful = True
                logging.info(f"Successfully deferred interaction for '{interaction.command.name}'.")
            except discord.errors.NotFound:
                logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound). Interaction likely timed out.", exc_info=True)
            except Exception as e:
                logging.error(f"Unexpected error during initial defer for '{interaction.command.name}': {e}", exc_info=True)
        else:
            logging.warning(f"Interaction for '{interaction.command.name}' was already responded to or timed out at command entry. Attempting to send followup directly.")


        response_message = ""
        try:
            discord_status = getattr(discord.Status, status) # "online" または "dnd"
            
            activity = None
            if status == "dnd":
                activity = discord.CustomActivity(name="現在は使用できません")
                logging.info(f"Setting custom activity '現在は使用できません' for 'dnd' status.")

            await self.bot.change_presence(status=discord_status, activity=activity)
            
            # ボットの管理者モードフラグを更新
            # 「取り込み中」（value="dnd"）が選択された場合のみTrue、それ以外はFalse
            self.bot.is_admin_mode_active = (status == "dnd") # 管理者モードフラグはdndでONにする
            logging.info(f"Bot's internal admin mode flag set to {self.bot.is_admin_mode_active} by {interaction.user.name} (selected status: {status}).")

            status_display_with_visual_hint = ""
            if status == "online":
                status_display_with_visual_hint = "オンライン (緑の丸)"
            elif status == "dnd": 
                status_display_with_visual_hint = "取り込み中 (赤い横棒 / カスタムステータス: 現在は使用できません)" 
            else:
                status_display_with_visual_hint = status.capitalize() # Fallback

            response_message = (
                f"✅ ボットのステータスを `{status_display_with_visual_hint}` に設定しました。\n"
                f"製作者以外のコマンドは{'制限されました' if self.bot.is_admin_mode_active else '制限されていません'}。\n"
                "**変更がDiscordクライアントに反映されない場合は、Discordアプリを完全に再起動してみてください。**"
            )
            logging.info(f"Bot status changed to {status_display_with_visual_hint}.")

        except AttributeError:
            logging.error(f"Invalid status provided by user {interaction.user.id}.", exc_info=True)
            response_message = "❌ 無効なステータスが指定されました。"
        except Exception as e:
            logging.error(f"Failed to set bot status for user {interaction.user.id}: {e}", exc_info=True)
            response_message = f"❌ ステータスの設定中にエラーが発生しました: {e}"
        
        if defer_successful:
            try:
                await interaction.followup.send(response_message)
            except Exception as e:
                logging.error(f"Failed to send follow-up message after successful defer: {e}", exc_info=True)
        else:
            if not interaction.response.is_done():
                logging.warning(f"Failed to send message to user for '{interaction.command.name}' as defer failed and interaction was already acknowledged/timed out.")


async def setup(bot):
    """Loads the StatusCommands cog into the bot."""
    cog = StatusCommands(bot)
    await bot.add_cog(cog)
    logging.info("StatusCommands cog loaded.")
