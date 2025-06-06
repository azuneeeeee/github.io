import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import requests 
import asyncio 

import patreon 

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

JST = timezone(timedelta(hours=9))

PREMIUM_ROLE_ID = 1380155806485315604 

try:
    from cogs.pjsk_record_result import SUPPORT_GUILD_ID
except ImportError:
    logging.error("Failed to import SUPPORT_GUILD_ID from cogs.pjsk_record_result. Please ensure pjsk_record_result.py is correctly set up and defines SUPPORT_GUILD_ID.")
    SUPPORT_GUILD_ID = 0

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GIST_ID = os.getenv('GIST_ID')
GITHUB_API_BASE_URL = "https://api.github.com/gists"

if not GITHUB_TOKEN or not GIST_ID:
    logging.critical("GITHUB_TOKEN or GIST_ID environment variables are not set. Data will not be persistent. Please configure GitHub Gist.")

PATREON_CREATOR_ACCESS_TOKEN = os.getenv('PATREON_CREATOR_ACCESS_TOKEN')
MIN_PREMIUM_PLEDGE_AMOUNT = 1.0 

if not PATREON_CREATOR_ACCESS_TOKEN:
    logging.critical("PATREON_CREATOR_ACCESS_TOKEN environment variable is not set. Patreon automation will not work.")

# --- Patreon テストモードの設定 ---
# PATREON_TEST_MODE_ENABLED = os.getenv('PATREON_TEST_MODE_ENABLED', 'False').lower() == 'true'

# TEST_PATRON_DATA (削除またはコメントアウト)
# TEST_PATRON_DATA = [
#     {
#         "patreon_user_id": "test_patron_id_1",
#         "email": "your.discord.test.email@example.com", 
#         "is_active_patron": True, 
#         "pledge_amount_cents": int(MIN_PREMIUM_PLEDGE_AMOUNT * 100) 
#     },
#     {
#         "patreon_user_id": "test_patron_id_free_trial",
#         "email": "your.discord.trial.email@example.com", 
#         "is_active_patron": True, 
#         "pledge_amount_cents": 0, 
#         "is_on_free_trial": True 
#     },
#     {
#         "patreon_user_id": "test_patron_id_2",
#         "email": "testuser2@example.com", 
#         "is_active_patron": False, 
#         "pledge_amount_cents": 0,
#         "is_on_free_trial": False
#     },
# ]
# logging.info(f"Patreon Test Mode Enabled: {PATREON_TEST_MODE_ENABLED}")
# if PATREON_TEST_MODE_ENABLED:
#     logging.warning("Patreon Test Mode is ENABLED. Actual Patreon API calls are bypassed.")


def _get_patreon_client():
    if not PATREON_CREATOR_ACCESS_TOKEN:
        logging.error("Patreon Creator Access Token is not set.")
        return None
    try:
        api_client = patreon.API(PATREON_CREATOR_ACCESS_TOKEN)
        logging.debug("Patreon API client created.")
        return api_client
    except Exception as e:
        logging.error(f"Failed to create Patreon API client: {e}", exc_info=True)
        return None

