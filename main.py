import sys
import os
import time # これを削除して、元の `asyncio` をインポート

# --- ここからボットのインポートと初期設定 ---
# 必要なライブラリをインポート
import discord
from discord.ext import commands
from dotenv import load_dotenv
import traceback
import logging
import asyncio # time の代わりに asyncio を使用

# --- デバッグログ設定 ---
# Render のメインログに出力されるように直接 sys.__stdout__ を使う
print("デバッグ: main.py 実行開始 - Discordボットの初期化を開始します。", file=sys.__stdout__) 

# admin_commands モジュール全体をインポート
# （まだコメントアウトしておく。問題が出たらさらに切り分けるため）
# from commands.admin import admin_commands 
# print("デバッグ: admin_commands をインポートしました。", file=sys.__stdout__) 

# 楽曲データをインポート
# （まだコメントアウトしておく）
# from data.songs import proseka_songs, VALID_DIFFICULTIES 
# print("デバッグ: data.songs をインポートしました。", file=sys.__stdout__) 

# .env ファイルから環境変数をロード
load_dotenv()
print("デバッグ: 環境変数をロードしました。", file=sys.__stdout__) 

# --- ロギング設定 ---
# 全体のロギングレベルを WARNING に設定し、出力先を標準出力 (Renderのログ) にする
logging.basicConfig(level=logging.WARNING, 
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.__stdout__) 

# 特定のモジュールのロギングレベルを調整し、不要なデバッグログを減らす
logging.getLogger('discord').setLevel(logging.WARNING) 
logging.getLogger('websockets').setLevel(logging.WARNING) 
logging.getLogger('discord.app_commands.tree').setLevel(logging.WARNING) 
print("デバッグ: ロギングを設定しました。", file=sys.__stdout__) 

# --- asyncioの未捕捉例外ハンドラ ---
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"非同期処理で未捕捉の例外が発生しました: {msg}")
    if "exception" in context:
        logging.error("トレースバック:", exc_info=context["exception"])
print("デバッグ: asyncio 例外ハンドラを設定しました。", file=sys.__stdout__) 

# --- Discordクライアントのインテント設定 ---
# --- Discordクライアントのインテント設定 ---
# intents = discord.Intents.default() # この行を削除またはコメントアウト
intents = discord.Intents.all() # この行を有効にする
print("デバッグ: インテントを設定しました。", file=sys.__stdout__) 

# --- ボットのインスタンス作成 ---
try:
    bot = commands.Bot(command_prefix='!', intents=intents)
    print("デバッグ: ボットインスタンスを作成しました。", file=sys.__stdout__) 
except Exception as e:
    print(f"致命的エラー: ボットインスタンスの作成に失敗しました: {e}", file=sys.__stderr__)
    sys.exit(1)

