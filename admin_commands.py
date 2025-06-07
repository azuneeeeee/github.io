import discord
from discord.ext import commands
import discord.app_commands # <-- ここが重要！ discord.app_commands をインポート

# ボットの製作者IDを格納する変数
OWNER_ID = None # main.py からも参照される

# 取り込み中モードの状態を管理する変数
is_maintenance_mode = False # main.py からも参照される

# 製作者のみがコマンドを使えるようにするチェック関数（app_commands 用に修正）
def is_owner():
    async def predicate(interaction: discord.Interaction): # <-- interaction を受け取る
        if OWNER_ID is None:
            await interaction.response.send_message("エラー: ボットの製作者IDが設定されていません。", ephemeral=True)
            return False
        if interaction.user.id != OWNER_ID: # <-- interaction.user.id でユーザーIDを取得
            await interaction.response.send_message("あなたはボットの製作者ではありません。このコマンドは使用できません。", ephemeral=True)
            return False
        return True
    return discord.app_commands.check(predicate) # <-- discord.app_commands.check を使用

# 取り込み中モード中に特定のコマンドを制限するチェック関数（app_commands 用に修正）
def not_in_maintenance():
    async def predicate(interaction: discord.Interaction): # <-- interaction を受け取る
        if is_maintenance_mode and interaction.user.id != OWNER_ID: # <-- interaction.user.id でユーザーIDを取得
            await interaction.response.send_message("現在ボットはメンテナンス中のため、このコマンドは使用できません。", ephemeral=True)
            return False
        return True
    return discord.app_commands.check(predicate) # <-- discord.app_commands.check を使用


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- 製作者専用コマンド群 ---

    # スラッシュコマンドは discord.app_commands.command を使用
    @discord.app_commands.command(name="set_owner", description="ボットの製作者IDを設定します (初回のみ)。")
    @is_owner() # <-- 修正したチェック関数を適用
    async def set_owner(self, interaction: discord.Interaction, user_id: str): # <-- ctx の代わりに interaction を使う
        global OWNER_ID
        try:
            OWNER_ID = int(user_id)
            await interaction.response.send_message(f"ボットの製作者IDを `{OWNER_ID}` に設定しました。", ephemeral=True) # <-- 応答方法を変更
            print(f"製作者IDが {OWNER_ID} に設定されました。")
        except ValueError:
            await interaction.response.send_message("無効なユーザーIDです。半角数字で入力してください。", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)

    @discord.app_commands.command(name="owner_status", description="現在の製作者IDを表示します。")
    @is_owner() # <-- 修正したチェック関数を適用
    async def owner_status(self, interaction: discord.Interaction): # <-- ctx の代わりに interaction を使う
        if OWNER_ID:
            owner_user = self.bot.get_user(OWNER_ID)
            if owner_user:
                await interaction.response.send_message(f"現在のボットの製作者は `{owner_user.name} ({OWNER_ID})` です。", ephemeral=True)
            else:
                await interaction.response.send_message(f"現在のボットの製作者IDは `{OWNER_ID}` ですが、ユーザー情報を取得できませんでした。", ephemeral=True)
        else:
            await interaction.response.send_message("現在、ボットの製作者IDは設定されていません。", ephemeral=True)

    @discord.app_commands.command(name="toggle_maintenance", description="ボットのメンテナンスモードを切り替えます。")
    @is_owner() # <-- 修正したチェック関数を適用
    async def toggle_maintenance(self, interaction: discord.Interaction): # <-- ctx の代わりに interaction を使う
        global is_maintenance_mode
        is_maintenance_mode = not is_maintenance_mode
        status = "オン" if is_maintenance_mode else "オフ"
        await interaction.response.send_message(f"メンテナンスモードを **{status}** に切り替えました。", ephemeral=True)
        print(f"メンテナンスモードが {status} に切り替わりました。")

        if is_maintenance_mode:
            await self.bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
        else:
            await self.bot.change_presence(activity=discord.Game(name="プロセカ！ | !help_proseka"))

    @discord.app_commands.command(name="maintenance_status", description="現在のメンテナンスモードの状態を表示します。")
    @is_owner() # <-- 修正したチェック関数を適用
    async def maintenance_status(self, interaction: discord.Interaction): # <-- ctx の代わりに interaction を使う
        status = "オン" if is_maintenance_mode else "オフ"
        await interaction.response.send_message(f"現在のメンテナンスモードは **{status}** です。", ephemeral=True)

def setup(bot):
    bot.add_cog(AdminCommands(bot))