async def _fetch_patrons_from_patreon():
    """
    Patreon APIからキャンペーンの全パトロン情報を取得します。
    """
    # ★テストモード関連の分岐は、テストモード無効化時に削除済みであると仮定★

    api_client = _get_patreon_client()
    if not api_client:
        return []

    campaign_id = None
    patrons_data = []

    try:
        loop = asyncio.get_running_loop()

        user_response = await loop.run_in_executor(
            None, lambda: api_client.fetch_user()
        )
        # user_response.data() は単一のユーザーリソースを返す
        user_resource = user_response.data() 
        
        # ユーザーに紐づくキャンペーンを取得 (relationships経由)
        campaigns_relationships = user_resource.relationships('campaigns').data()
        
        if campaigns_relationships:
            # ユーザーが所有する最初のキャンペーンIDを取得 (通常は1つのみ)
            campaign_id = campaigns_relationships[0].id
            logging.info(f"Found campaign ID: {campaign_id}")
        else:
            logging.error("No campaigns found related to the provided Patreon Creator Access Token's user. Please ensure your Patreon account has an active campaign.")
            return []

        cursor = None
        while True:
            pledges_response = await loop.run_in_executor(
                None, lambda c=cursor: api_client.fetch_campaign_members(campaign_id, page_size=25, cursor=c, includes=['user', 'currently_entitled_tiers'])
            )
            
            for member in pledges_response.data():
                if member.type == 'member':
                    patreon_user = member.relationships('user').get() 
                    patreon_user_id = patreon_user.id
                    patreon_user_email = patreon_user.attribute('email')
                    
                    is_premium_eligible = False 
                    current_pledge_cents = 0
                    
                    is_on_free_trial = member.attribute('is_free_trial') 
                    last_charge_status = member.attribute('last_charge_status')
                    is_delinquent = member.attribute('is_delinquent')
                    
                    entitled_tiers = member.relationships('currently_entitled_tiers').data()

                    # 1. 通常の支払い済みパトロンの条件
                    if last_charge_status == 'Paid' and not is_delinquent:
                        if member.attribute('current_entitled_amount_cents') is not None:
                            current_pledge_cents = member.attribute('current_entitled_amount_cents')
                        elif member.attribute('will_pay_cents') is not None: 
                            current_pledge_cents = member.attribute('will_pay_cents')
                        
                        if current_pledge_cents >= MIN_PREMIUM_PLEDGE_AMOUNT * 100 and entitled_tiers:
                            is_premium_eligible = True
                            logging.debug(f"Patreon User {patreon_user_email} (ID: {patreon_user_id}) is an active PAYING patron with pledge {current_pledge_cents/100:.2f} USD.")
                        else:
                            logging.debug(f"Patreon User {patreon_user_email} (ID: {patreon_user_id}) is a paying patron but not meeting pledge/tier criteria (pledge: {current_pledge_cents/100:.2f} USD, entitled_tiers: {bool(entitled_tiers)}).")
                    
                    # 2. 無料トライアル中のパトロンの条件
                    elif is_on_free_trial and entitled_tiers:
                        is_premium_eligible = True
                        logging.debug(f"Patreon User {patreon_user_email} (ID: {patreon_user_id}) is an active FREE TRIAL patron.")
                    else:
                        logging.debug(f"Patreon User {patreon_user_email} (ID: {patron_user_id}) not active (last_charge_status: {last_charge_status}, is_delinquent: {is_delinquent}, is_free_trial: {is_on_free_trial}, entitled_tiers: {bool(entitled_tiers)}).")

                    patrons_data.append({
                        "patreon_user_id": patreon_user_id,
                        "email": patreon_user_email.lower(), 
                        "is_active_patron": is_premium_eligible, 
                        "pledge_amount_cents": current_pledge_cents,
                        "is_on_free_trial": is_on_free_trial 
                    })
            
            cursor = api_client.get_next_cursor(pledges_response)
            if not cursor:
                break
        
        logging.info(f"Fetched {len(patrons_data)} patrons from Patreon API.")
        return patrons_data

    except patreon.PatreonAPIException as e: # ★ここを修正★
        logging.error(f"Patreon API Error during patron fetch: {e}", exc_info=True)
        if hasattr(e, 'status_code') and e.status_code == 401: # status_codeが存在するかチェック
            logging.error("Patreon Creator Access Token is invalid. Please check your PATREON_CREATOR_ACCESS_TOKEN.")
        elif hasattr(e, 'status_code') and e.status_code == 403: # 403 Forbidden も追加
            logging.error("Patreon API Forbidden (403). Check PATREON_CREATOR_ACCESS_TOKEN permissions or if your campaign is active.")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred during Patreon patron fetch: {e}", exc_info=True)
        return []


