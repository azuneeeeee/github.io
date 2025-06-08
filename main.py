import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import traceback
import logging
import asyncio

# --- ロギング設定 ---
# 全体のロギングレベルを INFO に設定し、出力先を標準出力 (Renderのログ) にする
# ここは残しておくことで、discord.py 内部の接続ログは出力される
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.__stdout__) 

# 特定のモジュールのロギングレベルを調整し、不要なデバッグログを減らす
logging.getLogger('discord').setLevel(logging.INFO) # INFO レベルで接続ログを出す
logging.getLogger('websockets').setLevel(logging.WARNING) 
logging.getLogger('discord.app_commands.tree').setLevel(logging.WARNING) 

# .env ファイルから環境変数をロード (最低限の処理)
load_dotenv()

# --- asyncioの未捕捉例外ハンドラ --- (これも必要最低限なので残す)
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"非同期処理で未捕捉の例外が発生しました: {msg}", file=sys.__stderr__)
    if "exception" in context:
        logging.error("トレースバック:", exc_info=context["exception"], file=sys.__stderr__)

# --- Discordクライアントのインテント設定 --- (これも必要)
intents = discord.Intents.all() # all() になっていることを再確認

# --- ボットのインスタンス作成 --- (これも必要)
bot = commands.Bot(command_prefix='!', intents=intents)

# --- on_readyイベントハンドラ ---
# ここだけを重点的にデバッグ
@bot.event
async def on_ready():
    # on_ready イベントが発火した瞬間のログ
    print("デバッグ: === on_ready イベントが発火しました！ ===", file=sys.__stdout__) 
    try:
        # ここに到達すれば、Discordに接続済み
        print(f'デバッグ: on_ready: Logged in as {bot.user.name} ({bot.user.id})', file=sys.__stdout__)
        
        # 短いスリープとシンプルなステータス変更のみ
        await asyncio.sleep(1) 
        await bot.change_presence(activity=discord.Game(name="稼働中！"), status=discord.Status.online) 
        print("デバッグ: on_ready: ステータスを変更しました。", file=sys.__stdout__)
        
        # on_ready イベントの終了を示すログ
        print("デバッグ: === on_ready イベント終了。ボットは完全に稼働中。===", file=sys.__stdout__)

    except Exception as e: 
        print(f"致命的エラー: on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.__stderr__)
        traceback.print_exc(file=sys.__stderr__)

# --- ボットの起動処理 --- (最小限のログに)
async def main():
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("致命的エラー: 環境変数 'DISCORD_BOT_TOKEN' が設定されていません。", file=sys.__stderr__)
        sys.exit(1)
    
    await bot.login(token) 
    await bot.connect() 

# --- プログラムのエントリポイント --- (最小限のログに)
if __name__ == '__main__':
    # ロギング設定の後に、イベントループを設定
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"致命的エラー: asyncio.run(main()) 呼び出し中にエラーが発生しました: {e}", file=sys.__stdout__)
        traceback.print_exc(file=sys.__stdout__)