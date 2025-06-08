import sys
# --- 追加するデバッグログのファイル出力 ---
# プロセス開始直後にログファイルを開き、標準出力もそこにリダイレクト
try:
    # ログファイル名
    log_file_path = "/tmp/bot_startup_debug.log" 
    
    # ファイルを書き込みモードで開く (毎回新規作成)
    sys.stdout = open(log_file_path, "w", encoding="utf-8")
    sys.stderr = open(log_file_path, "w", encoding="utf-8") # エラー出力も同じファイルへ

    print("デバッグ: 強制ログファイル出力開始。", file=sys.stdout)
    print("デバッグ: sys.stdout がファイルにリダイレクトされました。", file=sys.stdout)

except Exception as e:
    # もしログファイルを開くこと自体に失敗した場合の最終手段
    # このメッセージはRenderの通常のログに出ることを期待
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

# admin_commands モジュール全体をインポート
# admin_commands.py に定義されている is_maintenance_mode や is_bot_ready_for_commands にアクセスするため
from commands.admin import admin_commands 

# 楽曲データをインポート
# data/songs.py に定義されている proseka_songs と VALID_DIFFICULTIES にアクセスするため
from data.songs import proseka_songs, VALID_DIFFICULTIES 

# .env ファイルから環境変数をロード
load_dotenv()

# --- ロギング設定 ---
# 全体のロギングレベルを WARNING に設定し、出力先を標準出力 (Renderのログ) にする
logging.basicConfig(level=logging.WARNING, 
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.stdout) # ファイルにリダイレクトされたsys.stdoutに出力

# 特定のモジュールのロギングレベルを調整し、不要なデバッグログを減らす
logging.getLogger('discord').setLevel(logging.WARNING) 
logging.getLogger('websockets').setLevel(logging.WARNING) 
logging.getLogger('discord.app_commands.tree').setLevel(logging.WARNING) 

# --- asyncioの未捕捉例外ハンドラ ---
# 非同期処理で例外が発生した場合に、ログに出力するためのハンドラ
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"非同期処理で未捕捉の例外が発生しました: {msg}")
    if "exception" in context:
        logging.error("トレースバック:", exc_info=context["exception"])

# --- Discordクライアントのインテント設定 ---
# ボットが必要なイベントを受信できるように、全てのインテントを有効にする
intents = discord.Intents.all() 

# --- ボットのインスタンス作成 ---
# コマンドプレフィックスを '!' に設定し、インテントを渡す
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 楽曲数と譜面数をカウントするヘルパー関数 ---
def count_songs_and_charts():
    song_count = 0
    chart_count = 0
    if proseka_songs: # proseka_songs が存在する場合のみ処理
        song_count = len(proseka_songs) # 楽曲数はリストの要素数
        
        # 各楽曲について、VALID_DIFFICULTIES を参照して譜面数をカウント
        for song in proseka_songs:
            for difficulty_key_upper in VALID_DIFFICULTIES: # VALID_DIFFICULTIES は大文字なので
                difficulty_key = difficulty_key_upper.lower() # 楽曲辞書内のキーは小文字
                
                # 楽曲辞書に難易度キーが存在し、かつその値が None でない場合にカウント
                if difficulty_key in song and song[difficulty_key] is not None: 
                    chart_count += 1
    return song_count, chart_count

