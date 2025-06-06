import discord
from discord.ext import commands
from discord import app_commands # スラッシュコマンドを使用するため
import logging
from typing import Optional

# main.py からグローバルな is_bot_owner 関数をインポート
# ボットの楽曲データなどは bot.proseka_songs_data からアクセスするため、直接インポートは不要
from main import is_bot_owner

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class StatusCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        logging.info("StatusCommands Cog initialized.")

    @app_commands.command(name="set_status", description="ボットのステータスを設定します (オーナー限定)。")
    @app_commands.default_permissions(administrator=True) # 管理者権限が必要なことを示唆
    @is_bot_owner() # オーナー限定
    @app_commands.choices(
        status=[
            app_commands.Choice(name="オンライン", value="online"), # オンラインを選択肢として追加
            app_commands.Choice(name="取り込み中", value="dnd") # 取り込み中を選択肢として追加
        ]
    )
    async def set_status(self, 
                         interaction: discord.Interaction, 
                         status: str): 
        
        logging.info(f"Command '/set_status' invoked by {interaction.user.name} (ID: {interaction.user.id}). Status: {status}")
        
        # タイムアウトを防ぐため、最初にdeferを呼び出す
        try:
            await interaction.response.defer(ephemeral=True) 
            logging.info(f"Successfully deferred interaction for '{interaction.command.name}'.")
        except discord.errors.NotFound:
            logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound). Interaction might have timed out before defer.", exc_info=True)
            # defer に失敗した場合は、後続のfollowup.send も失敗するのでここで終了
            return
        except Exception as e:
            logging.error(f"Unexpected error during defer for '{interaction.command.name}': {e}", exc_info=True)
            return

        discord_status = {
            "online": discord.Status.online,
            "dnd": discord.Status.dnd
        }.get(status)

        if not discord_status:
            # defer しているので followup を使う
            await interaction.followup.send("無効なステータスが指定されました。", ephemeral=True)
            return

        activity = None
        if discord_status == discord.Status.dnd:
            # 取り込み中の場合は固定のカスタムステータス
            activity = discord.CustomActivity(name="現在は使用できません。")
        else:
            # オンラインの場合は on_ready で設定されるカスタムステータスを再設定
            # botインスタンスから楽曲データなどにアクセス
            total_songs = len(self.bot.proseka_songs_data)
            total_charts = 0
            for song in self.bot.proseka_songs_data:
                total_charts += sum(1 for diff in self.bot.valid_difficulties_data if diff.lower() in song and song[diff.lower()] is not None)
            activity_message = f"{total_songs}曲/{total_charts}譜面が登録済み"
            activity = discord.CustomActivity(name=activity_message)

        try:
            await self.bot.change_presence(status=discord_status, activity=activity)
            embed = discord.Embed(
                title="✅ ボットステータス更新",
                description=f"ボットのステータスを `{status}` に変更しました。",
                color=discord.Color.green()
            )
            if activity:
                embed.add_field(name="アクティビティ", value=f"カスタムステータス: `{activity.name}`", inline=False)
            
            # defer しているので followup を使う
            await interaction.followup.send(embed=embed, ephemeral=True)
            logging.info(f"Bot presence updated to Status: {status}, Activity: {activity.name if activity else 'None'}.")

        except Exception as e:
            logging.error(f"Failed to change bot presence: {e}", exc_info=True)
            # defer しているので followup を使う
            await interaction.followup.send(f"ステータスの変更に失敗しました: {e}", ephemeral=True)


async def setup(bot):
    logging.info("Entering StatusCommands setup function.")
    cog = StatusCommands(bot)
    await bot.add_cog(cog)
    logging.info("StatusCommands Cog added to bot.")

    # コグが追加された直後に、bot.treeにコマンドが追加されているか確認
    # この時点ではまだグローバル同期は行われていないため、bot.treeの内部状態を見る
    global_commands_in_tree = bot.tree.get_commands(guild=None)
    status_command_found = any(cmd.name == "set_status" for cmd in global_commands_in_tree)
    logging.info(f"DEBUG: After StatusCommands setup, 'set_status' in bot.tree (global): {status_command_found}")
    logging.info(f"DEBUG: All global commands in bot.tree after StatusCommands setup: {[cmd.name for cmd in global_commands_in_tree]}")

    logging.info("StatusCommands Cog loaded.")

