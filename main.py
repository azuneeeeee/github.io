import sys
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import logging
import asyncio

print("デバッグ: main.py 実行開始。", file=sys.stdout) # 1

# admin_commands モジュール全体をインポート
from commands.admin import admin_commands 
print("デバッグ: admin_commands をインポートしました。", file=sys.stdout) # 2

# 楽曲データをインポート
from data.songs import proseka_songs, VALID_DIFFICULTIES 
print("デバッグ: data.songs をインポートしました。", file=sys.stdout) # 3

# .env ファイルから環境変数をロード
load_dotenv()
print("デバッグ: 環境変数をロードしました。", file=sys.stdout) # 4

# --- ロギング設定 ---
logging.basicConfig(level=logging.WARNING, 
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.stdout)

logging.getLogger('discord').setLevel(logging.WARNING) 
logging.getLogger('websockets').setLevel(logging.WARNING) 
logging.getLogger('discord.app_commands.tree').setLevel(logging.WARNING) 
print("デバッグ: ロギングを設定しました。", file=sys.stdout) # 5

# --- asyncioの未捕捉例外ハンドラ ---
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"非同期処理で未捕捉の例外が発生しました: {msg}")
    if "exception" in context:
        logging.error("トレースバック:", exc_info=context["exception"])
print("デバッグ: asyncio 例外ハンドラを設定しました。", file=sys.stdout) # 6

# --- Discordクライアントのインテント設定 ---
intents = discord.Intents.all() 
print("デバッグ: インテントを設定しました。", file=sys.stdout) # 7

# --- ボットのインスタンス作成 ---
bot = commands.Bot(command_prefix='!', intents=intents)
print("デバッグ: ボットインスタンスを作成しました。", file=sys.stdout) # 8

# --- 楽曲数と譜面数をカウントするヘルパー関数 ---
def count_songs_and_charts():
    song_count = 0
    chart_count = 0
    if proseka_songs: 
        song_count = len(proseka_songs) 
        for song in proseka_songs:
            for difficulty_key_upper in VALID_DIFFICULTIES:
                difficulty_key = difficulty_key_upper.lower()
                if difficulty_key in song and song[difficulty_key] is not None: 
                    chart_count += 1
    return song_count, chart_count
print("デバッグ: 楽曲カウントヘルパー関数を定義しました。", file=sys.stdout) # 9

