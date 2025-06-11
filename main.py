import sys
import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import logging
import asyncio
import traceback

# ロガーの取得
logger = logging.getLogger(__name__)

# === 設定とセットアップ ===
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    handlers=[
                        logging.StreamHandler(sys.stdout)
                    ],
                    encoding='utf-8')

logger.info("デバッグ: ボットスクリプトの実行を開始しました。")

# data/songs.py から情報をインポート
try:
    logger.info("デバッグ: data/songs.py のインポートを試みます。")
    from data import songs
    logger.info("デバッグ: data/songs.py を正常にインポートしました。")
except ImportError:
    logger.critical("致命的なエラー: data/songs.py が見つからないか、インポートできませんでした。")
    logger.critical("致命的なエラー: GitHubリポジトリのルートに 'data' フォルダがあり、その中に 'songs.py' が存在するか確認してください。")
    sys.exit(1)

# utils/config_manager.py から情報をインポート
try:
    logger.info("デバッグ: utils/config_manager.py のインポートを試みます。")
    import utils.config_manager as config_manager_module
    logger.info("デバッグ: utils/config_manager.py を正常にインポートしました。")
except ImportError:
    logger.critical("致命的なエラー: utils/config_manager.py が見つからないか、インポートできませんでした。")
    logger.critical("致命的なエラー: 'utils' フォルダがあり、その中に 'config_manager.py' が存在するか確認してください。")
    sys.exit(1)


# ボットインスタンスの作成
intents = discord.Intents.all()
logger.info("デバッグ: インテントが設定されました (discord.Intents.all())。")

bot = commands.Bot(command_prefix='!', intents=intents)
logger.info("デバッグ: ボットインスタンスが作成されました。")

# === ボットにカスタム属性を追加して状態を管理する ===
bot.is_maintenance_mode = False # これは初期値。config_managerからロードされる
bot.is_bot_ready_for_commands = False
bot.original_status_message = ""
bot.maintenance_loop_initial_delay_done = False
logger.info(f"デバッグ: ボットのカスタム属性が初期化されました: is_maintenance_mode={bot.is_maintenance_mode}, is_bot_ready_for_commands={bot.is_bot_ready_for_commands}, original_status_message='{bot.original_status_message}', maintenance_loop_initial_delay_done={bot.maintenance_loop_initial_delay_done}")


load_dotenv()
logger.info("デバッグ: 環境変数のロードを試みます。")
logger.info("デバッグ: 環境変数がロードされました。")

