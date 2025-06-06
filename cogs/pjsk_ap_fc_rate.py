import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
import traceback
import logging # ロギングを追加
import math
from main import is_not_admin_mode_for_non_owner # ★修正: カスタムチェックをインポート★

# .envファイルから環境変数を読み込む (このファイルでは不要ですが、Pythonの規約に従い残します)
from dotenv import load_dotenv
load_dotenv()

# is_owner_globalはmain.pyで定義されているものを使用
# ここでは使われませんが、他のコグとの一貫性のため残します。
# def is_owner_global(interaction: discord.Interaction) -> bool:
#     return interaction.user.id == interaction.client.OWNER_ID

class PjskApFcRateCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # ユーザーごとの現在のViewインスタンスと自動更新ステータスを保持
        # キー: user_id, 値: { 'message_id': ..., 'channel_id': ..., 'view': ..., 'auto_update': bool }
        self.current_views = {}
        # ユーザーごとのAP/FC/クリア/失敗カウントを保持する辞書
        # ボットの再起動でリセットされる（永続化なし）
        self.user_counts = {}  
        logging.info("PjskApFcRateCommands Cog initialized.")

    def get_last_message_info(self, user_id: int) -> dict | None:
        """ユーザーの最後のAP/FCレート表示メッセージ情報を取得する"""
        return self.current_views.get(user_id, None)

    def set_last_message_info(self, user_id: int, message_id: int, channel_id: int, view_instance: discord.ui.View, auto_update: bool = True):
        """ユーザーのAP/FCレート表示メッセージ情報を設定する"""
        self.current_views[user_id] = {
            'message_id': message_id,
            'channel_id': channel_id,
            'view': view_instance, # Viewインスタンス自体も保存
            'auto_update': auto_update # 自動更新ステータス
        }
        logging.debug(f"Set last message info for user {user_id}: msg_id={message_id}, channel_id={channel_id}, auto_update={auto_update}.")

    async def clear_last_message_info(self, user_id: int):
        """
        ユーザーのAP/FCレート表示メッセージ情報をクリアし、
        可能であれば既存のメッセージのViewを無効化する
        """
        if user_id in self.current_views:
            last_msg_info = self.current_views[user_id]
            view = last_msg_info.get('view')
            message_id = last_msg_info.get('message_id')
            channel_id = last_msg_info.get('channel_id')

            # 既存のViewがまだアクティブであれば停止させる
            if view and not view.is_finished():
                view.stop()
                logging.debug(f"Stopped existing view for user {user_id}.")

            # 既存のメッセージのボタンを無効化する
            if message_id and channel_id:
                try:
                    channel = self.bot.get_channel(channel_id)
                    if not channel:
                        channel = await self.bot.fetch_channel(channel_id)

                    if isinstance(channel, (discord.TextChannel, discord.DMChannel)):
                        msg = await channel.fetch_message(message_id)

                        # 新しいViewを作成し、全てのボタンを無効化
                        disabled_view = discord.ui.View(timeout=1) # 短いタイムアウトで作成
                        # 元のViewのボタンをコピーする際に、ApFcRateViewの初期化にcogとuser_idが必要
                        # ただし、ここでは単にボタンを無効化したいだけなので、ダミーのインスタンスからchildrenを取得
                        # もしくは、動的にViewを作成し、ボタンを無効化して追加
                        for item_data in ApFcRateView(self, user_id).children: # 元のViewのボタンをコピー
                            item = discord.ui.Button(label=item_data.label, style=item_data.style, custom_id=item_data.custom_id, row=item_data.row)
                            item.disabled = True
                            disabled_view.add_item(item)

                        await msg.edit(view=disabled_view)
                        logging.debug(f"Disabled buttons for old message {message_id} in channel {channel_id}.")
                except (discord.NotFound, discord.Forbidden):
                    logging.warning(f"Old message {message_id} not found or forbidden, could not disable buttons.")
                except Exception as e:
                    logging.error(f"Failed to disable buttons on old message {message_id}: {e}", exc_info=True)

            del self.current_views[user_id]
            logging.debug(f"Cleared last message info for user {user_id}.")

    def set_user_auto_update_status(self, user_id: int, status: bool):
        """ユーザーのAP/FCレート表示の自動更新ステータスを設定する"""
        if user_id in self.current_views:
            self.current_views[user_id]['auto_update'] = status
            logging.debug(f"User {user_id} auto_update status set to {status}.")
        else:
            logging.warning(f"Attempted to set auto_update for non-existent view for user {user_id}.")

    # --- ユーザーカウントの取得/更新 ---
    def get_user_counts(self, user_id: int) -> dict:
        """ユーザーのAP/FC/クリア/失敗カウントを取得する。存在しない場合は初期値を返す。"""
        return self.user_counts.get(user_id, {'ap': 0, 'fc': 0, 'clear': 0, 'fail': 0})

    def update_user_counts(self, user_id: int, ap: int, fc: int, clear: int, fail: int):
        """ユーザーのAP/FC/クリア/失敗カウントを更新する。"""
        self.user_counts[user_id] = {'ap': ap, 'fc': fc, 'clear': clear, 'fail': fail}
        logging.debug(f"User {user_id} counts updated to: AP={ap}, FC={fc}, Clear={clear}, Fail={fail}")

    async def update_ap_fc_rate_display(self, user_id: int, channel: discord.TextChannel | discord.DMChannel):
        """
        指定されたユーザーのAP/FCレート表示メッセージを更新（または新規送信）する。
        常に新しいメッセージを送信するが、既存のメッセージがある場合はそのボタンを無効化する。
        自動更新がFalseの場合は新しいメッセージを送信しない。
        """
        logging.debug(f"update_ap_fc_rate_display called for user {user_id} in channel {channel.id}.")

        last_msg_info = self.get_last_message_info(user_id)

        # この関数は、Viewのボタン操作や、外部からの自動更新呼び出し(例: random_song cog)で使われます。
        # /pjsk_ap_fc_rate コマンドは、この関数を呼び出す前に auto_update を True にセットしているため、
        # コマンドからの呼び出しでは常に新しいメッセージ送信フローに入るはずです。
        if last_msg_info and not last_msg_info.get('auto_update', True):
            logging.debug(f"Auto-update is disabled for user {user_id}. Skipping new message creation.")
            return

        # ★ 既存のメッセージがある場合は、そのボタンを無効化する ★
        if last_msg_info and last_msg_info['channel_id'] == channel.id:
            logging.debug(f"Found existing message for user {user_id}. Attempting to disable its buttons.")
            try:
                msg = await channel.fetch_message(last_msg_info['message_id'])
                # 新しいViewを作成し、全てのボタンを無効化して既存のメッセージを更新
                disabled_view = discord.ui.View(timeout=1) # 短いタイムアウトで作成
                for item_data in ApFcRateView(self, user_id).children: # 元のViewのボタンをコピー
                    item = discord.ui.Button(label=item_data.label, style=item_data.style, custom_id=item_data.custom_id, row=item_data.row)
                    item.disabled = True
                    disabled_view.add_item(item)
                await msg.edit(view=disabled_view)
                logging.debug(f"Successfully disabled buttons on old message {msg.id}.")
            except (discord.NotFound, discord.Forbidden) as e:
                logging.warning(f"Old message {last_msg_info['message_id']} not found or forbidden, could not disable buttons. Error: {e}")
            except Exception as e:
                logging.error(f"Failed to disable buttons on old message {last_msg_info['message_id']}: {e}", exc_info=True)

            # 既存メッセージの情報をクリア
            await self.clear_last_message_info(user_id)
            logging.debug(f"Cleared old message info for user {user_id}.")


        # カウントを取得（この時点では既にupdate_user_countsで設定済み）
        counts = self.get_user_counts(user_id) 
        ap_count = counts['ap']
        fc_count = counts['fc']
        clear_count = counts['clear']
        fail_count = counts['fail']
        logging.debug(f"Using counts from self.user_counts for new message: AP={ap_count}, FC={fc_count}, Clear={clear_count}, Fail={fail_count}")

        total_attempts = ap_count + fc_count + clear_count + fail_count

        ap_percent = (ap_count / total_attempts * 100) if total_attempts > 0 else 0
        fc_percent = (fc_count / total_attempts * 100) if total_attempts > 0 else 0
        clear_percent = (clear_count / total_attempts * 100) if total_attempts > 0 else 0
        fail_percent = (fail_count / total_attempts * 100) if total_attempts > 0 else 0

        embed = discord.Embed(
            title="AP/FC/クリア率",
            color=discord.Color(0x36393F) # Discordの埋め込み背景に近い色
        )
        embed.add_field(name="総試行回数", value=f"{total_attempts}回", inline=False)
        embed.add_field(name="AP", value=f"{ap_count}回 ({ap_percent:.2f}%)", inline=False)
        embed.add_field(name="FC", value=f"{fc_count}回 ({fc_percent:.2f}%)", inline=False)
        embed.add_field(name="クリア", value=f"{clear_count}回 ({clear_percent:.2f}%)", inline=False)
        embed.add_field(name="クリア失敗", value=f"{fail_count}回 ({fail_percent:.2f}%)", inline=False)

        user_obj = self.bot.get_user(user_id)
        footer_text = f"実行者: {user_obj.display_name}" if user_obj else f"実行者: {user_id}"
        embed.set_footer(text=footer_text)

        # ★ 常に新しいメッセージを送信する ★
        new_view = ApFcRateView(self, user_id)
        try:
            sent_message = await channel.send(embed=embed, view=new_view)
            self.set_last_message_info(user_id, sent_message.id, channel.id, new_view, auto_update=True)
            new_view.message = sent_message
            logging.debug(f"Sent new AP/FC rate message {sent_message.id} for user {user_id} in channel {channel.id}.")
        except discord.Forbidden:
            logging.critical(f"Bot does not have permission to send messages in channel {channel.id} for user {user_id}.")
            traceback.print_exc()
        except Exception as e:
            logging.critical(f"Failed to send new AP/FC rate message for user {user_id} in channel {channel.id}: {e}", exc_info=True)
            traceback.print_exc()

    # --- Slash Commands ---

    @app_commands.command(name="pjsk_ap_fc_rate", description="AP/FC/クリア/クリア失敗の回数を表示します。初期値を指定できます。")
    @app_commands.describe(
        initial_ap="APの初期回数を指定します (デフォルト: 0)",
        initial_fc="FCの初期回数を指定します (デフォルト: 0)",
        initial_clear="クリアの初期回数を指定します (デフォルト: 0)",
        initial_fail="クリア失敗の初期回数を指定します (デフォルト: 0)"
    )
    @is_not_admin_mode_for_non_owner() # ★追加: 管理者モードチェックを適用★
    async def pjsk_ap_f_rate(
        self, 
        interaction: discord.Interaction, 
        initial_ap: app_commands.Range[int, 0] = None, # 0以上の整数
        initial_fc: app_commands.Range[int, 0] = None,
        initial_clear: app_commands.Range[int, 0] = None,
        initial_fail: app_commands.Range[int, 0] = None
    ):
        await interaction.response.defer(ephemeral=False)
        user_id = interaction.user.id
        logging.debug(f"/pjsk_ap_fc_rate called by {interaction.user.name} (ID: {user_id}) with initial_ap={initial_ap}, initial_fc={initial_fc}, initial_clear={initial_clear}, initial_fail={initial_fail}.")

        # ここを修正: 引数が指定されていない場合、0にリセットする
        ap_to_set = initial_ap if initial_ap is not None else 0
        fc_to_set = initial_fc if initial_fc is not None else 0
        clear_to_set = initial_clear if initial_clear is not None else 0
        fail_to_set = initial_fail if initial_fail is not None else 0

        logging.debug(f"User {user_id}'s counts updated with specified initials or reset to 0.")

        # カウントを更新 (これで self.user_counts が更新される)
        self.update_user_counts(user_id, ap_to_set, fc_to_set, clear_to_set, fail_to_set)

        # /pjsk_ap_fc_rateコマンドが実行された場合は、必ず自動更新を有効にする
        self.set_user_auto_update_status(user_id, True)

        # 新しいメッセージを送信するフローへ
        await self.update_ap_fc_rate_display(user_id, interaction.channel) 

        logging.debug(f"Finished processing /pjsk_ap_fc_rate for user {user_id}.")


