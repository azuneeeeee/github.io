import sys
import os
import discord
from discord.ext import commands
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
# メンテナンスモードの初期状態は、commands/admin/admin_commands.py で読み込まれるファイルから。
# しかし、bot.is_maintenance_mode はこの時点ではまだファイルから読み込まれないため、初期値は False にしておく。
# on_readyでファイルからロードした値をセットする。
bot.is_maintenance_mode = False
bot.is_bot_ready_for_commands = False
logger.info(f"デバッグ: ボットのカスタム属性が初期化されました: is_maintenance_mode={bot.is_maintenance_mode}, is_bot_ready_for_commands={bot.is_bot_ready_for_commands}")


load_dotenv()
logger.info("デバッグ: 環境変数のロードを試みます。")
logger.info("デバッグ: 環境変数がロードされました。")

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
            # commands.admin.admin_commands をロードする
            # このコグがロードされると、そのモジュールレベルのコードが実行され、
            # maintenance_status.json から is_maintenance_mode の初期値が読み込まれる
            await bot.load_extension("commands.admin.admin_commands") 
            logger.info("デバッグ: commands.admin.admin_commands がロードされました。")
            
            # ロード後、admin_module を参照して初期のメンテナンス状態を bot オブジェクトに設定
            # (これは、admin_commands.py がグローバル変数 _is_maintenance_mode に初期値をロードした後に行う)
            # ここでadmin_moduleをインポートし、そのモジュールから直接値を読み取る
            import commands.admin.admin_commands as admin_module
            bot.is_maintenance_mode = admin_module._is_maintenance_mode # アンダースコア付きのグローバル変数を参照
            logger.info(f"デバッグ: ボット初期起動時のメンテナンスモード状態を {bot.is_maintenance_mode} に設定しました (ファイルからロード)。")

            await bot.load_extension("commands.general.ping_command") 
            logger.info("デバッグ: commands.general.ping_command がロードされました。")
            
        except Exception as e:
            logger.error(f"エラー: コグのロード中にエラーが発生しました: {e}")
            traceback.print_exc(file=sys.__stderr__)

        # スラッシュコマンドを同期する
        logger.info("デバッグ: スラッシュコマンドの同期を開始します。")
        
        # === 同期前にメンテナンスモードを有効にする ===
        logger.info("デバッグ: スラッシュコマンド同期のため、メンテナンスモードを有効にします。")
        bot.is_maintenance_mode = True # bot オブジェクトの状態を更新
        # ファイルにも保存するために、admin_module の save_maintenance_status を使う
        import commands.admin.admin_commands as admin_module_for_save
        admin_module_for_save.save_maintenance_status(True)

        try:
            synced = await bot.tree.sync() # 全ての登録済みスラッシュコマンドを同期
            logger.info(f"デバッグ: スラッシュコマンドが {len(synced)} 件同期されました。")
        except Exception as e:
            logger.error(f"エラー: スラッシュコマンドの同期中にエラーが発生しました: {e}")
            traceback.print_exc(file=sys.__stderr__)
        finally:
            # === 同期後にメンテナンスモードを無効にする ===
            logger.info("デバッグ: スラッシュコマンド同期完了のため、メンテナンスモードを無効にします。")
            bot.is_maintenance_mode = False # bot オブジェクトの状態を更新
            admin_module_for_save.save_maintenance_status(False) # ファイルにも保存

        # ボットがコマンドを受け付ける準備ができたことをフラグに設定
        bot.is_bot_ready_for_commands = True
        logger.info(f"デバッグ: is_bot_ready_for_commands が {bot.is_bot_ready_for_commands} に設定されました。")


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
            
            await asyncio.sleep(1)
            await bot.change_presence(activity=discord.CustomActivity(name=status_message_text), status=discord.Status.online)
            logger.info(f"デバッグ: on_ready: カスタムステータス '{status_message_text}' が設定されました。")

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