# --- on_readyイベントハンドラ ---
# ボットがDiscordに接続し、準備ができたときに実行されるイベント
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
        # まずカスタムアクティビティを設定
        await asyncio.sleep(0.5) 
        await bot.change_presence(activity=discord.Game(name="起動準備中です。")) 
        # その後、短い遅延を置いてステータスを「退席中」に設定
        await asyncio.sleep(0.5) 
        await bot.change_presence(status=discord.Status.idle) 
        print("デバッグ: 起動準備中のステータス (退席中 + 準備中メッセージ) を設定しました。", file=sys.stdout)

        # コグのロードとスラッシュコマンドの同期
        await asyncio.sleep(1) # コグロード前の短い待機
        try:
            await bot.load_extension('commands.admin.admin_commands') 
            await bot.load_extension('commands.general.ping_command') 
            
            await asyncio.sleep(0.5) # コグロード後の短い待機
            await bot.tree.sync() # スラッシュコマンドをDiscordに同期
            
            await asyncio.sleep(5) # 同期後の待機 (Discord APIのレートリミット回避など)

        except Exception as e:
            # コグロードや同期中にエラーが発生した場合のハンドリング
            print(f"!!! コグのロードまたはコマンド同期中にエラーが発生しました: {e}", file=sys.stderr) 
            traceback.print_exc(file=sys.stderr)

        await asyncio.sleep(0.5) # 最終待機前の短い待機
        print("--- on_ready イベント終了 --- (ログ最小限版)", file=sys.stdout)

        # 起動後の最終待機（この間にボットはバックグラウンドで準備を続ける）
        print("デバッグ: ボット起動シーケンス完了。コマンド受付開始前の最終待機中...", file=sys.stdout)
        await asyncio.sleep(20) # ボットが完全に準備できるまでの待機時間
        
        # --- 起動準備完了後の処理を try-except で囲み、エラーを特定しやすくする ---
        try:
            print("デバッグ: ボットは全てのコマンドを受け付ける準備ができました。", file=sys.stdout)

            # 待機時間終了後、コマンド受付を有効にする
            admin_commands.is_bot_ready_for_commands = True 
            print("デバッグ: コマンド受付を有効にしました。", file=sys.stdout)

            # メンテナンスモードをオフにする (通常運用に戻す)
            admin_commands.is_maintenance_mode = False
            print("デバッグ: メンテナンスモードをオフにしました。通常運用を開始します。", file=sys.stdout)
            
            # 楽曲数と譜面数をカウントし、カスタムステータスを設定
            song_count, chart_count = count_songs_and_charts()
            custom_status_message = f"{song_count}曲/{chart_count}譜面が登録済み"
            
            # カスタムアクティビティを設定
            await bot.change_presence(activity=discord.Game(name=custom_status_message)) 
            await asyncio.sleep(0.5) # 短い遅延
            # その後、ステータスを「オンライン」に設定
            await bot.change_presence(status=discord.Status.online)
            print(f"デバッグ: ステータスを '{custom_status_message}' と 'オンライン' に設定しました。", file=sys.stdout)

        except Exception as e:
            # 起動準備完了後の最終処理でエラーが発生した場合のハンドリング
            print(f"!!! on_ready イベントの最終処理中にエラーが発生しました: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        # --- try-except ブロックここまで ---

    except Exception as e: # on_ready イベント全体の例外ハンドリング
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# --- ボットの起動処理 (段階的起動) ---
# bot.run() の代わりに、より詳細なデバッグが可能な非同期関数
async def main():
    print("デバッグ: メイン非同期関数 'main()' 開始。", file=sys.stdout)
    try:
        print("デバッグ: bot.login() を呼び出し中...", file=sys.stdout)
        # Discordにログイン。トークンは環境変数から取得
        await bot.login(os.getenv('DISCORD_BOT_TOKEN')) 
        print("デバッグ: bot.login() 完了。ゲートウェイ接続待機中...", file=sys.stdout)

        await asyncio.sleep(3) # ログイン後の短い待機

        print("デバッグ: bot.connect() を呼び出し中...", file=sys.stdout)
        # ゲートウェイに接続し、イベントループを開始
        await bot.connect() 

    except discord.LoginFailure:
        # トークンが不正な場合の致命的エラーハンドリング
        print("致命的エラー: トークン認証に失敗しました。環境変数 DISCORD_BOT_TOKEN を確認してください。", file=sys.stderr)
        sys.exit(1) # プロセスを終了
    except Exception as e:
        # その他の致命的エラーハンドリング
        print(f"致命的エラー: メイン非同期関数内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1) # プロセスを終了

# --- プログラムのエントリポイント ---
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    # 非同期ループの未捕捉例外をハンドリングするための設定
    loop.set_exception_handler(handle_exception)

    print("デバッグ: Discord Botを起動します。", file=sys.stdout)
    try:
        # メイン非同期関数を実行
        asyncio.run(main())
    except Exception as e:
        # asyncio.run() の実行中にエラーが発生した場合のハンドリング
        print(f"デバッグ: asyncio.run(main()) 呼び出し中に致命的なエラーが発生しました: {e}", file=sys.stdout)
        traceback.print_exc(file=sys.stdout)
    # ここまで到達した場合、通常はボットプロセスが意図せず終了していることを示す
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