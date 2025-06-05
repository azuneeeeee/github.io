import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional # Optional をインポート

# --- Firebase Admin SDK Imports ---
# Firebase Admin SDK は pip install firebase-admin でインストールする必要があります
import firebase_admin
from firebase_admin import credentials, firestore, auth
from google.cloud.firestore_v1.base_query import FieldFilter # FieldFilterのインポート (Firestoreクエリで使用する場合)

# ロギング設定
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

# プレミアムユーザーデータを保存するファイルパス (Firestoreに移行するため、ファイルはバックアップ用途)
PREMIUM_DATA_FILE = "data/premium_users.json" # Keep for local backup/dev if needed
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
    SUPPORT_GUILD_ID = 0

# Firestoreのクライアントインスタンスをグローバルに保持
db = None
# アプリケーションIDもFirestoreのコレクションパスで使用するためグローバルに保持
app_id_global = None 

def init_firestore():
    """Firebase Admin SDKとFirestoreクライアントを初期化します。"""
    global db, app_id_global
    if firebase_admin._apps: # アプリが既に初期化されているかチェック
        logging.info("Firebase app already initialized globally.")
        db = firestore.client()
        # app_id_globalは環境変数から取得し続ける
        app_id_global = os.getenv('__app_id')
        if not app_id_global:
            logging.critical("__app_id environment variable is not set. Firestore collection path might be incorrect (using default).")
            app_id_global = "default-app-id"
        return

    try:
        # Render環境変数からFirebase設定を読み込み
        firebase_config_str = os.getenv('__firebase_config')
        if not firebase_config_str:
            raise ValueError("__firebase_config environment variable is not set. Cannot initialize Firebase.")
        
        # サービスアカウントキーのJSON文字列をパース
        # Renderの環境変数には直接JSON文字列を格納していると仮定
        service_account_info = json.loads(firebase_config_str)
        cred = credentials.Certificate(service_account_info)
        
        firebase_admin.initialize_app(cred)
        db = firestore.client()
        logging.info("Firestore initialized successfully using service account credentials.")

        app_id_global = os.getenv('__app_id')
        if not app_id_global:
            logging.critical("__app_id environment variable is not set. Firestore collection path might be incorrect (using default).")
            app_id_global = "default-app-id"

    except ValueError as ve:
        logging.critical(f"Firestore initialization failed (ValueError): {ve}. Ensure __firebase_config is a valid JSON string and __app_id is set.", exc_info=True)
        db = None
        app_id_global = "default-app-id"
    except Exception as e:
        logging.critical(f"An unexpected error occurred during Firestore initialization: {e}", exc_info=True)
        db = None
        app_id_global = "default-app-id"

# Firestoreからプレミアムユーザーデータをロードする関数
async def load_premium_data_from_firestore():
    if not db:
        logging.error("Firestore client is not initialized. Cannot load premium data from Firestore.")
        return {} # Firestoreが利用できない場合は空の辞書を返す
    if not app_id_global or app_id_global == "default-app-id":
        logging.error("App ID is not set or is default. Firestore collection path might be incorrect. Please set __app_id.")
        return {}

    premium_users = {}
    # Firestoreのコレクションパス定義 (公共データとして保存)
    # ユーザー認証はここでは行わないため、public/dataを使用
    collection_path = f"artifacts/{app_id_global}/public/data/premium_users" 
    
    try:
        # stream() は同期的に動作するが、通常は高速
        docs = db.collection(collection_path).stream()
        for doc in docs:
            data = doc.to_dict()
            user_id = doc.id
            # FirestoreのTimestampオブジェクトをdatetimeに変換
            if 'expiration_date' in data and isinstance(data.get('expiration_date'), firestore.Timestamp):
                data['expiration_date'] = data['expiration_date'].astimezone(timezone.utc)
            # Noneの場合や他の型の場合はそのまま保持
            elif 'expiration_date' in data and data.get('expiration_date') is not None:
                # 念のため、ISOフォーマット文字列などの可能性がある場合も対応
                try:
                    data['expiration_date'] = datetime.fromisoformat(data['expiration_date']).astimezone(timezone.utc)
                except (ValueError, TypeError):
                    data['expiration_date'] = None # 無効な場合はNoneとする
            premium_users[user_id] = data
        logging.info(f"Loaded {len(premium_users)} premium users from Firestore collection: {collection_path}.")
        return premium_users
    except Exception as e:
        logging.error(f"Error loading premium data from Firestore collection '{collection_path}': {e}", exc_info=True)
        return {}

