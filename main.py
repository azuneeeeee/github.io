import sys
import os

# 強制ログファイル出力は今回は Render のメインログに直接出すので、
# sys.stdout のリダイレクトはしません。

print("デバッグ: main.py 実行開始 - Discordインポートテスト。", file=sys.__stdout__)

try:
    # discord モジュールのインポートだけを試す
    import discord
    print("デバッグ: discord モジュールのインポートに成功しました。", file=sys.__stdout__)

    # discord.ext.commands モジュールのインポートだけを試す
    from discord.ext import commands
    print("デバッグ: discord.ext.commands モジュールのインポートに成功しました。", file=sys.__stdout__)

    # ここまで来たら、ボットのインスタンス作成も試す
    intents = discord.Intents.default() # 最低限のインテントで試す
    bot = commands.Bot(command_prefix='!', intents=intents)
    print("デバッグ: ボットインスタンスの作成に成功しました。", file=sys.__stdout__)

except ImportError as e:
    print(f"致命的エラー: モジュールのインポートに失敗しました: {e}", file=sys.__stderr__)
    print(f"デバッグ: 環境変数 PATH: {os.getenv('PATH')}", file=sys.__stderr__)
    print(f"デバッグ: sys.path: {sys.path}", file=sys.__stderr__)
    sys.exit(1)
except Exception as e:
    print(f"致命的エラー: 予期せぬエラーが発生しました: {e}", file=sys.__stderr__)
    import traceback
    traceback.print_exc(file=sys.__stderr__)
    sys.exit(1)

print("デバッグ: main.py 実行終了 - Discordインポートテスト。", file=sys.__stdout__)