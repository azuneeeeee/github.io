# admin_commands.py

import discord
from discord.ext import commands
from discord import SlashCommandGroup # <-- この行を追加！
# または from discord.commands import slash_command, SlashCommandGroup # <-- どちらでもOK

# ... (中略) ...

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- 製作者専用コマンド群 ---

    # @commands.slash_command の代わりに @SlashCommandGroup.slash_command を使うか、
    # あるいは直接 @discord.slash_command を使う

    @discord.slash_command(name="set_owner", description="ボットの製作者IDを設定します (初回のみ)。") # <-- ここを修正
    @commands.is_owner()
    async def set_owner(self, ctx, user_id: str):
        global OWNER_ID
        try:
            OWNER_ID = int(user_id)
            await ctx.respond(f"ボットの製作者IDを `{OWNER_ID}` に設定しました。")
            print(f"製作者IDが {OWNER_ID} に設定されました。")
        except ValueError:
            await ctx.respond("無効なユーザーIDです。半角数字で入力してください。")
        except Exception as e:
            await ctx.respond(f"エラーが発生しました: {e}")

    @discord.slash_command(name="owner_status", description="現在の製作者IDを表示します。") # <-- ここを修正
    @is_owner()
    async def owner_status(self, ctx):
        if OWNER_ID:
            owner_user = self.bot.get_user(OWNER_ID)
            if owner_user:
                await ctx.respond(f"現在のボットの製作者は `{owner_user.name} ({OWNER_ID})` です。")
            else:
                await ctx.respond(f"現在のボットの製作者IDは `{OWNER_ID}` ですが、ユーザー情報を取得できませんでした。")
        else:
            await ctx.respond("現在、ボットの製作者IDは設定されていません。")

    @discord.slash_command(name="toggle_maintenance", description="ボットのメンテナンスモードを切り替えます。") # <-- ここを修正
    @is_owner()
    async def toggle_maintenance(self, ctx):
        global is_maintenance_mode
        is_maintenance_mode = not is_maintenance_mode
        status = "オン" if is_maintenance_mode else "オフ"
        await ctx.respond(f"メンテナンスモードを **{status}** に切り替えました。")
        print(f"メンテナンスモードが {status} に切り替わりました。")

        if is_maintenance_mode:
            await self.bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
        else:
            await self.bot.change_presence(activity=discord.Game(name="プロセカ！ | !help_proseka"))

    @discord.slash_command(name="maintenance_status", description="現在のメンテナンスモードの状態を表示します。") # <-- ここを修正
    @is_owner()
    async def maintenance_status(self, ctx):
        status = "オン" if is_maintenance_mode else "オフ"
        await ctx.respond(f"現在のメンテナンスモードは **{status}** です。")

def setup(bot):
    bot.add_cog(AdminCommands(bot))