async def load_premium_data_from_gist():
    if not GITHUB_TOKEN or not GIST_ID:
        logging.error("GitHub Token or Gist ID not set. Cannot load data from Gist.")
        return {}

    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    url = f"{GITHUB_API_BASE_URL}/{GIST_ID}"

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.get(url, headers=headers))
        response.raise_for_status() 
        
        gist_data = response.json()
        
        raw_json_content = gist_data['files'].get('premium_users.json', {}).get('content')
        
        if not raw_json_content:
            logging.warning("No 'premium_users.json' found or content is empty in the specified Gist. Starting with empty data.")
            return {}

        data = json.loads(raw_json_content)
        premium_users = {}
        for user_id, user_info in data.items():
            if 'expiration_date' in user_info and user_info['expiration_date']:
                try:
                    user_info['expiration_date'] = datetime.fromisoformat(user_info['expiration_date']).astimezone(timezone.utc)
                except ValueError:
                    logging.warning(f"Invalid datetime format for user {user_id} in Gist: {user_info['expiration_date']}")
                    user_info['expiration_date'] = None
            premium_users[user_id] = user_info
            
        logging.info(f"Loaded {len(premium_users)} premium users from GitHub Gist.")
        return premium_users
    except requests.exceptions.RequestException as e:
        logging.error(f"Error loading premium data from GitHub Gist: {e}", exc_info=True)
        if hasattr(response, 'status_code'):
            if response.status_code == 404: 
                logging.warning("GitHub Gist not found or incorrect ID/permissions. Starting with empty data.")
            elif response.status_code == 401 or response.status_code == 403: 
                logging.error("GitHub PAT is unauthorized or has insufficient permissions. Check your GITHUB_TOKEN and its 'gist' scope.")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON from GitHub Gist content: {e}", exc_info=True)
        return {}
    except Exception as e:
        logging.error(f"An unexpected error occurred during GitHub Gist data loading: {e}", exc_info=True)
        return {}

async def save_premium_data_to_gist(data: dict):
    if not GITHUB_TOKEN or not GIST_ID:
        logging.error("GitHub Token or Gist ID not set. Cannot save data to Gist.")
        return

    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json' 
    }
    url = f"{GITHUB_API_BASE_URL}/{GIST_ID}"

    serializable_data = {}
    for user_id, user_info in data.items():
        serializable_info = user_info.copy()
        if 'expiration_date' in serializable_info and serializable_info['expiration_date']:
            serializable_info['expiration_date'] = serializable_info['expiration_date'].isoformat()
        serializable_data[user_id] = serializable_info

    payload = {
        "files": {
            "premium_users.json": {
                "content": json.dumps(serializable_data, ensure_ascii=False, indent=4)
            }
        }
    }

    try:
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: requests.patch(url, headers=headers, json=payload))
        response.raise_for_status() 
        logging.info(f"Premium data saved/updated in GitHub Gist. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error saving premium data to GitHub Gist: {e}", exc_info=True)
        if hasattr(response, 'status_code'):
            if response.status_code == 401 or response.status_code == 403:
                logging.error("GitHub PAT is unauthorized or has insufficient permissions for PATCH. Check your GITHUB_TOKEN and its 'gist' scope.")
        return 
    except Exception as e:
        logging.error(f"An unexpected error occurred during GitHub Gist data saving: {e}", exc_info=True)
        return 

async def _update_discord_role(bot_instance: commands.Bot, guild_id: int, member_id: int, should_have_role: bool):
    if not bot_instance or not bot_instance.is_ready():
        logging.warning("Bot instance not ready. Skipping role update.")
        return False

    guild = bot_instance.get_guild(guild_id)
    if not guild:
        logging.error(f"Guild with ID {guild_id} not found for role update.")
        return False

    member = guild.get_member(member_id)
    if not member:
        try:
            member = await guild.fetch_member(member_id)
        except discord.NotFound:
            logging.info(f"Member with ID {member_id} not found in guild {guild_id}. Skipping role update.")
            return False
        except discord.HTTPException as e:
            logging.error(f"Failed to fetch member {member_id} in guild {guild_id}: {e}", exc_info=True)
            return False

    premium_role = guild.get_role(PREMIUM_ROLE_ID)
    if not premium_role:
        logging.error(f"Premium role with ID {PREMIUM_ROLE_ID} not found in guild {guild_id}.")
        return False

    if not guild.me.guild_permissions.manage_roles:
        logging.error("Bot lacks 'manage_roles' permission in the guild for role update.")
        return False

    try:
        if should_have_role and premium_role not in member.roles:
            await member.add_roles(premium_role)
            logging.info(f"Granted premium role to {member.name} (ID: {member_id}) in guild {guild_id}.")
            return True
        elif not should_have_role and premium_role in member.roles:
            await member.remove_roles(premium_role)
            logging.info(f"Revoked premium role from {member.name} (ID: {member_id}) in guild {guild_id}.")
            return True
        logging.debug(f"No role change needed for {member.name} (ID: {member_id}).")
        return False
    except discord.Forbidden:
        logging.error(f"Bot lacks permissions to modify role {premium_role.name} for {member.name} (Forbidden).", exc_info=True)
        return False
    except Exception as e:
        logging.error(f"Error updating role for {member.name} (ID: {member_id}): {e}", exc_info=True)
        return False


