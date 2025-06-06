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
        status="設定するステータス" # 説明を簡略化
    )
    @app_commands.choices(
        status=[
            app_commands.Choice(name="オンライン", value="online"),
            app_commands.Choice(name="取り込み中", value="dnd"), # 「取り込み中」を選択したら内部的にはdnd (赤い横棒)
        ]
    )
    async def set_status(self, interaction: discord.Interaction, status: str):
        """
        Sets the bot's Discord status and, if "dnd", sets a custom activity.
        """
        logging.info(f"Set_status command invoked by owner {interaction.user.name} (ID: {interaction.user.id}). Desired status: {status}.")
        
        # defer は必須であるため、まず defer を試み、失敗したらそれ以上応答しない
        # この try-except は Unknown interaction をキャッチするため。
        # defer が成功したかどうかをフラグで管理
        initial_response_attempted = False
        defer_successful = False

        if not interaction.response.is_done():
            try:
                await interaction.response.defer(ephemeral=False) # Public defer
                defer_successful = True
                initial_response_attempted = True
                logging.info(f"Successfully deferred interaction for '{interaction.command.name}'.")
            except discord.errors.NotFound:
                # Unknown interaction: インタラクションがタイムアウトした
                logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound). Interaction likely timed out.", exc_info=True)
                # defer が失敗した場合は、ユーザーへの応答は困難なので、ここで return する
                # ただし、以降のステータス変更ロジックは実行したいので、try-finally で囲む
            except Exception as e:
                logging.error(f"Unexpected error during initial defer for '{interaction.command.name}': {e}", exc_info=True)
            
            # defer に失敗した場合でも、ステータス変更ロジックは実行する
            # response_message の初期化は try の外で行う
            response_message = ""
            try:
                discord_status = getattr(discord.Status, status) # "online" または "dnd"
                
                activity = None
                if status == "dnd":
                    activity = discord.CustomActivity(name="現在は使用できません")
                    logging.info(f"Setting custom activity '現在は使用できません' for 'dnd' status.")

                await self.bot.change_presence(status=discord_status, activity=activity)
                
                self.bot.is_admin_mode_active = (status == "dnd") 
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
            
            # ここで、ユーザーへの最終的な応答を試みる
            if defer_successful: # defer が成功していた場合のみ followup を使用
                try:
                    await interaction.followup.send(response_message)
                except Exception as e:
                    logging.error(f"Failed to send follow-up message after successful defer: {e}", exc_info=True)
            else:
                # defer が失敗した場合、元々の interaction.response.send_message も使えない可能性が高い
                # ここで再度 send_message を試みると InteractionResponded エラーになる可能性が高い
                # そのため、ログに記録するだけに留める。ユーザーにはメッセージが届かない。
                if not interaction.response.is_done(): # 念のため確認
                    logging.warning(f"Failed to send message to user for '{interaction.command.name}' as defer failed and interaction was already acknowledged/timed out.")
                
        else: # interaction.response.is_done() == True の場合 (通常はここには来ないはずだが念のため)
            logging.warning(f"Interaction for '{interaction.command.name}' was already responded to or timed out at command entry. Skipping all response attempts.")


async def setup(bot):
    """Loads the StatusCommands cog into the bot."""
    cog = StatusCommands(bot)
    await bot.add_cog(cog)
    logging.info("StatusCommands cog loaded.")
