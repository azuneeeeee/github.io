import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging # logging モジュールをインポート
import asyncio
import traceback

# ロガーの取得をここで行う
logger = logging.getLogger(__name__) # <-- この行はここにあることを確認

# === 設定とセットアップ ===
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    handlers=[
                        logging.StreamHandler(sys.stdout) # <-- これを確実に含める
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

# commands.admin.admin_commands からグローバル変数をインポート
# import の際にコードが実行されるため、先にインポートしておく
import commands.admin.admin_commands as admin_module

logger.info("デバッグ: 環境変数のロードを試みます。")
load_dotenv()
logger.info("デバッグ: 環境変数がロードされました。")

intents = discord.Intents.all()
logger.info("デバッグ: インテントが設定されました (discord.Intents.all())。")

bot = commands.Bot(command_prefix='!', intents=intents)
logger.info("デバッグ: ボットインスタンスが作成されました。")

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

        # コグをロードする (順序が重要: admin_commands -> ping_command)
        logger.info("デバッグ: コグのロードを開始します。")
        try:
            logger.info("デバッグ: commands.admin.admin_commands のロードを試みます。")
            await bot.load_extension("commands.admin.admin_commands") 
            logger.info("デバッグ: commands.admin.admin_commands がロードされました。")
            
            logger.info("デバッグ: commands.general.ping_command のロードを試みます。")
            await bot.load_extension("commands.general.ping_command") 
            logger.info("デバッグ: commands.general.ping_command がロードされました。")
            
        except Exception as e:
            logger.error(f"エラー: コグのロード中にエラーが発生しました: {e}")
            traceback.print_exc(file=sys.__stderr__)

        logger.info("デバッグ: is_bot_ready_for_commands フラグを設定します。")
        # ボットがコマンドを受け付ける準備ができたことをフラグに設定
        # これにより、not_in_maintenance デコレータのチェックをパスできるようになります
        # ここで admin_commands.py のグローバル変数にアクセスする
        import commands.admin.admin_commands as admin_module # ここを修正済み
        admin_module.is_bot_ready_for_commands = True
        logger.info(f"デバッグ: is_bot_ready_for_commands が {admin_module.is_bot_ready_for_commands} に設定されました。")


        # スラッシュコマンドを同期する
        logger.info("デバッグ: スラッシュコマンドの同期を開始します。")
        try:
            synced = await bot.tree.sync() # 全ての登録済みスラッシュコマンドを同期
            logger.info(f"デバッグ: スラッシュコマンドが {len(synced)} 件同期されました。")
        except Exception as e:
            logger.error(f"エラー: スラッシュコマンドの同期中にエラーが発生しました: {e}")
            traceback.print_exc(file=sys.__stderr__)

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
        traceback.print_exc(file=sys.__stdout__) # ここは stdout に出力
    logger.info("デバッグ: プログラムの実行が終了しました。")