import discord
from discord.ext import commands
from discord import app_commands

class HelpCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="このボットのコマンド一覧を表示します。")
    async def help_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True) # 他のユーザーには見えないように一時的に遅延応答

        embed = discord.Embed(
            title="💡 ボットコマンド一覧",
            description="利用可能なスラッシュコマンドです。",
            color=discord.Color.blue()
        )

        # 登録されているスラッシュコマンドをすべて取得し、カテゴリごとに整理
        commands_list = []
        # グローバルコマンドとギルドコマンドの両方を取得を試みる
        # bot.tree.get_commands() はグローバルと同期済みのギルドコマンドを返す
        for command in self.bot.tree.get_commands():
            commands_list.append(command)

        # コマンドをアルファベット順にソート (分かりやすくするため)
        commands_list.sort(key=lambda cmd: cmd.name)

        general_commands_info = []
        rankmatch_commands_info = []
        owner_commands_info = [] # 製作者限定コマンドのリストを追加

        for command in commands_list:
            # helpコマンド自体は後で個別に追加するのでスキップ
            if command.name == "help":
                continue

            command_info = f"`/{command.name}`: {command.description}"
            # 製作者限定コマンドの判定 (descriptionに"[製作者限定]"が含まれているか)
            if "[製作者限定]" in command.description:
                owner_commands_info.append(command_info)
            elif command.name.startswith("pjsk_"):
                general_commands_info.append(command_info)
            elif command.name.startswith("rankmatch_"):
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
        embed.add_field(name="❓ その他", value="`/help`: このヘルプメッセージを表示します。", inline=False)

        embed.set_footer(text=f"ボット名: {self.bot.user.display_name}")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(HelpCommands(bot))
    print("HelpCommands cog loaded.")