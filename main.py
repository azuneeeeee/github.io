import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import traceback
import logging
import asyncio

# --- デバッグログ設定 ---
# Render のメインログに出力されるように直接 sys.__stdout__ を使う
print("デバッグ: main.py 実行開始 - Discordボットの最小限の初期化を開始します。", file=sys.__stdout__) 

# .env ファイルから環境変数をロード
load_dotenv()
print("デバッグ: 環境変数をロードしました。", file=sys.__stdout__) 

# --- ロギング設定 ---
# 全体のロギングレベルを INFO に変更して、discord.py からの情報をもう少し多く表示させる
logging.basicConfig(level=logging.INFO, # WARNING から INFO に変更
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.__stdout__) 

logging.getLogger('discord').setLevel(logging.INFO) # WARNING から INFO に変更
logging.getLogger('websockets').setLevel(logging.WARNING) 
logging.getLogger('discord.app_commands.tree').setLevel(logging.WARNING) 
print("デバッグ: ロギングを設定しました。", file=sys.__stdout__) 

# --- asyncioの未捕捉例外ハンドラ ---
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"非同期処理で未捕捉の例外が発生しました: {msg}", file=sys.__stderr__)
    if "exception" in context:
        logging.error("トレースバック:", exc_info=context["exception"], file=sys.__stderr__)
print("デバッグ: asyncio 例外ハンドラを設定しました。", file=sys.__stdout__) 

# --- Discordクライアントのインテント設定 ---
intents = discord.Intents.all() # all() になっていることを再確認
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
    print("--- on_ready イベント開始 --- (超シンプル版)", file=sys.__stdout__) 
    try:
        print(f'デバッグ: on_ready - ログイン情報: {bot.user.name} ({bot.user.id})', file=sys.__stdout__)
        print("デバッグ: on_ready - ボットはDiscordに接続済みです。", file=sys.__stdout__)

        # 短いスリープのみ。ステータス変更は行わない。
        await asyncio.sleep(5) 
        print("デバッグ: on_ready - 5秒スリープしました。", file=sys.__stdout__)
        
        print("--- on_ready イベント終了 --- (超シンプル版)", file=sys.__stdout__)

    except Exception as e: 
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.__stderr__)
        traceback.print_exc(file=sys.__stderr__)

print("デバッグ: on_ready イベントハンドラを定義しました。", file=sys.__stdout__)
# --- ボットの起動処理 ---
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

        print("デバッグ: bot.connect() を呼び出し中...", file=sys.__stdout__) 
        await bot.connect() # on_ready イベントが発火するのを待つ
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
    print("デバッグ: プログラムのエントリポイントに入りました。", file=sys.__stdout__) 
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