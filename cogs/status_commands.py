import discord
from discord.ext import commands
from discord import app_commands
import os
import logging

# .envファイルから環境変数を読み込む
from dotenv import load_dotenv
load_dotenv()

# main.py の OWNER_ID と同じ値をここに設定してください
OWNER_ID = int(os.getenv('OWNER_ID'))

# オーナーチェック用の関数
def is_owner_global(interaction: discord.Interaction) -> bool:
    return interaction.user.id == OWNER_ID

class StatusCommands(commands.Cog):
    """
    Commands for managing the bot's status (owner only).
    """
    def __init__(self, bot):
        self.bot = bot
        logging.info("StatusCommands Cog initialized.")

    @app_commands.command(name="set_status", description="ボットのステータスを設定します (オーナーのみ)")
    @app_commands.describe(
        # ★修正点: activity_typeとactivity_nameの説明を削除★
        status="設定するステータス (オンライン, 退席中, 取り込み中, オフライン/ステルス)" # 説明を更新
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(name="オンライン (緑の丸)", value="online"),
            app_commands.Choice(name="退席中 (オレンジの三日月)", value="idle"),
            app_commands.Choice(name="取り込み中 (赤い横棒)", value="dnd"), # ★修正点: 「応答不可」を「取り込み中」に変更★
            app_commands.Choice(name="オフライン/ステルス (灰色の丸)", value="invisible")
        ]
        # ★修正点: activity_typeとactivity_nameのchoicesを削除★
    )
    # ★修正点: function signatureからactivity_typeとactivity_nameを削除★
    async def set_status(self, interaction: discord.Interaction, status: str):
        """
        Sets the bot's Discord status.
        """
        # ★修正点: ログメッセージを簡略化★
        logging.info(f"Set_status command invoked by owner {interaction.user.name} (ID: {interaction.user.id}). Status: {status}.")
        
        defer_successful = False
        if not interaction.response.is_done():
            try:
                await interaction.response.defer(ephemeral=False) # Public defer
                defer_successful = True
                logging.info(f"Successfully deferred interaction for '{interaction.command.name}'.")
            except discord.errors.NotFound:
                logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound). This means the interaction likely timed out.", exc_info=True)
            except Exception as e:
                logging.error(f"Unexpected error during defer for '{interaction.command.name}': {e}", exc_info=True)
        else:
            logging.warning(f"Interaction for '{interaction.command.name}' was already responded to or timed out before defer. Attempting to send followup directly.")


        response_message = ""
        try:
            discord_status = getattr(discord.Status, status)
            
            # ★修正点: activityを常にNoneに設定（アクティビティ項目を削除したため）★
            activity = None

            await self.bot.change_presence(status=discord_status, activity=activity)
            
            # ボットの管理者モードフラグを更新
            # dndの場合のみTrue、それ以外（online, idle, invisible）はFalse
            self.bot.is_admin_mode_active = (status == "dnd")
            logging.info(f"Bot's internal admin mode flag set to {self.bot.is_admin_mode_active} by {interaction.user.name} (status: {status}).")

            # ★修正点: ステータスの表示名と視覚的な説明を強化（「取り込み中」に対応）★
            status_display_with_visual_hint = ""
            if status == "online":
                status_display_with_visual_hint = "オンライン (緑の丸)"
            elif status == "idle":
                status_display_with_visual_hint = "退席中 (オレンジの三日月)"
            elif status == "dnd":
                status_display_with_visual_hint = "取り込み中 (赤い横棒)" # ★修正点: ここも「取り込み中」に★
            elif status == "invisible":
                status_display_with_visual_hint = "オフライン/ステルス (灰色の丸)"
            else:
                status_display_with_visual_hint = status.capitalize() # Fallback

            # ★修正点: activity_displayの構築ロジックを削除（アクティビティ項目を削除したため）★

            response_message = (
                f"✅ ボットのステータスを `{status_display_with_visual_hint}` に設定しました。\n"
                "**変更がDiscordクライアントに反映されない場合は、Discordアプリを完全に再起動してみてください。**"
            )
            # ★修正点: ログメッセージを簡略化★
            logging.info(f"Bot status changed to {status_display_with_visual_hint}.")

        except AttributeError:
            # ★修正点: エラーメッセージを簡略化★
            logging.error(f"Invalid status provided by user {interaction.user.id}.", exc_info=True)
            response_message = "❌ 無効なステータスが指定されました。"
        except Exception as e:
            logging.error(f"Failed to set bot status for user {interaction.user.id}: {e}", exc_info=True)
            response_message = f"❌ ステータスの設定中にエラーが発生しました: {e}"
        
        # defer が成功したかどうかにかかわらず、followup.send を試みる
        if defer_successful:
            await interaction.followup.send(response_message)
        else:
            # defer が失敗した場合、元々の interaction.response.send_message で試す
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(response_message, ephemeral=True)
                except Exception as e:
                    logging.error(f"Failed to send direct response after defer failure: {e}", exc_info=True)


async def setup(bot):
    """Loads the StatusCommands cog into the bot."""
    cog = StatusCommands(bot)
    await bot.add_cog(cog)
    logging.info("StatusCommands cog loaded.")
