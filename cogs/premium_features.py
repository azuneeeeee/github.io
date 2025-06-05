import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional # Optional をインポート

# ロギング設定 (main.pyで一元管理されるため、ここでは簡易的に)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# プレミアムユーザーデータを保存するファイルパス
PREMIUM_DATA_FILE = "data/premium_users.json"
DATA_DIR = os.path.dirname(PREMIUM_DATA_FILE)

# UTC+9 (日本標準時) のタイムゾーンオフセット
JST = timezone(timedelta(hours=9))

# ★ユーザーが提供したプレミアムロールIDをここに設定
PREMIUM_ROLE_ID = 1380155806485315604 

# pjsk_record_result.py から SUPPORT_GUILD_ID をインポート
# これは、サポートサーバーのIDを指すことを想定しています
try:
    from cogs.pjsk_record_result import SUPPORT_GUILD_ID
except ImportError:
    logging.error("Failed to import SUPPORT_GUILD_ID from cogs.pjsk_record_result. Please ensure pjsk_record_result.py is correctly set up and defines SUPPORT_GUILD_ID.")
    SUPPORT_GUILD_ID = 0 # フォールバック。実際にはmain.pyでbot.GUILD_IDが設定されるはずだが、念のため。


def load_premium_data():
    """プレミアムユーザーデータをJSONファイルからロードします。"""
    if not os.path.exists(PREMIUM_DATA_FILE):
        return {}
    try:
        with open(PREMIUM_DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 日付文字列をdatetimeオブジェクトに変換（存在する場合）
            for user_id, user_info in data.items():
                if 'expiration_date' in user_info and user_info['expiration_date']:
                    try:
                        # UTCで保存されたISOフォーマット文字列をdatetimeオブジェクトに変換
                        user_info['expiration_date'] = datetime.fromisoformat(user_info['expiration_date'])
                    except ValueError:
                        logging.warning(f"Invalid datetime format for user {user_id}: {user_info['expiration_date']}")
                        user_info['expiration_date'] = None # 無効な場合はNoneとする
            return data
    except json.JSONDecodeError:
        logging.warning(f"JSONDecodeError in {PREMIUM_DATA_FILE}. Initializing with empty data.")
        return {}
    except Exception as e:
        logging.error(f"Error loading {PREMIUM_DATA_FILE}: {e}", exc_info=True)
        return {}

def save_premium_data(data):
    """プレミアムユーザーデータをJSONファイルに保存します。"""
    os.makedirs(DATA_DIR, exist_ok=True)
    # datetimeオブジェクトをISOフォーマットの文字列に変換して保存
    serializable_data = {}
    for user_id, user_info in data.items():
        serializable_info = user_info.copy()
        if 'expiration_date' in serializable_info and serializable_info['expiration_date']:
            # UTCで保存するために .astimezone(timezone.utc).isoformat() を使用
            serializable_info['expiration_date'] = serializable_info['expiration_date'].astimezone(timezone.utc).isoformat()
        # expiration_date が None の場合はそのまま None を保存
        elif 'expiration_date' in serializable_info and serializable_info['expiration_date'] is None:
            serializable_info['expiration_date'] = None
        serializable_data[user_id] = serializable_info
    
    with open(PREMIUM_DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(serializable_data, f, ensure_ascii=False, indent=4)

def is_premium_check():
    """
    ユーザーがプレミアムステータスを持っているかをチェックするカスタムデコレータ。
    このチェックは、有効期限が切れていないかも確認します。
    """
    async def predicate(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        premium_users = load_premium_data()
        
        user_info = premium_users.get(user_id)
        if not user_info:
            logging.info(f"User {interaction.user.name} (ID: {user_id}) is not premium.")
            await interaction.response.send_message(
                "この機能はプレミアムユーザー限定です。詳細については `/premium_info` コマンドを使用してください。",
                ephemeral=True
            )
            return False

        expiration_date = user_info.get('expiration_date')
        if not expiration_date:
            logging.info(f"User {interaction.user.name} (ID: {user_id}) is premium (indefinite).")
            return True # expiration_date が None の場合は無期限とみなす

        if expiration_date < datetime.now(JST): # 現在のJST時刻と比較
            logging.info(f"Premium status for user {user_id} expired on {expiration_date.astimezone(JST).strftime('%Y-%m-%d %H:%M:%S JST')}. Revoking automatically.")
            # 期限切れの場合は自動的にプレミアムステータスを削除
            del premium_users[user_id]
            save_premium_data(premium_users)
            await interaction.response.send_message(
                f"あなたのプレミアムステータスは {expiration_date.astimezone(JST).strftime('%Y年%m月%d日 %H時%M分')} に期限切れとなりました。再度購読してください。",
                ephemeral=True
            )
            return False
        
        logging.info(f"User {interaction.user.name} (ID: {user_id}) is premium, expires on {expiration_date.astimezone(JST).strftime('%Y-%m-%d %H:%M:%S JST')}.")
        return True

    return app_commands.check(predicate)

# ★追加: ボットのオーナーをチェックするカスタムデコレータ
def is_bot_owner():
    async def predicate(interaction: discord.Interaction):
        # main.pyで bot.OWNER_ID が設定されていることを前提とします
        if hasattr(interaction.client, 'OWNER_ID') and interaction.user.id == interaction.client.OWNER_ID:
            return True
        await interaction.response.send_message("このコマンドはボットのオーナーのみが実行できます。", ephemeral=True)
        return False
    return app_commands.check(predicate)


class PremiumManagerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # 起動時にデータディレクトリが存在することを確認
        os.makedirs(DATA_DIR, exist_ok=True)
        self.premium_users = load_premium_data() # プレミアムユーザーデータをロード
        logging.info("PremiumManagerCog initialized.")
        logging.info(f"Loaded {len(self.premium_users)} premium users.")

    @app_commands.command(name="premium_info", description="あなたのプレミアムステータスを表示します。")
    async def premium_info(self, interaction: discord.Interaction):
        """ユーザーのプレミアムステータスを表示するコマンド"""
        logging.info(f"Command '/premium_info' invoked by {interaction.user.name} (ID: {interaction.user.id}).")
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        user_info = self.premium_users.get(user_id)

        embed = discord.Embed(title="プレミアムステータス", color=discord.Color.gold())

        if user_info:
            expiration_date = user_info.get('expiration_date')
            if expiration_date:
                # JSTに変換して表示
                expires_at_jst = expiration_date.astimezone(JST)
                if expires_at_jst > datetime.now(JST):
                    embed.description = f"あなたは現在プレミアムユーザーです！\n期限: <t:{int(expires_at_jst.timestamp())}:F>"
                    embed.color = discord.Color.green()
                else:
                    embed.description = f"あなたのプレミアムステータスは期限切れです。\n期限: <t:{int(expires_at_jst.timestamp())}:F>"
                    embed.color = discord.Color.red()
                    # 期限切れの場合は、念のため内部データからも削除する
                    del self.premium_users[user_id]
                    save_premium_data(self.premium_users)
            else:
                embed.description = "あなたは現在プレミアムユーザーです！ (期限なし)"
                embed.color = discord.Color.green()
        else:
            embed.description = "あなたは現在プレミアムユーザーではありません。"
            embed.color = discord.Color.red()

        # ここにウェブサイトへのリンクを追加することも可能
        embed.add_field(
            name="プレミアムプランのご案内", 
            value="より多くの機能を利用するには、当社のウェブサイトでプレミアムプランをご購入ください。\n[ウェブサイトはこちら](https://your-website-url.com/premium)",
            inline=False
        )

        await interaction.followup.send(embed=embed, ephemeral=True)
        logging.info(f"Premium info sent to {interaction.user.name}.")

    @app_commands.command(name="premium_exclusive_command", description="プレミアムユーザー限定のすごい機能！")
    # ★修正: is_premium_check() をコメントアウトし、is_bot_owner() を追加
    # @is_premium_check() 
    @is_bot_owner() 
    async def premium_exclusive_command(self, interaction: discord.Interaction):
        """プレミアムユーザーのみが利用できるコマンドの例"""
        logging.info(f"Command '/premium_exclusive_command' invoked by {interaction.user.name} (ID: {interaction.user.id}).")
        await interaction.response.defer(ephemeral=False)
        
        # 実際にプレミアム機能の処理を行う
        embed = discord.Embed(
            title="✨ プレミアム機能へようこそ！ ✨",
            description=f"おめでとうございます、{interaction.user.display_name}さん！\nこれはプレミアムユーザーだけが使える特別な機能です。",
            color=discord.Color.blue()
        )
        embed.add_field(name="機能", value="より詳細な統計データや、限定の選曲オプションなどが利用できます！", inline=False)
        await interaction.followup.send(embed=embed)
        logging.info(f"Premium exclusive command executed for {interaction.user.name}.")

    @app_commands.command(name="grant_premium", description="指定ユーザーのIDにプレミアムステータスを付与します (オーナー限定)。")
    @app_commands.default_permissions(manage_roles=True)
    @is_bot_owner() 
    @app_commands.guilds(discord.Object(id=SUPPORT_GUILD_ID))
    async def grant_premium(self, interaction: discord.Interaction, 
                            user_id: str, # ユーザーIDは必須
                            days: Optional[app_commands.Range[int, 1, 365]] = None): # ★修正: days を Optional[int] に変更し、デフォルト値を None に設定
        """ボットのオーナーがユーザーにプレミアムステータスを付与するためのコマンド"""
        logging.info(f"Command '/grant_premium' invoked by {interaction.user.name} (ID: {interaction.user.id}) for user ID {user_id}. Days: {days}")
        await interaction.response.defer(ephemeral=True)

        try:
            # ユーザーIDが数値であることを確認
            target_user_id = int(user_id)
        except ValueError:
            await interaction.followup.send("無効なユーザーIDです。有効なDiscordユーザーID (数字のみ) を入力してください。", ephemeral=True)
            return

        # Discord APIからユーザーオブジェクトを取得 (サーバーにいるかどうかに関わらず)
        target_user = self.bot.get_user(target_user_id) # get_userはキャッシュから取得、fetch_userはAPIリクエスト
        if target_user is None:
            # キャッシュにない場合はAPIからフェッチを試みる
            try:
                target_user = await self.bot.fetch_user(target_user_id)
            except discord.NotFound:
                await interaction.followup.send(f"Discord上でID `{target_user_id}` のユーザーが見つかりませんでした。無効なIDの可能性があります。", ephemeral=True)
                logging.warning(f"User ID {target_user_id} not found via fetch_user.")
                return
            except discord.HTTPException as e:
                await interaction.followup.send(f"ユーザー情報の取得中にエラーが発生しました: {e.status}", ephemeral=True)
                logging.error(f"HTTPException when fetching user {target_user_id}: {e}", exc_info=True)
                return
            
        # 現在のUTC時刻を基準に有効期限を設定
        expiration_date = None
        if days is not None:
            expiration_date = datetime.now(timezone.utc) + timedelta(days=days)

        self.premium_users[user_id] = { # user_id (文字列) をキーとして保存
            "username": target_user.name, # 取得したユーザーオブジェクトから情報を取得
            "discriminator": target_user.discriminator,
            "display_name": target_user.display_name,
            "expiration_date": expiration_date # datetimeオブジェクトとして保存 (None の可能性あり)
        }
        save_premium_data(self.premium_users)

        status_message = f"{target_user.display_name} (ID: `{target_user.id}`) にプレミアムステータスを付与しました。"

        # ロール付与の処理 (サーバーにいるメンバーの場合のみ)
        target_guild = interaction.guild
        if target_guild:
            # ターゲットユーザーがこのサーバーのメンバーであるか確認
            member = target_guild.get_member(target_user.id)
            if member: # メンバーとして存在する場合
                premium_role = target_guild.get_role(PREMIUM_ROLE_ID) 
                if premium_role:
                    try:
                        await member.add_roles(premium_role)
                        status_message += f"\nまた、サーバー内で `{premium_role.name}` ロールを付与しました。"
                        logging.info(f"Added role {premium_role.name} to {member.name} in guild {target_guild.name}.")
                    except discord.Forbidden:
                        status_message += f"\nしかし、ボットに `{premium_role.name}` ロールを付与する権限がありませんでした。ボットのロールがプレミアムロールより上位にあるか確認してください。"
                        logging.error(f"Bot lacks permissions to assign role {premium_role.name} to {member.name}.")
                    except Exception as e:
                        status_message += f"\nしかし、ロール付与中にエラーが発生しました: {e}"
                        logging.error(f"Error adding role to member {member.name}: {e}", exc_info=True)
                else:
                    status_message += f"\nしかし、プレミアムロール (ID: `{PREMIUM_ROLE_ID}`) がこのサーバーで見つかりませんでした。"
                    logging.warning(f"Premium role (ID: {PREMIUM_ROLE_ID}) not found in guild {target_guild.name}.")
            else:
                status_message += f"\nターゲットユーザーは現在このサーバーにいません。ユーザーがサーバーに参加した際に手動でロールを付与するか、別途自動化を検討してください。"
                logging.info(f"Target user {target_user.name} (ID: {target_user.id}) is not a member of guild {target_guild.name}.")
        else:
            status_message += f"\nこのコマンドはDMでは実行できません。ロール操作はサーバー内でのみ可能です。"
            logging.warning("grant_premium command invoked in DM. Role operation skipped.")


        embed = discord.Embed(
            title="✅ プレミアムステータス付与",
            description=status_message,
            color=discord.Color.green()
        )
        if expiration_date: # 期限がある場合のみ表示
            expires_at_jst = expiration_date.astimezone(JST)
            embed.add_field(name="期限", value=f"<t:{int(expires_at_jst.timestamp())}:F>", inline=False)
        else: # 期限がない場合
            embed.add_field(name="期限", value="無期限", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
        logging.info(f"Premium status granted to user ID {user_id} by {interaction.user.name}. Details: {status_message}")


    @app_commands.command(name="revoke_premium", description="指定ユーザーのIDからプレミアムステータスを剥奪します (オーナー限定)。")
    @app_commands.default_permissions(manage_roles=True)
    @is_bot_owner()
    @app_commands.guilds(discord.Object(id=SUPPORT_GUILD_ID))
    async def revoke_premium(self, interaction: discord.Interaction, 
                             user_id: str): # ★変更: discord.Member から str (ユーザーID) に変更
        """ボットのオーナーがユーザーからプレミアムステータスを剥奪するためのコマンド"""
        logging.info(f"Command '/revoke_premium' invoked by {interaction.user.name} (ID: {interaction.user.id}) for user ID {user_id}.")
        
        # defer を最速で試みる
        try:
            await interaction.response.defer(ephemeral=True)
            logging.info(f"Successfully deferred interaction for '{interaction.command.name}'.")
        except discord.errors.NotFound:
            logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound). This will be caught by global error handler.", exc_info=True)
            # deferに失敗した場合は、これ以上処理を進めない
            return
        except Exception as e:
            logging.error(f"Unexpected error during defer for '{interaction.command.name}': {e}", exc_info=True)
            # deferに失敗した場合は、これ以上処理を進めない
            return

        try:
            target_user_id = int(user_id)
        except ValueError:
            await interaction.followup.send("無効なユーザーIDです。有効なDiscordユーザーID (数字のみ) を入力してください。", ephemeral=True)
            return

        status_message = ""
        if user_id in self.premium_users:
            user_info_from_data = self.premium_users.get(user_id)
            display_name = user_info_from_data.get("display_name", f"不明なユーザー (ID: `{user_id}`)") 
            
            del self.premium_users[user_id]
            save_premium_data(self.premium_users)
            status_message = f"{display_name} からプレミアムステータスを剥奪しました。"

            # Discord APIからユーザーオブジェクトを取得 (サーバーにいるかどうかに関わらず)
            target_user = self.bot.get_user(target_user_id)
            if target_user is None:
                try:
                    target_user = await self.bot.fetch_user(target_user_id)
                except discord.NotFound:
                    logging.warning(f"User ID {target_user_id} not found via fetch_user for role removal.")
                    target_user = None 
                except discord.HTTPException as e:
                    logging.error(f"HTTPException when fetching user {target_user_id} for role removal: {e}", exc_info=True)
                    target_user = None
            
            # ロール剥奪の処理 (サーバーにいるメンバーの場合のみ)
            target_guild = interaction.guild
            if target_guild and target_user: 
                member = target_guild.get_member(target_user.id)
                if member: 
                    premium_role = target_guild.get_role(PREMIUM_ROLE_ID) 
                    if premium_role:
                        try:
                            await member.remove_roles(premium_role)
                            status_message += f"\nまた、サーバー内で `{premium_role.name}` ロールを剥奪しました。"
                            logging.info(f"Removed role {premium_role.name} from {member.name} in guild {target_guild.name}.")
                        except discord.Forbidden:
                            status_message += f"\nしかし、ボットに `{premium_role.name}` ロールを剥奪する権限がありませんでした。"
                            logging.error(f"Bot lacks permissions to remove role {premium_role.name} from {member.name}.")
                        except Exception as e:
                            status_message += f"\nしかし、ロール剥奪中にエラーが発生しました: {e}"
                            logging.error(f"Error removing role from member {member.name}: {e}", exc_info=True)
                    else:
                        status_message += f"\nしかし、プレミアムロール (ID: `{PREMIUM_ROLE_ID}`) がこのサーバーで見つかりませんでした。"
                        logging.warning(f"Premium role (ID: {PREMIUM_ROLE_ID}) not found in guild {target_guild.name}.")
                else:
                    status_message += f"\nターゲットユーザーは現在このサーバーにいませんでした。ロール剥奪はスキップされました。"
                    logging.info(f"Target user {target_user.name} (ID: {target_user.id}) is not a member of guild {target_guild.name}. Role removal skipped.")
            elif not target_guild:
                status_message += f"\nこのコマンドはDMでは実行できません。ロール操作はサーバー内でのみ可能です。"
                logging.warning("revoke_premium command invoked in DM. Role operation skipped.")
            else: 
                 status_message += f"\nユーザーオブジェクトが取得できなかったため、ロール操作はスキップされました。"
                 logging.warning(f"Could not fetch target user {target_user_id} for role removal. Role operation skipped.")
        else:
            display_name = f"不明なユーザー (ID: `{user_id}`)" 
            status_message = f"{display_name} はプレミアムユーザーではありません。"
            logging.info(f"User ID {user_id} does not have premium status to revoke.")

        embed = discord.Embed(
            title="✅ プレミアムステータス剥奪",
            description=status_message,
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        logging.info(f"Premium status revoked for user ID {user_id} by {interaction.user.name}. Details: {status_message}")

async def setup(bot):
    cog = PremiumManagerCog(bot)
    await bot.add_cog(cog)
    logging.info("PremiumManagerCog loaded.")