async def setup(bot):
    """コグをボットにセットアップする関数"""
    cog = PjskApFcRateCommands(bot)
    await bot.add_cog(cog)
    logging.info("PjskApFcRateCommands cog loaded and commands added.")


# --- View クラス ---
class ApFcRateView(discord.ui.View):
    def __init__(self, cog_instance: PjskApFcRateCommands, user_id: int):
        super().__init__(timeout=3600) # 1時間でタイムアウト
        self.cog = cog_instance
        self.user_id = user_id
        # Viewの初期値は常にコグの内部データから取得
        counts = self.cog.get_user_counts(user_id)
        self.current_ap = counts['ap']
        self.current_fc = counts['fc']
        self.current_clear = counts['clear']
        self.current_fail = counts['fail']
        self.message = None # このViewが紐付けられているメッセージ

        logging.debug(f"ApFcRateView initialized for user {user_id}. Initial counts from cog: AP:{self.current_ap}, FC:{self.current_fc}, Clear:{self.current_clear}, Fail:{self.current_fail}")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """インタラクションが適切なユーザーから来ているかチェック"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("この操作は、あなたのAP/FCレート表示に対してのみ可能です。", ephemeral=True)
            return False
        return True

    async def update_display(self, interaction: discord.Interaction):
        """
        表示メッセージを更新し、同時にコグの内部データも更新する
        """
        # ボタン操作でカウントが変更されたら、コグの内部データを更新
        self.cog.update_user_counts(self.user_id, self.current_ap, self.current_fc, self.current_clear, self.current_fail)

        total_attempts = self.current_ap + self.current_fc + self.current_clear + self.current_fail
        ap_percent = (self.current_ap / total_attempts * 100) if total_attempts > 0 else 0
        fc_percent = (self.current_fc / total_attempts * 100) if total_attempts > 0 else 0
        clear_percent = (self.current_clear / total_attempts * 100) if total_attempts > 0 else 0
        fail_percent = (self.current_fail / total_attempts * 100) if total_attempts > 0 else 0

        embed = discord.Embed(
            title="AP/FC/クリア率",
            color=discord.Color(0x36393F) # Discordの埋め込み背景に近い色
        )
        embed.add_field(name="総試行回数", value=f"{total_attempts}回", inline=False)
        embed.add_field(name="AP", value=f"{self.current_ap}回 ({ap_percent:.2f}%)", inline=False)
        embed.add_field(name="FC", value=f"{self.current_fc}回 ({fc_percent:.2f}%)", inline=False)
        embed.add_field(name="クリア", value=f"{self.current_clear}回 ({clear_percent:.2f}%)", inline=False)
        embed.add_field(name="クリア失敗", value=f"{self.current_fail}回 ({fail_percent:.2f}%)", inline=False)
        embed.set_footer(text=f"実行者: {interaction.user.display_name}")

        if self.message:
            try:
                # View自体はそのまま使用し、ボタンの状態を維持
                await self.message.edit(embed=embed, view=self)
                logging.debug(f"ApFcRateView message {self.message.id} updated for user {self.user_id}.")
            except discord.NotFound:
                logging.warning(f"ApFcRateView message {self.message.id} not found during update. Stopping view.")
                self.stop()
                await self.cog.clear_last_message_info(self.user_id) # メッセージが無ければクリア
            except Exception as e:
                logging.error(f"Failed to edit ApFcRateView message {self.message.id}: {e}", exc_info=True)
                self.stop() 
                await self.cog.clear_last_message_info(self.user_id) # エラー時もクリア
        else:
            logging.warning("ApFcRateView message not set. Cannot update display through message.edit.")
            # interaction.response.edit_messageは、最初の応答にしか使えないため、
            # update_displayは基本的にself.messageがあることを前提とする。
            # もしここに来る場合は、何かしらの問題があるため、新規送信は行わない。

    @discord.ui.button(label="AP", style=discord.ButtonStyle.success, custom_id="ap_plus_one", row=0)
    async def ap_plus_one(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_ap += 1
        self.cog.set_user_auto_update_status(self.user_id, True)
        await self.update_display(interaction)
        logging.debug(f"User {self.user_id} incremented AP to {self.current_ap}.")

    @discord.ui.button(label="FC", style=discord.ButtonStyle.primary, custom_id="fc_plus_one", row=0)
    async def fc_plus_one(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_fc += 1
        self.cog.set_user_auto_update_status(self.user_id, True)
        await self.update_display(interaction)
        logging.debug(f"User {self.user_id} incremented FC to {self.current_fc}.")

    @discord.ui.button(label="クリア", style=discord.ButtonStyle.blurple, custom_id="clear_plus_one", row=0)
    async def clear_plus_one(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_clear += 1
        self.cog.set_user_auto_update_status(self.user_id, True)
        await self.update_display(interaction)
        logging.debug(f"User {self.user_id} incremented Clear to {self.current_clear}.")

    @discord.ui.button(label="クリア失敗", style=discord.ButtonStyle.gray, custom_id="fail_plus_one", row=1)
    async def fail_plus_one(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_fail += 1
        self.cog.set_user_auto_update_status(self.user_id, True)
        await self.update_display(interaction)
        logging.debug(f"User {self.user_id} incremented Fail to {self.current_fail}.")

    @discord.ui.button(label="リセット", style=discord.ButtonStyle.danger, custom_id="reset_all_counts", row=1)
    async def reset_all_counts(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.current_ap = 0
        self.current_fc = 0
        self.current_clear = 0
        self.current_fail = 0
        self.cog.set_user_auto_update_status(self.user_id, True)
        await self.update_display(interaction)  
        await interaction.followup.send("すべてのカウントをリセットしました。", ephemeral=True)
        logging.debug(f"User {self.user_id} reset all counts to 0.")

    @discord.ui.button(label="更新を停止", style=discord.ButtonStyle.red, custom_id="stop_ap_fc_rate_updates", row=2)
    async def stop_updates_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        # コグに自動更新を停止するように指示
        self.cog.set_user_auto_update_status(self.user_id, False)

        # このView内のボタンを無効化
        for item in self.children:
            item.disabled = True

        # メッセージを更新してボタンを無効にする
        if self.message:
            try:
                await self.message.edit(view=self)
                await interaction.followup.send("AP/FCレートの自動更新を停止しました。もう一度コマンドを実行すると新しい表示が開始されます。", ephemeral=True)
                logging.debug(f"User {self.user_id} stopped AP/FC rate auto-updates.")
            except discord.NotFound:
                logging.warning("AP/FC rate message not found during update. Stopping view.")
                self.stop() 
                await self.cog.clear_last_message_info(self.user_id) # メッセージが見つからない場合はクリア
            except Exception as e:
                logging.error(f"Failed to update AP/FC rate message and disable buttons: {e}", exc_info=True)
                self.stop() 
                await self.cog.clear_last_message_info(self.user_id) # エラー時もクリア
        else:
            await interaction.followup.send("エラー：メッセージが見つからないため更新停止できませんでした。", ephemeral=True)
            logging.error("ApFcRateView.message is None when stop_updates_button was called.")

        # Viewはタイムアウトで停止されるのを待つ (または clear_last_message_info で明示的に stop される)
        # ここでは View.stop() を呼び出さないことで、Viewインスタンスは残るがボタンは無効になる状態を維持
        # このViewインスタンスは、新しいメッセージが送信された際に clear_last_message_info で処理される。


    async def on_timeout(self):
        """Viewがタイムアウトした時の処理"""
        logging.debug(f"ApFcRateView for user {self.user_id} timed out.")
        if self.message:
            try:
                # タイムアウト時はボタンを無効化する
                for item in self.children:
                    if hasattr(item, 'disabled'):
                        item.disabled = True
                await self.message.edit(view=self)
                logging.debug(f"Disabled buttons for ApFcRateView message {self.message.id} on timeout.")
            except discord.NotFound:
                pass
            except Exception as e:
                logging.error(f"Failed to disable buttons on timeout for user {self.user_id}: {e}", exc_info=True)

        # タイムアウト時もコグから情報をクリア
        await self.cog.clear_last_message_info(self.user_id)
