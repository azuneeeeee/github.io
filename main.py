import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import traceback
import logging
import sys
import asyncio

# admin_commands コグをインポート
# is_maintenance_mode は admin_commands.py から共有されます
from admin_commands import is_maintenance_mode 

load_dotenv()

# --- ロギング設定 ---
# 本番運用向けにINFOレベルに設定。必要に応じてDEBUGに変更してください。
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(name)s: %(message)s',
                    stream=sys.stdout)

logging.getLogger('discord').setLevel(logging.INFO)
logging.getLogger('websockets').setLevel(logging.INFO)

# --- asyncioの未捕捉例外ハンドラ ---
def handle_exception(loop, context):
    msg = context.get("exception", context["message"])
    logging.error(f"非同期処理で未捕捉の例外が発生しました: {msg}")
    if "exception" in context:
        logging.error("トレースバック:", exc_info=context["exception"])
    # 状況によってはここで sys.exit(1) を呼び出すことも可能ですが、まずはログ記録に専念

# --- Discordクライアントのインテント設定 ---
# 本番運用時は必要なインテントのみに絞ることを強く推奨します (セキュリティとパフォーマンスのため)。
# 例: intents = discord.Intents.default()
# intents.message_content = True
# intents.members = True # メンバー情報を取得する場合
intents = discord.Intents.all() # デバッグ・テストのため、当面は all() のままにしておく

# --- ボットのインスタンス作成 ---
bot = commands.Bot(command_prefix='!', intents=intents)

# --- on_readyイベントハンドラ ---
@bot.event
async def on_ready():
    print("--- on_ready イベント開始 ---", file=sys.stdout)
    try:
        print(f'Logged in as {bot.user.name}', file=sys.stdout)
        print(f'Bot ID: {bot.user.id}', file=sys.stdout)
        print('------', file=sys.stdout)
        print("ボットは正常に起動し、Discordに接続しました！", file=sys.stdout)

        # ステータス変更処理
        if is_maintenance_mode:
            await bot.change_presence(activity=discord.Game(name="メンテナンス中... | !help_proseka"))
        else:
            await bot.change_presence(activity=discord.Game(name="プロセカ！ | !help_proseka"))
        print("--- ステータス設定後 ---", file=sys.stdout)

        # admin_commands コグのロードとスラッシュコマンドの同期
        try:
            await bot.load_extension('admin_commands')
            print("admin_commands コグをロードしました。", file=sys.stdout)
            await bot.tree.sync() # スラッシュコマンドをDiscordに同期
            print("スラッシュコマンドをDiscordに同期しました。", file=sys.stdout)
        except Exception as e:
            print(f"!!! admin_commands コグのロード中またはコマンド同期中にエラーが発生しました: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)

        print("--- on_ready イベント終了 ---", file=sys.stdout)

    except Exception as e:
        print(f"!!! on_ready イベント内で予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

# --- ボットの起動処理 ---
if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_exception)

    print("デバッグ: Discord Botを起動します。", file=sys.stdout)
    try:
        # bot.run() を直接呼び出す (以前の低レベルな分解は不要)
        bot.run(os.getenv('DISCORD_BOT_TOKEN'))
    except discord.LoginFailure:
        print("致命的エラー: Discordトークン認証に失敗しました。DISCORD_BOT_TOKEN を確認してください。", file=sys.stderr)
        sys.exit(1) # トークンが正しくない場合は終了
    except Exception as e:
        print(f"致命的エラー: Discord Botの実行中に予期せぬエラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
    print("デバッグ: bot.run() 呼び出し後（ここまで来たらボットプロセスが意図せず終了）", file=sys.stdout)