# Firestoreにプレミアムユーザーデータを保存する関数
# この関数は単一のユーザーのデータを保存するために最適化されています。
async def save_premium_user_to_firestore(user_id: str, user_data: dict):
    if not db:
        logging.error("Firestore client is not initialized. Cannot save premium user.")
        return
    if not app_id_global or app_id_global == "default-app-id":
        logging.error("App ID is not set or is default. Firestore collection path might be incorrect. Please set __app_id.")
        return

    collection_path = f"artifacts/{app_id_global}/public/data/premium_users"
    doc_ref = db.collection(collection_path).document(user_id)
    
    serializable_data = user_data.copy()
    # datetimeオブジェクトをFirestoreのTimestampに変換
    if 'expiration_date' in serializable_data and isinstance(serializable_data['expiration_date'], datetime):
        serializable_data['expiration_date'] = firestore.Timestamp.from_datetime(serializable_data['expiration_date'])
    elif 'expiration_date' in serializable_data and serializable_data['expiration_date'] is None:
        serializable_data['expiration_date'] = None # Explicitly save None
    
    try:
        # set() はドキュメントが存在すれば更新、存在しなければ作成
        await doc_ref.set(serializable_data) # set() is synchronous in Firebase Admin SDK, so no await unless wrapped.
        logging.info(f"User {user_id} saved/updated in Firestore.")
    except Exception as e:
        logging.error(f"Error saving user {user_id} to Firestore: {e}", exc_info=True)

# Firestoreから特定のユーザーを削除するヘルパー関数
async def delete_premium_user_from_firestore(user_id: str):
    if not db:
        logging.error("Firestore client is not initialized. Cannot delete premium user.")
        return
    if not app_id_global or app_id_global == "default-app-id":
        logging.error("App ID is not set or is default. Firestore collection path might be incorrect. Please set __app_id.")
        return

    collection_path = f"artifacts/{app_id_global}/public/data/premium_users"
    doc_ref = db.collection(collection_path).document(user_id)
    try:
        await doc_ref.delete() # delete() is synchronous in Firebase Admin SDK, so no await unless wrapped.
        logging.info(f"User {user_id} deleted from Firestore.")
    except Exception as e:
        logging.error(f"Error deleting user {user_id} from Firestore: {e}", exc_info=True)


# --- is_premium_check, is_bot_owner 関数 (Firestore対応のため変更あり) ---
def is_premium_check():
    """
    ユーザーがプレミアムステータスを持っているかをチェックするカスタムデコレータ。
    このチェックは、有効期限が切れていないかも確認します。
    """
    async def predicate(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        premium_users = await load_premium_data_from_firestore() # Firestoreからロード
        
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
            # 期限切れの場合は自動的にプレミアムステータスをFirestoreから削除
            await delete_premium_user_from_firestore(user_id) 
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
        os.makedirs(DATA_DIR, exist_ok=True)
        # Firebase初期化はコグのインスタンス作成時に行いますが、
        # main.pyのsetup_hookで既にグローバルに初期化されていることを推奨します。
        # ここでは念のため呼び出しておきますが、二重初期化はされません。
        init_firestore() 
        # premium_users は on_ready イベントでFirestoreからロードされます
        self.premium_users = {} 
        logging.info("PremiumManagerCog initialized.")

    @commands.Cog.listener()
    async def on_ready(self):
        """ボットが完全に起動し、Discordに接続された後に実行されます。"""
        # Firestoreの初期化が完了していることを確認
        global db
        if db: 
            self.premium_users = await load_premium_data_from_firestore()
            logging.info(f"Loaded {len(self.premium_users)} premium users from Firestore during on_ready.")
        else:
            logging.warning("Firestore client not initialized during on_ready. Premium features might not load correctly.")


    @app_commands.command(name="premium_info", description="あなたのプレミアムステータスを表示します。")
    async def premium_info(self, interaction: discord.Interaction):
        """ユーザーのプレミアムステータスを表示するコマンド"""
        logging.info(f"Command '/premium_info' invoked by {interaction.user.name} (ID: {interaction.user.id}).")
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        # コマンド実行時に常に最新データをFirestoreからロードして確認
        self.premium_users = await load_premium_data_from_firestore() 
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
                    # 期限切れの場合は、念のためFirestoreからも削除する
                    await delete_premium_user_from_firestore(user_id)
                    # 内部状態も更新
                    if user_id in self.premium_users:
                        del self.premium_users[user_id]
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

        user_data_to_save = { # Firestoreに保存するデータ構造
            "username": target_user.name, 
            "discriminator": target_user.discriminator,
            "display_name": target_user.display_name,
            "expiration_date": expiration_date # datetimeオブジェクト (None の可能性あり)
        }
        
        await save_premium_user_to_firestore(user_id, user_data_to_save) # Firestoreに保存
        self.premium_users = await load_premium_data_from_firestore() # 内部状態をFirestoreから再ロード

        status_message = f"{target_user.display_name} (ID: `{target_user.id}`) にプレミアムステータスを付与しました。"

        target_guild = interaction.guild
        if target_guild:
            member = target_guild.get_member(target_user.id)
            if member: # メンバーとして存在する場合のみロールを付与
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
        # コマンド実行時に常に最新データをFirestoreからロードして確認
        self.premium_users = await load_premium_data_from_firestore() 
        
        if user_id in self.premium_users:
            user_info_from_data = self.premium_users.get(user_id)
            display_name = user_info_from_data.get("display_name", f"不明なユーザー (ID: `{user_id}`)") 
            
            await delete_premium_user_from_firestore(user_id) # Firestoreから削除
            self.premium_users = await load_premium_data_from_firestore() # 内部状態をFirestoreから再ロード

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
                if member: # メンバーとして存在する場合のみロールを剥奪
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