def is_premium_check():
    async def predicate(interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        premium_users = await load_premium_data_from_gist() 
        
        user_info = premium_users.get(user_id)
        if not user_info:
            logging.info(f"User {interaction.user.name} (ID: {user_id}) is not premium.")
            await interaction.response.send_message(
                "この機能はプレミアムユーザー限定です。詳細については `/premium_info` コマンドを使用してください。",
                ephemeral=True
            )
            return False

        expiration_date = user_info.get('expiration_date')
        patreon_email = user_info.get('patreon_email')

        if patreon_email:
            logging.info(f"User {interaction.user.name} (ID: {user_id}) is premium via Patreon linkage.")
            return True

        if not expiration_date: 
            logging.info(f"User {interaction.user.name} (ID: {user_id}) is premium (indefinite).")
            return True 

        if expiration_date < datetime.now(JST): 
            logging.info(f"Premium status for user {user_id} expired on {expiration_date.astimezone(JST).strftime('%Y-%m-%d %H:%M:%S JST')}. Revoking automatically.")
            premium_users.pop(user_id, None) 
            await save_premium_data_to_gist(premium_users) 
            
            guild = interaction.guild
            if guild:
                member_id = interaction.user.id
                await _update_discord_role(interaction.client, guild.id, member_id, False)

            await interaction.response.send_message(
                f"あなたのプレミアムステータスは {expiration_date.astimezone(JST).strftime('%Y年%m月%d日 %H時%M分')} に期限切れとなりました。再度購読してください。",
                ephemeral=True
            )
            return False
        
        logging.info(f"User {interaction.user.name} (ID: {user_id}) is premium, expires on {expiration_date.astimezone(JST).strftime('%Y-%m-%d %H:%M:%S JST')}.")
        return True

    return app_commands.check(predicate)

def is_bot_owner():
    async def predicate(interaction: discord.Interaction):
        if hasattr(interaction.client, 'OWNER_ID') and interaction.user.id == interaction.client.OWNER_ID:
            return True
        await interaction.response.send_message("このコマンドはボットのオーナーのみが実行できます。", ephemeral=True)
        return False
    return app_commands.check(predicate)


class PremiumManagerCog(commands.Cog):
    DEFAULT_PATREON_SYNC_INTERVAL_HOURS = 12 

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.premium_users = {} 
        logging.info("PremiumManagerCog initialized.")
        
        self.patreon_sync_task.add_exception_type(Exception)
        
    @tasks.loop(hours=DEFAULT_PATREON_SYNC_INTERVAL_HOURS) 
    async def patreon_sync_task(self):
        logging.info("Starting scheduled Patreon sync task...")
        await self.bot.wait_until_ready()
        await self._perform_patreon_sync_job()
        logging.info("Scheduled Patreon sync task completed.")

    @patreon_sync_task.before_loop
    async def before_patreon_sync_task(self):
        logging.info("Waiting for bot to be ready before starting Patreon sync task loop...")
        await self.bot.wait_until_ready()
        logging.info("Bot ready, starting Patreon sync task loop.")

    async def _perform_patreon_sync_job(self, interaction: Optional['discord.Interaction'] = None):
        sync_start_time = datetime.now(JST)
        success_count = 0
        removed_count = 0
        
        guild_id_to_use = SUPPORT_GUILD_ID 
        if guild_id_to_use == 0:
            logging.error("SUPPORT_GUILD_ID is not set. Cannot perform Patreon sync. Please set the GUILD_ID environment variable.")
            if interaction:
                await interaction.followup.send("エラー: SUPPORT_GUILD_ID が設定されていません。ボットの設定を確認してください。", ephemeral=True)
            return

        guild = self.bot.get_guild(guild_id_to_use)
        if not guild:
            logging.error(f"Guild with ID {guild_id_to_use} not found for Patreon sync.")
            if interaction:
                await interaction.followup.send(f"エラー: 設定されたギルド (ID: `{guild_id_to_use}`) が見つかりません。", ephemeral=True)
            return
        
        if not guild.me.guild_permissions.manage_roles:
            logging.error("Bot lacks 'manage_roles' permission in the guild for Patreon sync.")
            if interaction:
                await interaction.followup.send("ボットにロールを管理する権限がありません。ボットのロールをプレミアムロールより上位に配置し、'ロールの管理'権限を付与してください。", ephemeral=True)
            return

        if interaction: 
            await interaction.followup.send("Patreonとプレミアムステータスの同期を開始します...", ephemeral=True)
        logging.info("Starting Patreon and premium status synchronization.")

        patreon_patrons = await _fetch_patrons_from_patreon() 
        if not patreon_patrons:
            logging.error("Failed to fetch patrons from Patreon. Skipping sync.")
            if interaction:
                await interaction.followup.send("Patreonからパトロンデータを取得できませんでした。PATREON_CREATOR_ACCESS_TOKENが正しいか、キャンペーンにパトロンがいるか確認してください。", ephemeral=True)
            return
        
        patreon_email_map = {p['email'].lower(): p for p in patreon_patrons if p['email']}

        self.premium_users = await load_premium_data_from_gist()
        
        users_to_update_in_gist = self.premium_users.copy() 
        
        for discord_user_id, user_info in self.premium_users.items():
            patreon_email = user_info.get('patreon_email')
            discord_member_id = int(discord_user_id)

            should_be_premium_by_patreon = False
            if patreon_email:
                patron_in_patreon = patreon_email_map.get(patreon_email.lower())
                if patron_in_patreon and patron_in_patreon['is_active_patron']:
                    should_be_premium_by_patreon = True
            
            current_is_premium = False
            if patreon_email: 
                current_is_premium = should_be_premium_by_patreon
                if current_is_premium: 
                    if user_info.get('expiration_date') is not None: 
                        user_info['expiration_date'] = None
                        users_to_update_in_gist[discord_user_id] = user_info 
                        logging.info(f"Set expiration_date to None for Patreon user {discord_user_id}.")
                else: 
                    if discord_user_id in users_to_update_in_gist:
                        users_to_update_in_gist.pop(discord_user_id)
                        logging.info(f"Removed user {discord_user_id} from Gist due to inactive Patreon pledge.")
            elif user_info.get('expiration_date'): 
                if user_info['expiration_date'] < datetime.now(JST):
                    current_is_premium = False 
                    if discord_user_id in users_to_update_in_gist:
                        users_to_update_in_gist.pop(discord_user_id)
                        logging.info(f"Removed expired manual premium user {discord_user_id} from Gist.")
                else:
                    current_is_premium = True 
            else: 
                current_is_premium = True

            role_changed = await _update_discord_role(self.bot, guild.id, discord_member_id, current_is_premium)
            if role_changed:
                if current_is_premium:
                    success_count += 1
                else:
                    removed_count += 1
        
        await save_premium_data_to_gist(users_to_update_in_gist)
        self.premium_users = users_to_update_in_gist 
        
        sync_end_time = datetime.now(JST)
        duration = (sync_end_time - sync_start_time).total_seconds()

        if interaction: 
            embed = discord.Embed(
                title="✅ Patreon同期完了",
                description=f"PatreonとDiscordのプレミアムステータスを同期しました。\n\n"
                            f"**同期開始:** <t:{int(sync_start_time.timestamp())}:F>\n"
                            f"**同期終了:** <t:{int(sync_end_time.timestamp())}:F>\n"
                            f"**処理時間:** `{duration:.2f}`秒\n"
                            f"**新たにプレミアム付与:** `{success_count}`人\n"
                            f"**プレミアム剥奪:** `{removed_count}`人",
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        logging.info(f"Patreon sync completed. Added: {success_count}, Removed: {removed_count}. Duration: {duration:.2f}s")


    @app_commands.command(name="premium_info", description="あなたのプレミアムステータスを表示します。")
    async def premium_info(self, interaction: discord.Interaction):
        logging.info(f"Command '/premium_info' invoked by {interaction.user.name} (ID: {interaction.user.id}).")
        await interaction.response.defer(ephemeral=True)

        user_id = str(interaction.user.id)
        self.premium_users = await load_premium_data_from_gist() 
        user_info = self.premium_users.get(user_id)

        embed = discord.Embed(title="プレミアムステータス", color=discord.Color.gold())

        if user_info:
            expiration_date = user_info.get('expiration_date')
            patreon_email = user_info.get('patreon_email') 

            if patreon_email: 
                embed.description = f"あなたは現在プレミアムユーザーです！\nPatreonアカウント: `{patreon_email}` と連携済み。"
                embed.color = discord.Color.green()
            
                if expiration_date: 
                    expires_at_jst = expiration_date.astimezone(JST)
                    if expires_at_jst > datetime.now(JST):
                        embed.description += f"\n(手動付与の期限: <t:{int(expires_at_jst.timestamp())}:F>)"
                    else: 
                        embed.description += f"\n(手動付与は期限切れ: <t:{int(expires_at_jst.timestamp())}:F>)"
                        embed.color = discord.Color.orange() 
            elif expiration_date: 
                expires_at_jst = expiration_date.astimezone(JST)
                if expires_at_jst > datetime.now(JST):
                    embed.description = f"あなたは現在プレミアムユーザーです！\n期限: <t:{int(expires_at_jst.timestamp())}:F>"
                    embed.color = discord.Color.green()
                else:
                    embed.description = f"あなたのプレミアムステータスは期限切れです。\n期限: <t:{int(expires_at_jst.timestamp())}:F>"
                    embed.color = discord.Color.red()
                    if user_id in self.premium_users:
                        self.premium_users.pop(user_id)
                        await save_premium_data_to_gist(self.premium_users)
            else: 
                embed.description = "あなたは現在プレミアムユーザーです！ (期限なし)"
                embed.color = discord.Color.green()
        else:
            embed.description = "あなたは現在プレミアムユーザーではありません。"
            embed.color = discord.Color.red()
        
        sync_interval_display = getattr(self.patreon_sync_task, 'interval', self.DEFAULT_PATREON_SYNC_INTERVAL_HOURS)

        embed.add_field(
            name="プレミアムプランのご案内", 
            value=f"より多くの機能を利用するには、Patreonで私たちを支援してください。\n[Patreonはこちら](https://www.patreon.com/your_bot_name_here)\n\nPatreonとDiscordアカウントを連携するには、`/link_patreon <Patreon登録メールアドレス>` コマンドを使用してください。\n**自動同期は `{sync_interval_display}` 時間ごとに行われます。**", 
            inline=False
        )

        await interaction.followup.send(embed=embed, ephemeral=True)
        logging.info(f"Premium info sent to {interaction.user.name}.")

    @app_commands.command(name="premium_exclusive_command", description="プレミアムユーザー限定のすごい機能！")
    @is_bot_owner() 
    @app_commands.guilds(discord.Object(id=SUPPORT_GUILD_ID))
    async def premium_exclusive_command(self, interaction: discord.Interaction):
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

    @app_commands.command(name="link_patreon", description="PatreonアカウントとDiscordアカウントを連携します。")
    async def link_patreon(self, interaction: discord.Interaction, patreon_email: str):
        logging.info(f"Command '/link_patreon' invoked by {interaction.user.name} (ID: {interaction.user.id}) with email: {patreon_email}.")
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound).", exc_info=True)
            return
        except Exception as e:
            logging.error(f"Unexpected error during defer for '{interaction.command.name}': {e}", exc_info=True)
            return
        
        user_id = str(interaction.user.id)
        self.premium_users = await load_premium_data_from_gist() 

        user_info = self.premium_users.get(user_id, {})
        user_info.update({
            "username": interaction.user.name, 
            "discriminator": interaction.user.discriminator,
            "display_name": interaction.user.display_name,
            "patreon_email": patreon_email.lower() 
        })
        if "expiration_date" not in user_info:
             user_info["expiration_date"] = None 

        self.premium_users[user_id] = user_info
        await save_premium_data_to_gist(self.premium_users)

        sync_interval_display = getattr(self.patreon_sync_task, 'interval', self.DEFAULT_PATREON_SYNC_INTERVAL_HOURS)

        embed = discord.Embed(
            title="✅ アカウント連携完了！",
            description=f"DiscordアカウントとPatreonメールアドレス `{patreon_email}` を連携しました。\n自動同期は `{sync_interval_display}` 時間ごとに行われます。次回同期時にプレミアムステータスが更新されます。",
            color=discord.Color.blue()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        logging.info(f"User {interaction.user.id} linked with Patreon email {patreon_email}.")


    @app_commands.command(name="sync_patrons", description="PatreonのパトロンリストとDiscordのプレミアムステータスを同期します (オーナー限定)。")
    @app_commands.default_permissions(manage_roles=True)
    @is_bot_owner()
    @app_commands.guilds(discord.Object(id=SUPPORT_GUILD_ID))
    async def sync_patrons(self, interaction: discord.Interaction):
        logging.info(f"Command '/sync_patrons' invoked by {interaction.user.name} (ID: {interaction.user.id}).")
        
        try:
            await interaction.response.defer(ephemeral=True)
            logging.info(f"Successfully deferred interaction for '{interaction.command.name}'.")
        except discord.errors.NotFound:
            logging.error(f"Failed to defer interaction for '{interaction.command.name}': Unknown interaction (404 NotFound).", exc_info=True)
            return
        except Exception as e:
            logging.error(f"Unexpected error during defer for '{interaction.command.name}': {e}", exc_info=True)
            return

        await self._perform_patreon_sync_job(interaction) 


    @app_commands.command(name="grant_premium", description="指定ユーザーのIDにプレミアムステータスを付与します (オーナー限定)。")
    @app_commands.default_permissions(manage_roles=True)
    @is_bot_owner() 
    @app_commands.guilds(discord.Object(id=SUPPORT_GUILD_ID))
    async def grant_premium(self, interaction: discord.Interaction, 
                            user_id: str, 
                            days: Optional[app_commands.Range[int, 1, 365]] = None): 
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

        target_user = self.bot.get_user(target_user_id) 
        if target_user is None:
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
            
        expiration_date = None
        if days is not None:
            expiration_date = datetime.now(timezone.utc) + timedelta(days=days)

        self.premium_users = await load_premium_data_from_gist()
        user_info = self.premium_users.get(user_id, {})
        user_info.update({ 
            "username": target_user.name, 
            "discriminator": target_user.discriminator,
            "display_name": target_user.display_name,
            "expiration_date": expiration_date 
        })
        if "patreon_email" in user_info:
            logging.info(f"Removing patreon_email for manually granted user {user_id}.")
            user_info.pop("patreon_email")

        self.premium_users[user_id] = user_info 
        await save_premium_data_to_gist(self.premium_users) 

        status_message = f"{target_user.display_name} (ID: `{target_user.id}`) にプレミアムステータスを付与しました。"

        target_guild = interaction.guild
        if target_guild:
            member_id = target_user.id
            await _update_discord_role(self.bot, target_guild.id, member_id, True)
            status_message += f"\nDiscordロールを付与しました。"
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
        self.premium_users = await load_premium_data_from_gist() 
        
        if user_id in self.premium_users:
            user_info_from_data = self.premium_users.get(user_id)
            display_name = user_info_from_data.get("display_name", f"不明なユーザー (ID: `{user_id}`)") 
            
            self.premium_users.pop(user_id, None) 
            await save_premium_data_to_gist(self.premium_users) 

            status_message = f"{display_name} からプレミアムステータスを剥奪しました。"

            target_guild = interaction.guild
            if target_guild:
                member_id = target_user_id
                await _update_discord_role(self.bot, target_guild.id, member_id, False)
                status_message += f"\nDiscordロールを剥奪しました。"
            else: 
                status_message += f"\nこのコマンドはDMでは実行できません。ロール操作はサーバー内でのみ可能です。"
                logging.warning("revoke_premium command invoked in DM. Role operation skipped.")
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