# === メンテナンスモード時のステータス切り替えループ ===
@tasks.loop(seconds=10)
async def maintenance_status_loop():
    maintenance_message = "メンテナンス中... 🛠️"
    logger.debug("デバッグ: maintenance_status_loop が実行されました。")

    try:
        # 初回遅延チェックはそのまま
        if not bot.maintenance_loop_initial_delay_done:
            if not bot.is_ready():
                logger.info("デバッグ: maintenance_status_loop: 初回実行時、ボットが ready でないため、次サイクルで再試行します。")
                return
            bot.maintenance_loop_initial_delay_done = True
            logger.info("デバッグ: maintenance_status_loop: 初回遅延チェックを完了し、ボットが ready 状態であることを確認しました。")

        # ボットが準備できていない場合はスキップ
        if not bot.is_ready():
            logger.warning("警告: maintenance_status_loop: ボットがまだ準備できていないため、ステータス変更をスキップします。")
            return

        # ギルド情報の取得とログ追加
        if not bot.guilds:
            logger.warning("警告: maintenance_status_loop: ボットが参加しているギルドが見つかりません。ステータスを変更できません。")
            return # ギルドがないとme_memberも取得できないのでここで終了

        me_member = bot.guilds[0].me
        if not me_member:
            logger.warning("警告: maintenance_status_loop: ギルドのボットメンバー情報が取得できません。ステータスを変更できません。")
            return

        current_activity = me_member.activity
        current_activity_name = current_activity.name if current_activity and isinstance(current_activity, discord.CustomActivity) else ""
        current_status_raw = me_member.status
        logger.debug(f"デバッグ: maintenance_status_loop: 現在のステータス: {current_status_raw.name}, 現在のアクティビティ: '{current_activity_name}'")


        if bot.is_maintenance_mode:
            logger.debug("デバッグ: maintenance_status_loop: メンテナンスモードが有効です。ステータス変更を試みます。")
            
            # 目的のステータスと現在のステータスを比較
            target_activity_name = maintenance_message
            target_status = discord.Status.dnd

            should_change_status = False
            if current_status_raw != target_status:
                logger.debug(f"デバッグ: maintenance_status_loop: ステータスが異なる ({current_status_raw.name} != {target_status.name})")
                should_change_status = True
            
            if not (isinstance(current_activity, discord.CustomActivity) and current_activity.name == target_activity_name):
                logger.debug(f"デバッグ: maintenance_status_loop: アクティビティが異なる ('{current_activity_name}' != '{target_activity_name}')")
                should_change_status = True

            if should_change_status:
                await bot.change_presence(activity=discord.CustomActivity(name=target_activity_name), status=target_status)
                logger.info(f"デバッグ: ステータスを '{target_activity_name}' (DND) に切り替えました。")
            else:
                logger.debug("デバッグ: maintenance_status_loop: すでにメンテナンスステータスに設定済みです。")

        else: # bot.is_maintenance_mode が False の場合
            logger.debug("デバッグ: maintenance_status_loop: メンテナンスモードが無効です。ステータスをオンラインに戻します。")
            
            # 目的のステータスと現在のステータスを比較
            target_activity_name = bot.original_status_message
            target_status = discord.Status.online

            should_change_status = False
            if current_status_raw != target_status:
                logger.debug(f"デバッグ: maintenance_status_loop: ステータスが異なる ({current_status_raw.name} != {target_status.name})")
                should_change_status = True

            if not (isinstance(current_activity, discord.CustomActivity) and current_activity.name == target_activity_name):
                logger.debug(f"デバッグ: maintenance_status_loop: アクティビティが異なる ('{current_activity_name}' != '{target_activity_name}')")
                should_change_status = True

            if should_change_status:
                await bot.change_presence(activity=discord.CustomActivity(name=target_activity_name), status=target_status)
                logger.info("デバッグ: maintenance_status_loop: メンテナンスモード無効化に伴い、ステータスをオンラインに戻しました。")
            else:
                logger.debug("デバッグ: maintenance_status_loop: すでにオンラインステータスに設定済みです。")

    except discord.HTTPException as http_e:
        logger.error(f"エラー: Discord APIからのHTTPエラーが発生しました（ステータス変更中）: {http_e} (コード: {http_e.status})", exc_info=True)
    except Exception as e:
        logger.error(f"エラー: メンテナンスステータスループ中に予期せぬエラーが発生しました: {e}", exc_info=True)


