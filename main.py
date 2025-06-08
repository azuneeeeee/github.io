import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import logging
import sys
import asyncio

# admin_commands モジュール全体をインポート
from commands.admin import admin_commands 

# 楽曲データをインポート
from data.songs import proseka_songs, VALID_DIFFICULTIES 

load_dotenv()

# --- ロギング設定 ---
logging.basicConfig(level=logging.WARNING, 
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.stdout)

logging.getLogger('discord').setLevel(logging.WARNING) 
logging.getLogger('websockets').setLevel(logging.WARNING) 
logging.getLogger('discord.app_commands.tree').setLevel(logging.WARNING) 

# --- asyncioの未捕捉例外ハンドラ ---
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"非同期処理で未捕捉の例外が発生しました: {msg}")
    if "exception" in context:
        logging.error("トレースバック:", exc_info=context["exception"])

# --- Discordクライアントのインテント設定 ---
intents = discord.Intents.all() 

# --- ボットのインスタンス作成 ---
bot = commands.Bot(command_prefix='!', intents=intents)

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

# --- on_readyイベントハンドラ ---
@bot.event
async def on_ready():
    # 起動準備中にコマンド受付を無効化
    admin_commands.is_bot_ready_for_commands = False 
    print("デバッグ: 起動準備中のため、コマンド受付を一時停止しました。", file=sys.stdout)

    # 起動準備中にメンテナンスモードをオンにする
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
        # --- ここを修正：ステータスを idle (退席中) に、カスタムステータスを「起動準備中です。」に設定 ---
        await bot.change_presence(activity=discord.CustomActivity(name="起動準備中です。"), status=discord.Status.idle) 
        # --- 修正ここまで ---

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

        # 起動後の最終待機
        print("デバッグ: ボット起動シーケンス完了。コマンド受付開始前の最終待機中...", file=sys.stdout)
        await asyncio.sleep(20) 
        print("デバッグ: ボットは全てのコマンドを受け付ける準備ができました。", file=sys.stdout)

        # 待機時間終了後、コマンド受付を有効にする
        admin_commands.is_bot_ready_for_commands = True 
        print("デバッグ: コマンド受付を有効にしました。", file=sys.stdout)

        # メンテナンスモードをオフにする
        admin_commands.is_maintenance_mode = False
        print("デバッグ: メンテナンスモードをオフにしました。通常運用を開始します。", file=sys.stdout)
        
        # 楽曲数と譜面数をカウント
        song_count, chart_count = count_songs_and_charts()
        custom_status_message = f"{song_count}曲/{chart_count}譜面が登録済み"
        
        # カスタムステータスを設定し、初期ステータスをオンラインにする
        await bot.change_presence(activity=discord.CustomActivity(name=custom_status_message), status=discord.Status.online)
        print(f"デバッグ: ステータスを '{custom_status_message}' と 'オンライン' に設定しました。", file=sys.stdout)

    except Exception as e:
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

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

    except discord.LoginFailure:
        print("致命的エラー: トークン認証に失敗しました。環境変数 DISCORD_BOT_TOKEN を確認してください。", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"致命的エラー: メイン非同期関数内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

    print("デバッグ: Discord Botを起動します。", file=sys.stdout)
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"デバッグ: asyncio.run(main()) 呼び出し中に致命的なエラーが発生しました: {e}", file=sys.stdout)
        traceback.print_exc(file=sys.stdout)
    print("デバッグ: asyncio.run(main()) 呼び出し後（ここまで来たらボットプロセスが意図せず終了）", file=sys.stdout)