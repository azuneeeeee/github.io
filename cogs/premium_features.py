import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

# HTTPリクエストを行うためのライブラリをインポート
import requests 

# ロギング設定
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# UTC+9 (日本標準時) のタイムゾーンオフセット
JST = timezone(timedelta(hours=9))

# ★ユーザーが提供したプレミアムロールIDをここに設定
PREMIUM_ROLE_ID = 1380155806485315604 

# pjsk_record_result.py から SUPPORT_GUILD_ID をインポート
try:
    from cogs.pjsk_record_result import SUPPORT_GUILD_ID
except ImportError:
    logging.error("Failed to import SUPPORT_GUILD_ID from cogs.pjsk_record_result. Please ensure pjsk_record_result.py is correctly set up and defines SUPPORT_GUILD_ID.")
    SUPPORT_GUILD_ID = 0

# --- JSONBin.io 関連の設定とヘルパー関数 ---
JSONBIN_API_KEY = os.getenv('JSONBIN_API_KEY')
JSONBIN_BIN_ID = os.getenv('JSONBIN_BIN_ID')
JSONBIN_BASE_URL = "https://api.jsonbin.io/v3/b"

if not JSONBIN_API_KEY or not JSONBIN_BIN_ID:
    logging.critical("JSONBIN_API_KEY or JSONBIN_BIN_ID environment variables are not set. Data will not be persistent. Please configure JSONBin.io.")

async def load_premium_data_from_jsonbin():
    """JSONBin.io からプレミアムユーザーデータをロードします。"""
    if not JSONBIN_API_KEY or not JSONBIN_BIN_ID:
        logging.error("JSONBin API key or Bin ID not set. Cannot load data from JSONBin.io.")
        return {}

    headers = {
        'X-Master-Key': JSONBIN_API_KEY,
        'X-Bin-Meta': 'false' # メタデータを含めない
    }
    url = f"{JSONBIN_BASE_URL}/{JSONBIN_BIN_ID}/latest" # 最新バージョンを取得

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.get(url, headers=headers))
        response.raise_for_status() # HTTPエラーがあれば例外を発生させる
        
        data = response.json()
        premium_users = {}
        for user_id, user_info in data.items():
            # 日付文字列をdatetimeオブジェクトに変換（存在する場合）
            if 'expiration_date' in user_info and user_info['expiration_date']:
                try:
                    # ISOフォーマット文字列をdatetimeオブジェクトに変換
                    user_info['expiration_date'] = datetime.fromisoformat(user_info['expiration_date']).astimezone(timezone.utc)
                except ValueError:
                    logging.warning(f"Invalid datetime format for user {user_id} in JSONBin: {user_info['expiration_date']}")
                    user_info['expiration_date'] = None
            premium_users[user_id] = user_info
            
        logging.info(f"Loaded {len(premium_users)} premium users from JSONBin.io.")
        return premium_users
    except requests.exceptions.RequestException as e:
        logging.error(f"Error loading premium data from JSONBin.io: {e}", exc_info=True)
        # Binが存在しない、またはアクセス権がない場合は空のデータを返す
        if response.status_code == 404: # Binが見つからない場合
            logging.warning("JSONBin.io bin not found or incorrect ID. Starting with empty data.")
        elif response.status_code == 401: # 認証エラー
            logging.error("JSONBin.io API key is unauthorized. Check your X-Master-Key.")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON from JSONBin.io: {e}", exc_info=True)
        return {}
    except Exception as e:
        logging.error(f"An unexpected error occurred during JSONBin.io data loading: {e}", exc_info=True)
        return {}

async def save_premium_data_to_jsonbin(data: dict):
    """JSONBin.io にプレミアムユーザーデータを保存（更新）します。"""
    if not JSONBIN_API_KEY or not JSONBIN_BIN_ID:
        logging.error("JSONBin API key or Bin ID not set. Cannot save data to JSONBin.io.")
        return

    headers = {
        'Content-Type': 'application/json',
        'X-Master-Key': JSONBIN_API_KEY
    }
    url = f"{JSONBIN_BASE_URL}/{JSONBIN_BIN_ID}"

    # datetimeオブジェクトをISOフォーマットの文字列に変換して保存
    serializable_data = {}
    for user_id, user_info in data.items():
        serializable_info = user_info.copy()
        if 'expiration_date' in serializable_info and serializable_info['expiration_date']:
            serializable_info['expiration_date'] = serializable_info['expiration_date'].isoformat()
        serializable_data[user_id] = serializable_info

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.put(url, headers=headers, json=serializable_data))
        response.raise_for_status() # HTTPエラーがあれば例外を発生させる
        logging.info(f"Premium data saved/updated in JSONBin.io. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error saving premium data to JSONBin.io: {e}", exc_info=True)
        if response.status_code == 401:
            logging.error("JSONBin.io API key is unauthorized. Check your X-Master-Key for PUT requests.")
        elif response.status_code == 403: # Forbidden, often due to master key not having write access
            logging.error("JSONBin.io API key does not have write access. Ensure it's a Master Key.")
    except Exception as e:
        logging.error(f"An unexpected error occurred during JSONBin.io data saving: {e}", exc_info=True)