# === on_ready イベントハンドラ ===
@bot.event
async def on_ready():
    logger.info("デバッグ: on_readyイベントが開始されました！")
    try:
        if bot.user:
            logger.info(f'デバッグ: on_ready: {bot.user.name} (ID: {bot.user.id}) としてログインしました')
        else:
            logger.info("デバッグ: on_ready: ボットユーザーがNoneです。")
        logger.info("デバッグ: on_ready: ボットはDiscordに正常に接続し、準備が完了しました！")

        # コグをロードする
        logger.info("デバッグ: コグのロードを開始します。")
        try:
            # admin_commands が最初にロードされ、その中でメンテナンスモードの状態がロードされる
            await bot.load_extension("commands.admin.admin_commands")
            logger.info("デバッグ: commands.admin.admin_commands がロードされました。")

            await bot.load_extension("commands.general.ping_commands")
            logger.info("デバッグ: commands.general.ping_commands がロードされました。")

            await bot.load_extension("commands.general.pjsk_random_song_commands")
            logger.info("デバッグ: commands.general.pjsk_random_song_commands がロードされました。")

        except Exception as e:
            logger.error(f"エラー: コグのロード中にエラーが発生しました: {e}", exc_info=True)
            pass


        # スラッシュコマンドを同期する
        logger.info("デバッグ: スラッシュコマンドの同期を開始します。")

        # 同期前にメンテナンスモードを有効にする（起動時の同期用）
        try:
            bot.is_maintenance_mode = True
            config_manager_module.save_maintenance_status(True)
            logger.info("デバッグ: スラッシュコマンド同期のため、一時的にメンテナンスモードを有効にしました。")
        except Exception as e:
            logger.error(f"エラー: 起動時のメンテナンスモード有効化中にエラーが発生しました: {e}", exc_info=True)


        try:
            synced = await bot.tree.sync()
            logger.info(f"デバッグ: スラッシュコマンドが {len(synced)} 件同期されました。")
        except Exception as e:
            logger.error(f"エラー: スラッシュコマンドの同期中にエラーが発生しました: {e}", exc_info=True)
        finally:
            # 同期後にメンテナンスモードを無効にする（起動時の同期完了用）
            try:
                bot.is_maintenance_mode = False
                config_manager_module.save_maintenance_status(False)
                logger.info("デバッグ: スラッシュコマンド同期完了のため、メンテナンスモードを無効にしました。")
            except Exception as e:
                logger.error(f"エラー: 起動時のメンテナンスモード無効化中にエラーが発生しました: {e}", exc_info=True)


        bot.is_bot_ready_for_commands = True
        logger.info(f"デバッグ: is_bot_ready_for_commands が {bot.is_bot_ready_for_commands} に設定されました。")


        # カスタムステータスの設定
        logger.info("デバッグ: カスタムステータスの設定を開始します。")
        try:
            total_songs = len(songs.proseka_songs)
            total_charts = 0
            for song in songs.proseka_songs:
                for diff_key_upper in songs.VALID_DIFFICULTIES:
                    diff_key_lower = diff_key_upper.lower()
                    if diff_key_lower in song and song[diff_key_lower] is not None:
                        total_charts += 1

            status_message_text = f"{total_songs}曲/{total_charts}譜面が登録済み"

            bot.original_status_message = status_message_text
            logger.info(f"デバッグ: on_ready: original_status_message を '{bot.original_status_message}' に設定しました。")

            await asyncio.sleep(1)
            await bot.change_presence(activity=discord.CustomActivity(name=bot.original_status_message), status=discord.Status.online)
            logger.info(f"デバッグ: on_ready: カスタムステータス '{bot.original_status_message}' とステータス 'オンライン' が設定されました。")

        except AttributeError as ae:
            logger.error(f"エラー: data/songs.py から必要なデータ構造 (proseka_songs) を読み込めませんでした: {ae}", exc_info=True)
        except Exception as status_e:
            logger.error(f"エラー: カスタムステータスの設定中にエラーが発生しました: {status_e}", exc_info=True)

        # メンテナンスループの開始
        if not maintenance_status_loop.is_running():
            maintenance_status_loop.start()
            logger.info("デバッグ: maintenance_status_loop が開始されました。")
        else:
            logger.info("デバッグ: maintenance_status_loop は既に実行中です。")


        logger.info("デバッグ: on_readyイベントが終了しました。ボットは完全に稼働中です。")

    except Exception as e:
        logger.critical(f"致命的なエラー: on_readyイベント内で予期せぬエラーが発生しました: {e}", exc_info=True)
logger.info("デバッグ: on_readyイベントハンドラが定義されました。")


# === プログラムのエントリポイント ===
if __name__ == '__main__':
    logger.info("デバッグ: プログラムのエントリポイントに入りました。bot.run()でボットを起動します。")
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        logger.critical("致命的なエラー: 'DISCORD_BOT_TOKEN' 環境変数が設定されていません。終了します。")
        sys.exit(1)

    try:
        bot.run(token)
        logger.info("デバッグ: bot.run() が戻りました。これはボットが切断または停止したことを意味します。")
    except discord.LoginFailure:
        logger.critical("致命的なエラー: トークン認証に失敗しました。DISCORD_BOT_TOKEN を確認してください。")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"致命的なエラー: asyncio.run()中に重大なエラーが発生しました: {e}", exc_info=True)
    logger.info("デバッグ: プログラムの実行が終了しました。")