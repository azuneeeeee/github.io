import sys
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
import asyncio # asyncio.sleepのため

# === 設定とセットアップ ===
# ロギング設定をシンプルにする
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.__stdout__,
                    encoding='utf-8')
logging.getLogger('discord').setLevel(logging.INFO) # DiscordログレベルをINFOに設定

# .env ファイルから環境変数をロード
load_dotenv()
print("デバッグ: 環境変数がロードされました。", file=sys.__stdout__)

# インテントの設定 (必須)
intents = discord.Intents.all() # 全てのインテントを有効にする
print("デバッグ: インテントが設定されました (discord.Intents.all())。", file=sys.__stdout__)

# ボットインスタンスの作成
bot = commands.Bot(command_prefix='!', intents=intents) # プレフィックスコマンドも使えるようにしておく
print("デバッグ: ボットインスタンスが作成されました。", file=sys.__stdout__)

# === on_ready イベントハンドラ ===
@bot.event
async def on_ready():
    print("デバッグ: on_readyイベントが開始されました！", file=sys.__stdout__) # on_readyの先頭ログ
    try:
        if bot.user:
            print(f'デバッグ: on_ready: {bot.user.name} (ID: {bot.user.id}) としてログインしました', file=sys.__stdout__)
        else:
            print("デバッグ: on_ready: ボットユーザーがNoneです。", file=sys.__stdout__)
        print("デバッグ: on_ready: ボットはDiscordに正常に接続し、準備が完了しました！", file=sys.__stdout__)

        # 最小限のステータス変更
        await asyncio.sleep(1) # 念のため非同期処理を挟む
        await bot.change_presence(activity=discord.Game(name="Online!"), status=discord.Status.online)
        print("デバッグ: on_ready: ステータスが 'Online!' に設定されました。", file=sys.__stdout__)

        print("デバッグ: on_readyイベントが終了しました。ボットは完全に稼働中です。", file=sys.__stdout__)

    except Exception as e:
        print(f"致命的なエラー: on_readyイベント内で予期せぬエラーが発生しました: {e}", file=sys.__stderr__)
        # traceback.print_exc(file=sys.__stderr__) # エラーログはDiscord.pyが出すので省略
print("デバッグ: on_readyイベントハンドラが定義されました。", file=sys.__stdout__)

# === プログラムのエントリポイント ===
if __name__ == '__main__':
    print("デバッグ: プログラムのエントリポイントに入りました。bot.run()でボットを起動します。", file=sys.__stdout__)
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("致命的なエラー: 'DISCORD_BOT_TOKEN' 環境変数が設定されていません。終了します。", file=sys.__stderr__)
        sys.exit(1)
    
    try:
        # bot.run() はボットが停止するまでイベントループをブロックし続ける
        bot.run(token) 
        print("デバッグ: bot.run() が戻りました。これはボットが切断または停止したことを意味します。", file=sys.__stdout__)
    except discord.LoginFailure:
        print("致命的なエラー: トークン認証に失敗しました。DISCORD_BOT_TOKEN を確認してください。", file=sys.__stderr__)
        sys.exit(1)
    except Exception as e:
        print(f"致命的なエラー: asyncio.run()中に重大なエラーが発生しました: {e}", file=sys.__stdout__)
        # traceback.print_exc(file=sys.__stdout__) # エラーログはDiscord.pyが出すので省略
    print("デバッグ: プログラムの実行が終了しました。", file=sys.__stdout__)