import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import logging
import sys
import asyncio # <-- asyncioのエラーハンドリング用


# --- ロギング設定を一番最初に配置 ---
# 全体のロギングレベルをDEBUGに設定し、標準出力へ
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.stdout)

# discord.pyとwebsocketsのロガーもDEBUGレベルに設定
logging.getLogger('discord').setLevel(logging.DEBUG)
logging.getLogger('websockets').setLevel(logging.DEBUG)


# --- async def handle_exception(loop, context): を追加 ---
def handle_exception(loop, context):
    """asyncioの未捕捉例外を処理するハンドラ"""
    msg = context.get("exception", context["message"])
    logging.error(f"非同期処理で未捕捉の例外が発生しました: {msg}")
    if "exception" in context:
        logging.error("トレースバック:", exc_info=context["exception"])
    # 必要であれば、ここでボットを安全にシャットダウンする処理などを追加できます
    # 例: asyncio.create_task(bot.close())

# --- ここまで追加 ---


load_dotenv()

# Discordクライアントのインテント設定
# !!! デバッグのため、全てのインテントを一時的に有効にします !!!
# 問題解決後には、必要なインテントのみに戻すことを推奨します。
intents = discord.Intents.all()


# ボットのインスタンスを作成
# application_command_prefix は今回もデバッグのため削除したまま
bot = commands.Bot(command_prefix='!', intents=intents)


# --- on_readyデコレータの直前にデバッグログを追加 ---
print("DEBUG: on_readyイベントハンドラ定義直前（ボット初期化後）", file=sys.stderr)

@bot.event
async def on_ready():
    """ボットがDiscordに接続した際に実行される処理"""
    print("DEBUG: on_readyイベントの最初に入りました！", file=sys.stderr) # <-- on_ready内の最初のprint
    print("--- on_ready イベント開始 (最終デバッグ版) ---", file=sys.stdout)
    try:
        print(f'Logged in as {bot.user.name}', file=sys.stdout)
        print(f'Bot ID: {bot.user.id}', file=sys.stdout)
        print('------', file=sys.stdout)
        print("ボットは正常に起動し、Discordに接続しました！", file=sys.stdout)
        print("--- on_ready イベント終了 (最終デバッグ版) ---", file=sys.stdout)

        # ここから先は、問題解決後にコメントアウトを解除し、元のコードを戻してください
        # global OWNER_ID
        # print("--- OWNER_ID 読み込み前 ---", file=sys.stdout)
        # if os.getenv('DISCORD_OWNER_ID'):
        #     try:
        #         OWNER_ID = int(os.getenv('DISCORD_OWNER_ID'))
        #         print(f"製作者IDが環境変数から {OWNER_ID} に設定されました。", file=sys.stdout)
        #     except ValueError:
        #         print("警告: 環境変数 DISCORD_OWNER_ID が無効な数値です。製作者IDは設定されません。", file=sys.stdout)
        #         OWNER_ID = None
        # else:
        #     print("警告: 環境変数 DISCORD_OWNER_ID が設定されていません。製作者専用コマンドは機能しません。", file=sys.stdout)
        #     OWNER_ID = None
        # print("--- OWNER_ID 読み込み後 ---", file=sys.stdout)

        # if is_maintenance_mode:
        #     await bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
        # else:
        #     await bot.change_presence(activity=discord.Game(name="プロセカ！ | !help_proseka"))
        # print("--- ステータス変更後 ---", file=sys.stdout)

        # try:
        #     await bot.load_extension('admin_commands')
        #     print("admin_commands コグをロードしました。", file=sys.stdout)
        #     # ボットがWeb ServiceではなくBackground Workerとしてデプロイされているため、
        #     # Flaskは不要で、純粋なボット動作になるはずです。
        #     # スラッシュコマンドを同期 (treeはcommands.Botに自動で付与される)
        #     await bot.tree.sync() # <-- treeを明示的に呼び出す
        #     print("スラッシュコマンドをDiscordに同期しました。", file=sys.stdout)
        # except Exception as e:
        #     print(f"admin_commands コグのロード中またはコマンド同期中にエラーが発生しました: {e}", file=sys.stderr)
        #     traceback.print_exc(file=sys.stderr)

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