# --- is_premium_check, is_bot_owner 関数 (JSONBin.io対応のため変更) ---
def is_premium_check():
    """
    ユーザーがプレミアムステータスを持っているかをチェックするカスタムデコレータ。
    このチェックは、有効期限が切れていないかも確認します。
    """
    async def predicate(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        premium_users = await load_premium_data_from_jsonbin() # JSONBin.ioからロード
        
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
            # 期限切れの場合は自動的にプレミアムステータスをJSONBin.ioからも削除
            premium_users.pop(user_id, None) # 内部データから削除
            await save_premium_data_to_jsonbin(premium_users) # JSONBin.ioを更新
            await interaction.response.send_message(
                f"あなたのプレミアムステータスは {expiration_date.astimezone(JST).strftime('%Y年%m月%d日 %H時%M分')} に期限切れとなりました。再度購読してください。",
                ephemeral=True
            )
            return False
        
        logging.info(f"User {interaction.user.name} (ID: {user_id}) is premium, expires on {expiration_date.astimezone(JST).strftime('%Y-%m-%d %H:%M:%S JST')}.")
        return True

    return app_commands.check(predicate)

def is_bot_owner():
    """ボットのオーナーをチェックするカスタムデコレータ。"""
    async def predicate(interaction: discord.Interaction):
        if hasattr(interaction.client, 'OWNER_ID') and interaction.user.id == interaction.client.OWNER_ID:
            return True
        await interaction.response.send_message("このコマンドはボットのオーナーのみが実行できます。", ephemeral=True)
        return False
    return app_commands.check(predicate)


class PremiumManagerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # JSONBin.io からデータは on_ready でロードされる
        self.premium_users = {} 
        logging.info("PremiumManagerCog initialized.")

    @commands.Cog.listener()
    async def on_ready(self):
        """ボットが完全に起動し、Discordに接続された後に実行されます。"""
        # JSONBin.io からデータをロード
        self.premium_users = await load_premium_data_from_jsonbin()
        logging.info(f"Loaded {len(self.premium_users)} premium users from JSONBin.io during on_ready.")


    @app_commands.command(name="premium_info", description="あなたのプレミアムステータスを表示します。")
    async def premium_info(self, interaction: discord.Interaction):
        """ユーザーのプレミアムステータスを表示するコマンド"""
        logging.info(f"Command '/premium_info' invoked by {interaction.user.name} (ID: {interaction.user.id}).")
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        # コマンド実行時に常に最新データをJSONBin.ioからロードして確認
        self.premium_users = await load_premium_data_from_jsonbin() 
        user_info = self.premium_users.get(user_id)

        embed = discord.Embed(title="プレミアムステータス", color=discord.Color.gold())

        if user_info:
            expiration_date = user_info.get('expiration_date')
            if expiration_date:
                expires_at_jst = expiration_date.astimezone(JST)
                if expires_at_jst > datetime.now(JST):
                    embed.description = f"あなたは現在プレミアムユーザーです！\n期限: <t:{int(expires_at_jst.timestamp())}:F>"
                    embed.color = discord.Color.green()
                else:
                    embed.description = f"あなたのプレミアムステータスは期限切れです。\n期限: <t:{int(expires_at_jst.timestamp())}:F>"
                    embed.color = discord.Color.red()
                    # 期限切れの場合は、念のためJSONBin.ioからも削除する
                    if user_id in self.premium_users:
                        self.premium_users.pop(user_id) # 内部データから削除
                        await save_premium_data_to_jsonbin(self.premium_users) # JSONBin.ioを更新
            else:
                embed.description = "あなたは現在プレミアムユーザーです！ (期限なし)"
                embed.color = discord.Color.green()
        else:
            embed.description = "あなたは現在プレミアムユーザーではありません。"
            embed.color = discord.Color.red()

        embed.add_field(
            name="プレミアムプランのご案内", 
            value="より多くの機能を利用するには、当社のウェブサイトでプレミアムプランをご購入ください。\n[ウェブサイトはこちら](https://your-website-url.com/premium)",
            inline=False
        )

        await interaction.followup.send(embed=embed, ephemeral=True)
        logging.info(f"Premium info sent to {interaction.user.name}.")

    @app_commands.command(name="premium_exclusive_command", description="プレミアムユーザー限定のすごい機能！")
    @is_bot_owner() # 開発中はオーナー限定 (本番運用時は @is_premium_check() に戻す)
    async def premium_exclusive_command(self, interaction: discord.Interaction):
        """プレミアムユーザーのみが利用できるコマンドの例"""
        logging.info(f"Command '/premium_exclusive_command' invoked by {interaction.user.name} (ID: {interaction.user.id}).")
        await interaction.response.defer(ephemeral=False)
        
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
                            days: Optional[app_commands.Range[int, 1, 365]] = None): # Optional で無期限も可能に
        """ボットのオーナーがユーザーにプレミアムステータスを付与するためのコマンド"""
        logging.info(f"Command '/grant_premium' invoked by {interaction.user.name} (ID: {interaction.user.id}) for user ID {user_id}. Days: {days}")
        
        try:
            await interaction.response.defer(ephemeral=True)
            logging.info(f"Successfully deferred interaction for '{interaction.command.name}'.")
        except discord.errors.NotFound:
            logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound).", exc_info=True)
            return
        except Exception as e:
            logging.error(f"Unexpected error during defer for '{interaction.command.name}': {e}", exc_info=True)
            return

        try:
            target_user_id = int(user_id)
        except ValueError:
            await interaction.followup.send("無効なユーザーIDです。有効なDiscordユーザーID (数字のみ) を入力してください。", ephemeral=True)
            return

        target_user = self.bot.get_user(target_user_id) # キャッシュから取得
        if target_user is None:
            try:
                target_user = await self.bot.fetch_user(target_user_id) # APIからフェッチ
            except discord.NotFound:
                await interaction.followup.send(f"Discord上でID `{target_user_id}` のユーザーが見つかりませんでした。無効なIDの可能性があります。", ephemeral=True)
                logging.warning(f"User ID {target_user_id} not found via fetch_user.")
                return
            except discord.HTTPException as e:
                await interaction.followup.send(f"ユーザー情報の取得中にエラーが発生しました: {e.status}", ephemeral=True)
                logging.error(f"HTTPException when fetching user {target_user_id}: {e}", exc_info=True)
                return
            
        expiration_date = None
        if days is not None:
            expiration_date = datetime.now(timezone.utc) + timedelta(days=days)

        # 現在の全プレミアムユーザーデータをロードし、更新してから保存
        self.premium_users = await load_premium_data_from_jsonbin()
        self.premium_users[user_id] = { # 内部データ構造を更新
            "username": target_user.name, 
            "discriminator": target_user.discriminator,
            "display_name": target_user.display_name,
            "expiration_date": expiration_date # datetimeオブジェクト (None の可能性あり)
        }
        await save_premium_data_to_jsonbin(self.premium_users) # JSONBin.io に保存

        status_message = f"{target_user.display_name} (ID: `{target_user.id}`) にプレミアムステータスを付与しました。"

        target_guild = interaction.guild
        if target_guild:
            member = target_guild.get_member(target_user.id)
            if member: 
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
        if expiration_date: 
            expires_at_jst = expiration_date.astimezone(JST)
            embed.add_field(name="期限", value=f"<t:{int(expires_at_jst.timestamp())}:F>", inline=False)
        else: 
            embed.add_field(name="期限", value="無期限", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
        logging.info(f"Premium status granted to user ID {user_id} by {interaction.user.name}. Details: {status_message}")


    @app_commands.command(name="revoke_premium", description="指定ユーザーのIDからプレミアムステータスを剥奪します (オーナー限定)。")
    @app_commands.default_permissions(manage_roles=True)
    @is_bot_owner()
    @app_commands.guilds(discord.Object(id=SUPPORT_GUILD_ID))
    async def revoke_premium(self, interaction: discord.Interaction, 
                             user_id: str): 
        """ボットのオーナーがユーザーからプレミアムステータスを剥奪するためのコマンド"""
        logging.info(f"Command '/revoke_premium' invoked by {interaction.user.name} (ID: {interaction.user.id}) for user ID {user_id}.")
        
        try:
            await interaction.response.defer(ephemeral=True)
            logging.info(f"Successfully deferred interaction for '{interaction.command.name}'.")
        except discord.errors.NotFound:
            logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound).", exc_info=True)
            return
        except Exception as e:
            logging.error(f"Unexpected error during defer for '{interaction.command.name}': {e}", exc_info=True)
            return

        try:
            target_user_id = int(user_id)
        except ValueError:
            await interaction.followup.send("無効なユーザーIDです。有効なDiscordユーザーID (数字のみ) を入力してください。", ephemeral=True)
            return

        status_message = ""
        # コマンド実行時に常に最新データをJSONBin.ioからロード
        self.premium_users = await load_premium_data_from_jsonbin() 
        
        if user_id in self.premium_users:
            user_info_from_data = self.premium_users.get(user_id)
            display_name = user_info_from_data.get("display_name", f"不明なユーザー (ID: `{user_id}`)") 
            
            self.premium_users.pop(user_id, None) # 内部データから削除
            await save_premium_data_to_jsonbin(self.premium_users) # JSONBin.io に保存

            status_message = f"{display_name} からプレミアムステータスを剥奪しました。"

            target_user = self.bot.get_user(target_user_id) # キャッシュから取得
            if target_user is None:
                try:
                    target_user = await self.bot.fetch_user(target_user_id) # APIからフェッチ
                except discord.NotFound:
                    logging.warning(f"User ID {target_user_id} not found via fetch_user for role removal.")
                    target_user = None 
                except discord.HTTPException as e:
                    logging.error(f"HTTPException when fetching user {target_user_id} for role removal: {e}", exc_info=True)
                    target_user = None
            
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
