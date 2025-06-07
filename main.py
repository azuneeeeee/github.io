import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import logging
import sys
import asyncio

# admin_commands コグをインポート
# OWNER_ID と is_maintenance_mode は admin_commands.py から共有される変数
from admin_commands import OWNER_ID, is_maintenance_mode # not_in_maintenanceも必要なら追加

load_dotenv()

# ロギング設定 (デバッグに役立つため、このままにしておきましょう)
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.stdout)

logging.getLogger('discord').setLevel(logging.DEBUG)
logging.getLogger('websockets').setLevel(logging.DEBUG)


def handle_exception(loop, context):
    """asyncioの未捕捉例外を処理するハンドラ"""
    msg = context.get("exception", context["message"])
    logging.error(f"非同期処理で未捕捉の例外が発生しました: {msg}")
    if "exception" in context:
        logging.error("トレースバック:", exc_info=context["exception"])


# Discordクライアントのインテント設定
# 本番運用時は必要なインテントのみに絞ることを推奨します。
intents = discord.Intents.all() # デバッグのため、このまま all() にしておく


# ボットのインスタンスを作成
# commands.Botにapplication_command_prefix='!'は不要です！
bot = commands.Bot(command_prefix='!', intents=intents)


print("DEBUG: on_readyイベントハンドラ定義直前（ボット初期化後）", file=sys.stderr)

@bot.event
async def on_ready():
    """ボットがDiscordに接続した際に実行される処理"""
    print("DEBUG: on_readyイベントの最初に入りました！", file=sys.stderr)
    print("--- on_ready イベント開始 ---", file=sys.stdout)
    try:
        print(f'Logged in as {bot.user.name}', file=sys.stdout)
        print(f'Bot ID: {bot.user.id}', file=sys.stdout)
        print('------', file=sys.stdout)
        print("ボットは正常に起動し、Discordに接続しました！", file=sys.stdout)

        # OWNER_IDの読み込み処理を有効化
        global OWNER_ID
        print("--- OWNER_ID 読み込み前 ---", file=sys.stdout)
        if os.getenv('DISCORD_OWNER_ID'):
            try:
                OWNER_ID = int(os.getenv('DISCORD_OWNER_ID'))
                print(f"製作者IDが環境変数から {OWNER_ID} に設定されました。", file=sys.stdout)
            except ValueError:
                print("警告: 環境変数 DISCORD_OWNER_ID が無効な数値です。製作者IDは設定されません。", file=sys.stdout)
                OWNER_ID = None
        else:
            print("警告: 環境変数 DISCORD_OWNER_ID が設定されていません。製作者専用コマンドは機能しません。", file=sys.stdout)
            OWNER_ID = None
        print("--- OWNER_ID 読み込み後 ---", file=sys.stdout)

        # ステータス変更処理を有効化
        if is_maintenance_mode:
            await bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
        else:
            await bot.change_presence(activity=discord.Game(name="プロセカ！ | !help_proseka"))
        print("--- ステータス変更後 ---", file=sys.stdout)

        # admin_commands コグのロードとスラッシュコマンドの同期を有効化
        try:
            await bot.load_extension('admin_commands')
            print("admin_commands コグをロードしました。", file=sys.stdout)
            # スラッシュコマンドをDiscordに同期
            await bot.tree.sync() # treeを明示的に呼び出す
            print("スラッシュコマンドをDiscordに同期しました。", file=sys.stdout)
        except Exception as e:
            print(f"admin_commands コグのロード中またはコマンド同期中にエラーが発生しました: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

        print("--- on_ready イベント終了 ---", file=sys.stdout)

    except Exception as e:
        # on_ready 内で発生するエラーを捕捉
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


# ボットの起動処理
if __name__ == '__main__':
    # asyncioのイベントループを取得し、未捕捉例外ハンドラを設定
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

    print("デバッグ: Flaskは無効。Discord Botを単独で実行します。", file=sys.stdout)
    try:
        print("デバッグ: bot.run() を呼び出し中...", file=sys.stdout)
        bot.run(os.getenv('DISCORD_BOT_TOKEN'))
    except Exception as e:
        # bot.run() 自体で発生するエラーを捕捉
        print(f"デバッグ: Discord Botの実行中に致命的なエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    print("デバッグ: bot.run() 呼び出し後（ここまで来たらボットプロセスが意図せず終了）", file=sys.stdout)