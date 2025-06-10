import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
import asyncio
import traceback

# data/songs.py から情報をインポート
try:
    from data import songs
    print("デバッグ: data/songs.py を正常にインポートしました。", file=sys.__stdout__)
except ImportError:
    print("致命的なエラー: data/songs.py が見つからないか、インポートできませんでした。", file=sys.__stderr__)
    print("致命的なエラー: GitHubリポジトリのルートに 'data' フォルダがあり、その中に 'songs.py' が存在するか確認してください。", file=sys.__stderr__)
    sys.exit(1)


# === 設定とセットアップ ===
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.__stdout__,
                    encoding='utf-8')
logging.getLogger('discord').setLevel(logging.INFO)

load_dotenv()
print("デバッグ: 環境変数がロードされました。", file=sys.__stdout__)

intents = discord.Intents.all()
print("デバッグ: インテントが設定されました (discord.Intents.all())。", file=sys.__stdout__)

bot = commands.Bot(command_prefix='!', intents=intents)
print("デバッグ: ボットインスタンスが作成されました。", file=sys.__stdout__)

# === on_ready イベントハンドラ ===
@bot.event
async def on_ready():
    print("デバッグ: on_readyイベントが開始されました！", file=sys.__stdout__)
    try:
        if bot.user:
            print(f'デバッグ: on_ready: {bot.user.name} (ID: {bot.user.id}) としてログインしました', file=sys.__stdout__)
        else:
            print("デバッグ: on_ready: ボットユーザーがNoneです。", file=sys.__stdout__)
        print("デバッグ: on_ready: ボットはDiscordに正常に接続し、準備が完了しました！", file=sys.__stdout__)

        # ここで data/songs.py から読み込んだ情報を使ってステータスを設定
        try:
            total_songs = len(songs.proseka_songs) # proseka_songs リストの要素数＝曲数
            
            total_charts = 0
            for song in songs.proseka_songs:
                for diff_key in ['easy', 'normal', 'hard', 'expert', 'master', 'append']:
                    # 難易度キーが存在し、かつその値が None でない場合にのみカウントする
                    if diff_key in song and song[diff_key] is not None:
                        total_charts += 1

            status_message = f"{total_songs}曲/{total_charts}譜面が登録済み"
            
            print(f"デバッグ: on_ready: 設定するカスタムステータス: '{status_message}'", file=sys.__stdout__)
            await asyncio.sleep(1) # 念のため待機
            await bot.change_presence(activity=discord.Game(name=status_message), status=discord.Status.online)
            print("デバッグ: on_ready: カスタムステータスが設定されました。", file=sys.__stdout__)

        except AttributeError as ae:
            print(f"エラー: data/songs.py から必要なデータ構造 (proseka_songs) を読み込めませんでした: {ae}", file=sys.__stderr__)
            print("エラー: songs.py に proseka_songs リストが定義されているか確認してください。", file=sys.__stderr__)
            traceback.print_exc(file=sys.__stderr__)
        except Exception as status_e:
            print(f"エラー: カスタムステータスの設定中にエラーが発生しました: {status_e}", file=sys.__stderr__)
            traceback.print_exc(file=sys.__stderr__)

        print("デバッグ: on_readyイベントが終了しました。ボットは完全に稼働中です。", file=sys.__stdout__)

    except Exception as e:
        print(f"致命的なエラー: on_readyイベント内で予期せぬエラーが発生しました: {e}", file=sys.__stderr__)
        traceback.print_exc(file=sys.__stderr__)
print("デバッグ: on_readyイベントハンドラが定義されました。", file=sys.__stdout__)

# === プログラムのエントリポイント ===
if __name__ == '__main__':
    print("デバッグ: プログラムのエントリポイントに入りました。bot.run()でボットを起動します。", file=sys.__stdout__)
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("致命的なエラー: 'DISCORD_BOT_TOKEN' 環境変数が設定されていません。終了します。", file=sys.__stderr__)
        sys.exit(1)
    
    try:
        bot.run(token) 
        print("デバッグ: bot.run() が戻りました。これはボットが切断または停止したことを意味します。", file=sys.__stdout__)
    except discord.LoginFailure:
        print("致命的なエラー: トークン認証に失敗しました。DISCORD_BOT_TOKEN を確認してください。", file=sys.__stderr__)
        sys.exit(1)
    except Exception as e:
        print(f"致命的なエラー: asyncio.run()中に重大なエラーが発生しました: {e}", file=sys.__stdout__)
        traceback.print_exc(file=sys.__stdout__)
    print("デバッグ: プログラムの実行が終了しました。", file=sys.__stdout__)