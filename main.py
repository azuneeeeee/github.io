import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import logging
import sys
import asyncio

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
    print(f"致命的エラー: ログファイルを開けませんでした: {e}", file=sys.__stdout__) # 元の標準出力に出す
    sys.exit(1) # プロセスを終了

# --- ここから元の main.py のコード ---

# .env ファイルから環境変数をロード
load_dotenv()

# --- ロギング設定 ---
logging.basicConfig(level=logging.WARNING, 
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.stdout) # リダイレクトされたsys.stdoutに出力

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
# data/songs.py をインポートする前に定義されていることを確認
# proseka_songs と VALID_DIFFICULTIES は後でインポートされるので注意

# 楽曲データをインポート
# data/songs.py に定義されている proseka_songs と VALID_DIFFICULTIES にアクセスするため
from data.songs import proseka_songs, VALID_DIFFICULTIES # <--- ここでインポート

def count_songs_and_charts():
    # ... (既存の count_songs_and_charts 関数) ...
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


# admin_commands モジュール全体をインポート
from commands.admin import admin_commands 


# --- on_readyイベントハンドラ ---
@bot.event
async def on_ready():
    # ... (既存の on_ready 関数) ...
    # on_readyの全てのprint文は、これでファイルに書き出されます
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

# --- プログラムのエントリポイント ---
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

# --- ログファイルクローズ処理 ---
# これがないと、最後のログがファイルに書き込まれない可能性があります
if sys.stdout is not sys.__stdout__: # もしリダイレクトされていたら
    print("デバッグ: 強制ログファイル出力終了。", file=sys.stdout)
    sys.stdout.close()
    sys.stderr.close()
    sys.stdout = sys.__stdout__ # 元に戻す
    sys.stderr = sys.__stderr__ # 元に戻す