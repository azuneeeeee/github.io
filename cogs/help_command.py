import discord
from discord.ext import commands
from discord import app_commands
import logging # ロギングを追加

class HelpCommand(commands.Cog): # クラス名を HelpCommand に修正
    def __init__(self, bot):
        self.bot = bot
        logging.info("HelpCommand cog initialized.") # ロギングを追加

    @app_commands.command(name="help", description="このボットのコマンド一覧を表示します。")
    async def help_command(self, interaction: discord.Interaction):
        logging.info(f"Command '/help' invoked by {interaction.user.name} (ID: {interaction.user.id}).") # ロギングを追加
        
        try:
            await interaction.response.defer(ephemeral=True) # 他のユーザーには見えないように一時的に遅延応答
            logging.info(f"Successfully deferred interaction for '/help'.") # ロギングを追加
        except discord.errors.NotFound:
            logging.error(f"Failed to defer interaction for '/help': Unknown interaction (404 NotFound). This will be caught by global error handler.", exc_info=True)
            return
        except Exception as e:
            logging.error(f"Unexpected error during defer for '/help': {e}", exc_info=True)
            return

        if not self.bot.is_bot_ready:
            logging.warning(f"Bot not ready for command '/help'. User: {interaction.user.name}. Sending 'bot not ready' message via followup.")
            await interaction.followup.send("ボットがまだ起動中です。しばらくお待ちください。", ephemeral=True)
            return

        embed = discord.Embed(
            title="💡 ボットコマンド一覧",
            description="利用可能なスラッシュコマンドです。",
            color=discord.Color.blue()
        )

        # 登録されているスラッシュコマンドをすべて取得し、カテゴリごとに整理
        commands_list = []
        # グローバルコマンドを取得
        for command in self.bot.tree.get_commands():
            commands_list.append(command)

        # 特定のギルドコマンドを取得 (もしあれば)
        # bot.GUILD_ID は MyBot クラスの属性として設定されていることを前提とする
        if hasattr(self.bot, 'GUILD_ID') and self.bot.GUILD_ID != 0:
            guild_obj = discord.Object(id=self.bot.GUILD_ID)
            for command in self.bot.tree.get_commands(guild=guild_obj):
                commands_list.append(command)

        # 重複を避けて表示するためにセットを使用
        unique_commands = {}
        for command in commands_list:
            unique_commands[command.name] = command # 名前が重複する場合は上書きされる（通常は同じコマンド）

        sorted_unique_commands = sorted(unique_commands.values(), key=lambda cmd: cmd.name)

        general_commands_info = []
        rankmatch_commands_info = []
        owner_commands_info = [] # 製作者限定コマンドのリストを追加

        for command in sorted_unique_commands:
            # helpコマンド自体は後で個別に追加するのでスキップ
            if command.name == "help":
                continue

            command_info = f"`/{command.name}`: {command.description}"
            # 製作者限定コマンドの判定 (descriptionに"[製作者限定]"が含まれているか)
            if "[製作者限定]" in command.description:
                owner_commands_info.append(command_info)
            elif command.name.startswith("pjsk_"): # プロセカ関連コマンドのプレフィックス
                general_commands_info.append(command_info)
            elif command.name.startswith("rankmatch_"): # ランクマッチ関連コマンドのプレフィックス
                rankmatch_commands_info.append(command_info)
            else: # その他のコマンド（今回は該当しない可能性が高いが、念のため）
                general_commands_info.append(command_info)


        if general_commands_info:
            embed.add_field(name="📚 プロセカ関連コマンド", value="\n".join(general_commands_info), inline=False)

        if rankmatch_commands_info:
            embed.add_field(name="🏆 ランクマッチ関連コマンド", value="\n".join(rankmatch_commands_info), inline=False)

        if owner_commands_info: # 製作者限定コマンドのフィールドを追加
            embed.add_field(name="👑 製作者限定コマンド", value="\n".join(owner_commands_info), inline=False)

        # ヘルプコマンド自体を追加
        embed.add_field(name="❓ その他", value="`/help`: このヘルプメッセージを表示します。\n`/help [コマンド名]`: 特定のコマンドの詳細を表示します。", inline=False)

        embed.set_footer(text=f"ボット名: {self.bot.user.display_name}")
        await interaction.followup.send(embed=embed, ephemeral=True)
        logging.info(f"Help message sent for user {interaction.user.name}.") # ロギングを追加

async def setup(bot):
    cog = HelpCommand(bot) # クラス名を HelpCommand に修正
    await bot.add_cog(cog)
    logging.info("HelpCommand cog loaded.") # ロギングを追加