# --- on_readyイベントハンドラ ---
@bot.event
async def on_ready():
    # admin_commands がインポートされていないので、ここでは呼び出さない
    # admin_commands.is_bot_ready_for_commands = False 
    print("--- on_ready イベント開始 ---", file=sys.__stdout__) 
    try:
        print(f'Logged in as {bot.user.name}', file=sys.__stdout__)
        print(f'Bot ID: {bot.user.id}', file=sys.__stdout__) 
        print('------', file=sys.__stdout__)
        print("デバッグ: ボットは正常に起動し、Discordに接続しました！", file=sys.__stdout__)

        # ステータス変更処理（起動準備中ステータス）
        await asyncio.sleep(0.5) 
        await bot.change_presence(activity=discord.Game(name="起動準備中です。")) 
        await asyncio.sleep(0.5) 
        await bot.change_presence(status=discord.Status.idle) 
        print("デバッグ: 起動準備中のステータスを設定しました。", file=sys.__stdout__)

        # コグのロードとスラッシュコマンドの同期
        # （まだコメントアウトしておく）
        # await asyncio.sleep(1) 
        # try:
        #     await bot.load_extension('commands.admin.admin_commands') 
        #     await bot.load_extension('commands.general.ping_command') 
        #     await asyncio.sleep(0.5) 
        #     await bot.tree.sync() 
        #     await asyncio.sleep(5) 
        # except Exception as e:
        #     print(f"!!! コグのロードまたはコマンド同期中にエラーが発生しました: {e}", file=sys.__stderr__) 
        #     traceback.print_exc(file=sys.__stderr__)

        await asyncio.sleep(0.5) 
        print("--- on_ready イベント終了 ---", file=sys.__stdout__)

        # ボットが完全に準備できるまでの待機時間（短縮）
        print("デバッグ: コマンド受付開始前の最終待機中...", file=sys.__stdout__)
        await asyncio.sleep(5) # 短い時間に変更
        
        print("デバッグ: ボットはコマンドを受け付ける準備ができました。", file=sys.__stdout__)
        
        # メンテナンスモードの解除などは admin_commands をインポートしてから行う
        # admin_commands.is_bot_ready_for_commands = True 
        # admin_commands.is_maintenance_mode = False
        
        # ステータスをオンラインにする
        await bot.change_presence(activity=discord.Game(name="稼働中！"), status=discord.Status.online)
        print("デバッグ: ステータスをオンラインに設定しました。", file=sys.__stdout__)

    except Exception as e: 
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.__stderr__)
        traceback.print_exc(file=sys.__stderr__)

print("デバッグ: on_ready イベントハンドラを定義しました。", file=sys.__stdout__) 

# --- ボットの起動処理 (段階的起動) ---
async def main():
    print("デバッグ: メイン非同期関数 'main()' 開始。", file=sys.__stdout__) 
    try:
        print("デバッグ: bot.login() を呼び出し中...", file=sys.__stdout__) 
        token = os.getenv('DISCORD_BOT_TOKEN')
        if not token:
            print("致命的エラー: 環境変数 'DISCORD_BOT_TOKEN' が設定されていません。", file=sys.__stderr__)
            sys.exit(1)
        await bot.login(token) 
        print("デバッグ: bot.login() 完了。ゲートウェイ接続待機中...", file=sys.__stdout__) 

        await asyncio.sleep(3) # ログイン後の短い待機

        print("デバッグ: bot.connect() を呼び出し中...", file=sys.__stdout__) 
        await bot.connect() 
        print("デバッグ: bot.connect() 完了。", file=sys.__stdout__) 

    except discord.LoginFailure:
        print("致命的エラー: トークン認証に失敗しました。環境変数 DISCORD_BOT_TOKEN を確認してください。", file=sys.__stderr__)
        sys.exit(1) 
    except Exception as e:
        print(f"致命的エラー: メイン非同期関数内で予期せぬエラーが発生しました: {e}", file=sys.__stderr__)
        traceback.print_exc(file=sys.__stderr__)
        sys.exit(1) 
print("デバッグ: メイン非同期関数 'main' を定義しました。", file=sys.__stdout__) 

# --- プログラムのエントリポイント ---
if __name__ == '__main__':
    print("デバッグ: プログラムのエントriポイントに入りました。", file=sys.__stdout__) 
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    print("デバッグ: イベントループを設定しました。", file=sys.__stdout__) 

    print("デバッグ: Discord Botを起動します。", file=sys.__stdout__) 
    try:
        asyncio.run(main())
        print("デバッグ: asyncio.run(main()) 完了。", file=sys.__stdout__) 
    except Exception as e:
        print(f"デバッグ: asyncio.run(main()) 呼び出し中に致命的なエラーが発生しました: {e}", file=sys.__stdout__)
        traceback.print_exc(file=sys.__stdout__)
    print("デバッグ: asyncio.run(main()) 呼び出し後（ここまで来たらボットプロセスが意図せず終了）", file=sys.__stdout__)