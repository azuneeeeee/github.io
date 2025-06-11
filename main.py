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
logging.basicConfig(level=logging.INFO,
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

# ボットインスタンスの作成
intents = discord.Intents.all()
logger.info("デバッグ: インテントが設定されました (discord.Intents.all())。")

bot = commands.Bot(command_prefix='!', intents=intents)
logger.info("デバッグ: ボットインスタンスが作成されました。")

# === ボットにカスタム属性を追加して状態を管理する ===
bot.is_maintenance_mode = False
bot.is_bot_ready_for_commands = False
# カスタムステータスのメッセージを保持する属性を追加
bot.original_status_message = "" 
logger.info(f"デバッグ: ボットのカスタム属性が初期化されました: is_maintenance_mode={bot.is_maintenance_mode}, is_bot_ready_for_commands={bot.is_bot_ready_for_commands}, original_status_message='{bot.original_status_message}'")


load_dotenv()
logger.info("デバッグ: 環境変数のロードを試みます。")
logger.info("デバッグ: 環境変数がロードされました。")

# === メンテナンスモード時のステータス切り替えループ ===
@tasks.loop(seconds=10)
async def maintenance_status_loop():
    maintenance_message = "メンテナンス中... 🛠️" # ループ内で定義

    try:
        # bot.is_maintenance_mode が True でない場合は、before_loop で処理されるはずだが、
        # 万が一のためここでもチェックする (ただし、理論上は before_loop で阻止される)
        if not bot.is_maintenance_mode:
            logger.warning("警告: maintenance_status_loop がメンテナンスモードではない状態で実行されました。停止します。")
            maintenance_status_loop.cancel()
            return
            
        current_activity_name = bot.guilds[0].me.activity.name if bot.guilds and bot.guilds[0].me.activity else ""

        if current_activity_name == bot.original_status_message:
            # 現在が元のステータスなら、メンテナンスメッセージに切り替える
            await bot.change_presence(activity=discord.CustomActivity(name=maintenance_message), status=discord.Status.dnd)
            logger.debug(f"デバッグ: ステータスを '{maintenance_message}' に切り替えました。")
        else:
            # 現在がメンテナンスメッセージなら、元のステータスに切り替える
            await bot.change_presence(activity=discord.CustomActivity(name=bot.original_status_message), status=discord.Status.dnd)
            logger.debug(f"デバッグ: ステータスを '{bot.original_status_message}' に切り替えました。")
    except Exception as e:
        logger.error(f"エラー: メンテナンスステータスループ中にエラーが発生しました: {e}")
        traceback.print_exc(file=sys.__stderr__)

@maintenance_status_loop.before_loop
async def before_maintenance_status_loop():
    # ループが開始される直前に実行
    if not bot.is_maintenance_mode:
        logger.warning("警告: maintenance_status_loop.before_loop: bot.is_maintenance_mode が False のためループ開始を阻止します。")
        # ここで例外を発生させることでループの開始を停止できる
        raise RuntimeError("Maintenance loop attempted to start when not in maintenance mode.")
    
    # ループが開始される際に、まず「メンテナンス中」のステータスを設定する
    maintenance_message = "メンテナンス中... 🛠️"
    await bot.change_presence(activity=discord.CustomActivity(name=maintenance_message), status=discord.Status.dnd)
    logger.info(f"デバッグ: maintenance_status_loop.before_loop: 初期ステータスを '{maintenance_message}' に設定しました。")
    await asyncio.sleep(1) # 変更が反映されるのを少し待つ


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
            await bot.load_extension("commands.admin.admin_commands") 
            logger.info("デバッグ: commands.admin.admin_commands がロードされました。")
            
            await bot.load_extension("commands.general.ping_command") 
            logger.info("デバッグ: commands.general.ping_command がロードされました。")
            
        except Exception as e:
            logger.error(f"エラー: コグのロード中にエラーが発生しました: {e}")
            traceback.print_exc(file=sys.__stderr__)

        # スラッシュコマンドを同期する
        logger.info("デバッグ: スラッシュコマンドの同期を開始します。")
        
        # === 同期前にメンテナンスモードを有効にする（起動時の同期用） ===
        logger.info("デバッグ: スラッシュコマンド同期のため、一時的にメンテナンスモードを有効にします。")
        bot.is_maintenance_mode = True 
        # save_maintenance_status を使うため、admin_module を参照
        import commands.admin.admin_commands as admin_module_for_save
        admin_module_for_save.save_maintenance_status(True)

        try:
            synced = await bot.tree.sync() # 全ての登録済みスラッシュコマンドを同期
            logger.info(f"デバッグ: スラッシュコマンドが {len(synced)} 件同期されました。")
        except Exception as e:
            logger.error(f"エラー: スラッシュコマンドの同期中にエラーが発生しました: {e}")
            traceback.print_exc(file=sys.__stderr__)
        finally:
            # === 同期後にメンテナンスモードを無効にする（起動時の同期完了用） ===
            logger.info("デバッグ: スラッシュコマンド同期完了のため、メンテナンスモードを無効にします。")
            bot.is_maintenance_mode = False 
            admin_module_for_save.save_maintenance_status(False)

        # ボットがコマンドを受け付ける準備ができたことをフラグに設定
        bot.is_bot_ready_for_commands = True
        logger.info(デバッグ: is_bot_ready_for_commands が {bot.is_bot_ready_for_commands} に設定されました。)


        # カスタムステータスの設定
        logger.info("デバッグ: カスタムステータスの設定を開始します。")
        try:
            total_songs = len(songs.proseka_songs)
            total_charts = 0
            for song in songs.proseka_songs:
                for diff_key in ['easy', 'normal', 'hard', 'expert', 'master', 'append']:
                    if diff_key in song and song[diff_key] is not None:
                        total_charts += 1

            status_message_text = f"{total_songs}曲/{total_charts}譜面が登録済み"
            
            # bot オブジェクトに元のカスタムステータスを保存
            bot.original_status_message = status_message_text

            await asyncio.sleep(1)
            # 起動時は「オンライン（online）」ステータスに設定
            await bot.change_presence(activity=discord.CustomActivity(name=bot.original_status_message), status=discord.Status.online)
            logger.info(f"デバッグ: on_ready: カスタムステータス '{bot.original_status_message}' とステータス 'オンライン' が設定されました。")

        except AttributeError as ae:
            logger.error(f"エラー: data/songs.py から必要なデータ構造 (proseka_songs) を読み込めませんでした: {ae}")
            traceback.print_exc(file=sys.__stderr__)
        except Exception as status_e:
            logger.error(f"エラー: カスタムステータスの設定中にエラーが発生しました: {status_e}")
            traceback.print_exc(file=sys.__stderr__)

        logger.info("デバッグ: on_readyイベントが終了しました。ボットは完全に稼働中です。")

    except Exception as e:
        logger.critical(f"致命的なエラー: on_readyイベント内で予期せぬエラーが発生しました: {e}")
        traceback.print_exc(file=sys.__stderr__) 
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
        logger.critical(f"致命的なエラー: asyncio.run()中に重大なエラーが発生しました: {e}")
        traceback.print_exc(file=sys.__stdout__)
    logger.info("デバッグ: プログラムの実行が終了しました。")