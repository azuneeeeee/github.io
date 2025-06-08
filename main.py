import sys

# --- 強制ログファイル出力開始 ---
# プロセス開始直後にログファイルを開き、標準出力もそこにリダイレクト
try:
    log_file_path = "/tmp/bot_startup_debug.log" 
    sys.stdout = open(log_file_path, "w", encoding="utf-8")
    sys.stderr = open(log_file_path, "w", encoding="utf-8")

    print("デバッグ: 強制ログファイル出力開始。Renderのメインログには出ないはず。", file=sys.stdout)
    print("デバッグ: sys.stdout と sys.stderr がファイルにリダイレクトされました。", file=sys.stdout)

except Exception as e:
    # ログファイルを開くこと自体に失敗した場合の最終手段。Renderの通常のログに出ることを期待。
    print(f"致命的エラー: ログファイルを開けませんでした: {e}", file=sys.__stdout__) 
    sys.exit(1) # プロセスを終了

# --- ここから元の main.py のコード ---

import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import logging
import asyncio

print("デバッグ: main.py 実行開始。", file=sys.stdout) 

# admin_commands モジュール全体をインポート
from commands.admin import admin_commands 
print("デバッグ: admin_commands をインポートしました。", file=sys.stdout) 

# 楽曲データをインポート
from data.songs import proseka_songs, VALID_DIFFICULTIES 
print("デバッグ: data.songs をインポートしました。", file=sys.stdout) 

# .env ファイルから環境変数をロード
load_dotenv()
print("デバッグ: 環境変数をロードしました。", file=sys.stdout) 

# --- ロギング設定 ---
logging.basicConfig(level=logging.WARNING, 
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.stdout)

logging.getLogger('discord').setLevel(logging.WARNING) 
logging.getLogger('websockets').setLevel(logging.WARNING) 
logging.getLogger('discord.app_commands.tree').setLevel(logging.WARNING) 
print("デバッグ: ロギングを設定しました。", file=sys.stdout) 

# --- asyncioの未捕捉例外ハンドラ ---
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"非同期処理で未捕捉の例外が発生しました: {msg}")
    if "exception" in context:
        logging.error("トレースバック:", exc_info=context["exception"])
print("デバッグ: asyncio 例外ハンドラを設定しました。", file=sys.stdout) 

# --- Discordクライアントのインテント設定 ---
intents = discord.Intents.all() 
print("デバッグ: インテントを設定しました。", file=sys.stdout) 

# --- ボットのインスタンス作成 ---
bot = commands.Bot(command_prefix='!', intents=intents)
print("デバッグ: ボットインスタンスを作成しました。", file=sys.stdout) 

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
print("デバッグ: 楽曲カウントヘルパー関数を定義しました。", file=sys.stdout) 

# --- on_readyイベントハンドラ ---
@bot.event
async def on_ready():
    admin_commands.is_bot_ready_for_commands = False 
    print("デバッグ: 起動準備中のため、コマンド受付を一時停止しました。", file=sys.stdout)

    admin_commands.is_maintenance_mode = True 
    print("デバッグ: 起動準備中のため、メンテナンスモードをオンにしました。", file=sys.stdout)

    print("--- on_ready イベント開始 --- (ログ最小限版)", file=sys.stdout) 
    try:
        print(f'Logged in as {bot.user.name}', file=sys.stdout)
        print(f'Bot ID: {bot.user.id}', file=sys.stdout) 
        print('------', file=sys.stdout)
        print("ボットは正常に起動し、Discordに接続しました！", file=sys.stdout)

        await asyncio.sleep(0.5) 
        await bot.change_presence(activity=discord.Game(name="起動準備中です。")) 
        await asyncio.sleep(0.5) 
        await bot.change_presence(status=discord.Status.idle) 
        print("デバッグ: 起動準備中のステータス (退席中 + 準備中メッセージ) を設定しました。", file=sys.stdout)

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
print("デバッグ: on_ready イベントハンドラを定義しました。", file=sys.stdout) 

# --- ボットの起動処理 (段階的起動) ---
async def main():
    print("デバッグ: メイン非同期関数 'main()' 開始。", file=sys.stdout) 
    try:
        print("デバッグ: bot.login() を呼び出し中...", file=sys.stdout) 
        await bot.login(os.getenv('DISCORD_BOT_TOKEN')) 
        print("デバッグ: bot.login() 完了。ゲートウェイ接続待機中...", file=sys.stdout) 

        await asyncio.sleep(3) 

        print("デバッグ: bot.connect() を呼び出し中...", file=sys.stdout) 
        await bot.connect() 
        print("デバッグ: bot.connect() 完了。", file=sys.stdout) 

    except discord.LoginFailure:
        print("致命的エラー: トークン認証に失敗しました。環境変数 DISCORD_BOT_TOKEN を確認してください。", file=sys.stderr)
        sys.exit(1) 
    except Exception as e:
        print(f"致命的エラー: メイン非同期関数内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1) 
print("デバッグ: メイン非同期関数 'main' を定義しました。", file=sys.stdout) 

# --- プログラムのエントリポイント ---
if __name__ == '__main__':
    print("デバッグ: プログラムのエントリポイントに入りました。", file=sys.stdout) 
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    print("デバッグ: イベントループを設定しました。", file=sys.stdout) 

    print("デバッグ: Discord Botを起動します。", file=sys.stdout) 
    try:
        asyncio.run(main())
        print("デバッグ: asyncio.run(main()) 完了。", file=sys.stdout) 
    except Exception as e:
        print(f"デバッグ: asyncio.run(main()) 呼び出し中に致命的なエラーが発生しました: {e}", file=sys.stdout)
        traceback.print_exc(file=sys.stdout)
    print("デバッグ: asyncio.run(main()) 呼び出し後（ここまで来たらボットプロセスが意図せず終了）", file=sys.stdout) 

# --- ログファイルクローズ処理 ---
# sys.stdout がリダイレクトされていた場合にのみクローズ
if sys.stdout is not sys.__stdout__: 
    print("デバッグ: 強制ログファイル出力終了。", file=sys.stdout)
    sys.stdout.close()
    sys.stderr.close()
    # 元の標準出力に戻す
    sys.stdout = sys.__stdout__ 
    sys.stderr = sys.__stderr__