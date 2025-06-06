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
        status="設定するステータス (オンラインまたは応答不可)",
        activity_type="アクティビティタイプ",
        activity_name="アクティビティ名 (例: プレイ中)"
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(name="オンライン", value="online"),
            app_commands.Choice(name="応答不可", value="dnd")
        ],
        activity_type=[
            app_commands.Choice(name="プレイ中", value="playing"),
            app_commands.Choice(name="ストリーミング中", value="streaming"),
            app_commands.Choice(name="視聴中", value="watching"),
            app_commands.Choice(name="競合中", value="competing"),
            app_commands.Choice(name="リスニング", value="listening")
        ]
    )
    @app_commands.check(is_owner_global)
    async def set_status(self, interaction: discord.Interaction, status: str, activity_type: str = None, activity_name: str = None):
        """
        Sets the bot's Discord status and activity.
        """
        logging.info(f"Set_status command invoked by owner {interaction.user.name} (ID: {interaction.user.id}). Status: {status}, Activity Type: {activity_type}, Activity Name: {activity_name}")
        
        # ★修正点: defer を try-except で囲み、成功/失敗をフラグで管理
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
            
            activity = None
            if activity_type and activity_name:
                if activity_type == "playing":
                    activity = discord.Game(name=activity_name)
                elif activity_type == "streaming":
                    activity = discord.Streaming(name=activity_name, url="https://www.twitch.tv/discord") # URLはダミー
                elif activity_type == "watching":
                    activity = discord.Activity(type=discord.ActivityType.watching, name=activity_name)
                elif activity_type == "competing":
                    activity = discord.Activity(type=discord.ActivityType.competing, name=activity_name)
                elif activity_type == "listening":
                    activity = discord.Activity(type=discord.ActivityType.listening, name=activity_name)
                
            elif activity_name and not activity_type: # Only activity name provided without type
                activity = discord.CustomActivity(name=activity_name) # Default to Custom if type is not specified but name is.
            elif not activity_name and not activity_type:
                # If neither activity_name nor activity_type is provided, reset to default (empty activity)
                activity = None

            await self.bot.change_presence(status=discord_status, activity=activity)
            
            # ボットの管理者モードフラグを更新
            self.bot.is_admin_mode_active = (status == "dnd")
            logging.info(f"Bot's internal admin mode flag set to {self.bot.is_admin_mode_active} by {interaction.user.name} (status: {status}).")

            status_display = status.capitalize()
            activity_display = f"({activity_type.capitalize()}: {activity_name})" if activity_type and activity_name else ""
            if activity_name and not activity_type:
                activity_display = f"(カスタム: {activity_name})"

            response_message = f"✅ ボットのステータスを `{status_display}` {activity_display} に設定しました。"
            logging.info(f"Bot status changed to {status_display} {activity_display}.")

        except AttributeError:
            logging.error(f"Invalid status or activity type provided by user {interaction.user.id}.", exc_info=True)
            response_message = "❌ 無効なステータスまたはアクティビティタイプが指定されました。"
        except Exception as e:
            logging.error(f"Failed to set bot status for user {interaction.user.id}: {e}", exc_info=True)
            response_message = f"❌ ステータスの設定中にエラーが発生しました: {e}"
        
        # ★修正点: defer が成功したかどうかにかかわらず、followup.send を試みる★
        if defer_successful:
            await interaction.followup.send(response_message)
        else:
            # defer が失敗した場合、元々の interaction.response.send_message で試す
            # ただし、これは最初の応答でしか使えないため、既にタイムアウトしている場合はこれも失敗する可能性が高い
            # その場合は、エラーがログに記録されるだけで、ユーザーにはメッセージが届かない。
            # Discord APIのタイムアウトが原因の場合、ユーザーにはボットからの応答がない状態となる。
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(response_message, ephemeral=True) # ephemeralでユーザーにだけ表示
                except Exception as e:
                    logging.error(f"Failed to send direct response after defer failure: {e}", exc_info=True)


async def setup(bot):
    """Loads the StatusCommands cog into the bot."""
    cog = StatusCommands(bot)
    await bot.add_cog(cog)
    logging.info("StatusCommands cog loaded.")