# --- on_readyイベントハンドラ ---
@bot.event
async def on_ready():
    # 起動準備中にコマンド受付を無効化
    admin_commands.is_bot_ready_for_commands = False 
    print("デバッグ: 起動準備中のため、コマンド受付を一時停止しました。", file=sys.stdout)

    # 起動準備中にメンテナンスモードをオンにする (製作者以外のコマンドを制限)
    admin_commands.is_maintenance_mode = True 
    print("デバッグ: 起動準備中のため、メンテナンスモードをオンにしました。", file=sys.stdout)

    print("--- on_ready イベント開始 --- (ログ最小限版)", file=sys.stdout) 
    try:
        print(f'Logged in as {bot.user.name}', file=sys.stdout)
        print(f'Bot ID: {bot.user.id}', file=sys.stdout) 
        print('------', file=sys.stdout)
        print("ボットは正常に起動し、Discordに接続しました！", file=sys.stdout)

        # ステータス変更処理（起動準備中ステータス）
        await asyncio.sleep(0.5) 
        await bot.change_presence(activity=discord.Game(name="起動準備中です。")) 
        await asyncio.sleep(0.5) 
        await bot.change_presence(status=discord.Status.idle) 
        print("デバッグ: 起動準備中のステータス (退席中 + 準備中メッセージ) を設定しました。", file=sys.stdout)

        # コグのロードとスラッシュコマンドの同期
        await asyncio.sleep(1) 
        try:
            await bot.load_extension('commands.admin.admin_commands') 
            await bot.load_extension('commands.general.ping_command') 
            
            await asyncio.sleep(0.5) 
            await bot.tree.sync() 
            
            await asyncio.sleep(5) 

        except Exception as e:
            print(f"!!! コグのロードまたはコマンド同期中にエラーが発生しました: {e}", file=sys.stderr) 
            traceback.print_exc(file=sys.stderr)

        await asyncio.sleep(0.5) 
        print("--- on_ready イベント終了 --- (ログ最小限版)", file=sys.stdout)

        print("デバッグ: ボット起動シーケンス完了。コマンド受付開始前の最終待機中...", file=sys.stdout)
        await asyncio.sleep(20) 
        
        try:
            print("デバッグ: ボットは全てのコマンドを受け付ける準備ができました。", file=sys.stdout)

            admin_commands.is_bot_ready_for_commands = True 
            print("デバッグ: コマンド受付を有効にしました。", file=sys.stdout)

            admin_commands.is_maintenance_mode = False
            print("デバッグ: メンテナンスモードをオフにしました。通常運用を開始します。", file=sys.stdout)
            
            song_count, chart_count = count_songs_and_charts()
            custom_status_message = f"{song_count}曲/{chart_count}譜面が登録済み"
            
            await bot.change_presence(activity=discord.Game(name=custom_status_message)) 
            await asyncio.sleep(0.5) 
            await bot.change_presence(status=discord.Status.online)
            print(f"デバッグ: ステータスを '{custom_status_message}' と 'オンライン' に設定しました。", file=sys.stdout)

        except Exception as e:
            print(f"!!! on_ready イベントの最終処理中にエラーが発生しました: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

    except Exception as e: 
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
print("デバッグ: on_ready イベントハンドラを定義しました。", file=sys.stdout) # 10

# --- ボットの起動処理 (段階的起動) ---
async def main():
    print("デバッグ: メイン非同期関数 'main()' 開始。", file=sys.stdout) # 11
    try:
        print("デバッグ: bot.login() を呼び出し中...", file=sys.stdout) # 12
        # Discordにログイン。トークンは環境変数から取得
        await bot.login(os.getenv('DISCORD_BOT_TOKEN')) 
        print("デバッグ: bot.login() 完了。ゲートウェイ接続待機中...", file=sys.stdout) # 13

        await asyncio.sleep(3) 

        print("デバッグ: bot.connect() を呼び出し中...", file=sys.stdout) # 14
        # ゲートウェイに接続し、イベントループを開始
        await bot.connect() 
        print("デバッグ: bot.connect() 完了。", file=sys.stdout) # 15

    except discord.LoginFailure:
        # トークンが不正な場合の致命的エラーハンドリング
        print("致命的エラー: トークン認証に失敗しました。環境変数 DISCORD_BOT_TOKEN を確認してください。", file=sys.stderr)
        sys.exit(1) 
    except Exception as e:
        # その他の致命的エラーハンドリング
        print(f"致命的エラー: メイン非同期関数内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1) 
print("デバッグ: メイン非同期関数 'main' を定義しました。", file=sys.stdout) # 16

# --- プログラムのエントリポイント ---
if __name__ == '__main__':
    print("デバッグ: プログラムのエントリポイントに入りました。", file=sys.stdout) # 17
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    print("デバッグ: イベントループを設定しました。", file=sys.stdout) # 18

    print("デバッグ: Discord Botを起動します。", file=sys.stdout) # 19
    try:
        asyncio.run(main())
        print("デバッグ: asyncio.run(main()) 完了。", file=sys.stdout) # 20
    except Exception as e:
        print(f"デバッグ: asyncio.run(main()) 呼び出し中に致命的なエラーが発生しました: {e}", file=sys.stdout)
        traceback.print_exc(file=sys.stdout)
    print("デバッグ: asyncio.run(main()) 呼び出し後（ここまで来たらボットプロセスが意図せず終了）", file=sys.stdout) # 21