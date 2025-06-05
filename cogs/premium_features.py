import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
from datetime import datetime, timedelta, timezone

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
            logging.warning(f"Premium status for user {user_id} has no expiration date. Treating as non-premium or indefinite if intended.")
            # 期限が設定されていない場合は、管理者による手動付与と見なし、無期限とするか、エラーとするかは設計次第。
            # ここでは、期限が設定されていない場合はプレミアムとみなします。
            # ただし、ウェブサイト経由の販売では必ず期限を設定することが推奨されます。
            logging.info(f"User {interaction.user.name} (ID: {user_id}) is premium (no expiration date).")
            return True

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

    @app_commands.command(name="grant_premium", description="指定ユーザーにプレミアムステータスを付与します (オーナー限定)。")
    @app_commands.default_permissions(manage_roles=True)
    @is_bot_owner() 
    async def grant_premium(self, interaction: discord.Interaction, user: discord.Member, days: app_commands.Range[int, 1, 365] = 30):
        """ボットのオーナーがユーザーにプレミアムステータスを付与するためのコマンド"""
        logging.info(f"Command '/grant_premium' invoked by {interaction.user.name} (ID: {interaction.user.id}) for user {user.name} for {days} days.")
        await interaction.response.defer(ephemeral=True)

        user_id = str(user.id)
        
        # 現在のUTC時刻を基準に有効期限を設定
        expiration_date = datetime.now(timezone.utc) + timedelta(days=days)

        self.premium_users[user_id] = {
            "username": user.name,
            "discriminator": user.discriminator,
            "display_name": user.display_name,
            "expiration_date": expiration_date # datetimeオブジェクトとして保存
        }
        save_premium_data(self.premium_users)

        # Discordロールの付与 (ボットにロール管理権限が必要)
        target_guild = interaction.guild
        if target_guild:
            premium_role = target_guild.get_role(PREMIUM_ROLE_ID) 
            
            if premium_role and user:
                try:
                    await user.add_roles(premium_role)
                    logging.info(f"Added role {premium_role.name} to {user.name}.")
                except discord.Forbidden:
                    logging.error(f"Bot lacks permissions to assign role {premium_role.name} to {user.name}.")
                    await interaction.followup.send("ロールを付与する権限がありません。ボットのロールがプレミアムロールより上位にあるか確認してください。", ephemeral=True)
                except Exception as e:
                    logging.error(f"Error adding role to user {user.name}: {e}", exc_info=True)
            else:
                logging.warning(f"Premium role (ID: {PREMIUM_ROLE_ID}) or user {user.name} not found in guild {target_guild.name}.")
                await interaction.followup.send("プレミアムロールが見つからないか、ユーザーがこのサーバーにいませんでした。", ephemeral=True)
        else:
            await interaction.followup.send("このコマンドはサーバー内でのみ実行できます。", ephemeral=True)


        expires_at_jst = expiration_date.astimezone(JST)
        embed = discord.Embed(
            title="✅ プレミアムステータス付与",
            description=f"{user.display_name} にプレミアムステータスを付与しました。",
            color=discord.Color.green()
        )
        embed.add_field(name="期限", value=f"<t:{int(expires_at_jst.timestamp())}:F>", inline=False)
        await interaction.followup.send(embed=embed, ephemeral=True)
        logging.info(f"Premium status granted to {user.name} by {interaction.user.name}.")

    @app_commands.command(name="revoke_premium", description="指定ユーザーからプレミアムステータスを剥奪します (オーナー限定)。")
    @app_commands.default_permissions(manage_roles=True)
    @is_bot_owner()
    async def revoke_premium(self, interaction: discord.Interaction, user: discord.Member):
        """ボットのオーナーがユーザーからプレミアムステータスを剥奪するためのコマンド"""
        logging.info(f"Command '/revoke_premium' invoked by {interaction.user.name} (ID: {interaction.user.id}) for user {user.name}.")
        await interaction.response.defer(ephemeral=True)

        user_id = str(user.id)
        if user_id in self.premium_users:
            del self.premium_users[user_id]
            save_premium_data(self.premium_users)

            # Discordロールの剥奪 (ボットにロール管理権限が必要)
            target_guild = interaction.guild
            if target_guild:
                premium_role = target_guild.get_role(PREMIUM_ROLE_ID) 
                
                if premium_role and user:
                    try:
                        await user.remove_roles(premium_role)
                        logging.info(f"Removed role {premium_role.name} from {user.name}.")
                    except discord.Forbidden:
                        logging.error(f"Bot lacks permissions to remove role {premium_role.name} from {user.name}.")
                        await interaction.followup.send("ロールを剥奪する権限がありません。", ephemeral=True)
                    except Exception as e:
                        logging.error(f"Error removing role from user {user.name}: {e}", exc_info=True)
                else:
                    logging.warning(f"Premium role (ID: {PREMIUM_ROLE_ID}) or user {user.name} not found in guild {target_guild.name}.")
                    await interaction.followup.send("プレミアムロールが見つからないか、ユーザーがこのサーバーにいませんでした。", ephemeral=True)
            else:
                await interaction.followup.send("このコマンドはサーバー内でのみ実行できます。", ephemeral=True)

            embed = discord.Embed(
                title="✅ プレミアムステータス剥奪",
                description=f"{user.display_name} からプレミアムステータスを剥奪しました。",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            logging.info(f"Premium status revoked from {user.name} by {interaction.user.name}.")
        else:
            logging.info(f"User {user.name} does not have premium status to revoke.")
            await interaction.followup.send(f"{user.display_name} はプレミアムユーザーではありません。", ephemeral=True)

async def setup(bot):
    cog = PremiumManagerCog(bot)
    await bot.add_cog(cog)
    logging.info("PremiumManagerCog loaded.")
