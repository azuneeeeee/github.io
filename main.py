import sys
# 強制ログファイル出力開始
try:
    log_file_path = "/tmp/bot_startup_debug.log"
    sys.stdout = open(log_file_path, "w", encoding="utf-8")
    sys.stderr = open(log_file_path, "w", encoding="utf-8")
    print("デバッグ: 強制ログファイル出力開始。", file=sys.stdout)
except Exception as e:
    print(f"致命的エラー: ログファイルを開けませんでした: {e}", file=sys.__stdout__)
    sys.exit(1)

# ここからテストコード
import os
from dotenv import load_dotenv

print("デバッグ: main.py 実行開始 - ステップ1", file=sys.stdout)

try:
    load_dotenv()
    print("デバッグ: .env ファイルをロードしました。", file=sys.stdout)
    token = os.getenv('DISCORD_BOT_TOKEN')
    if token:
        print(f"デバッグ: トークンを読み込みました。長さ: {len(token)} 文字。", file=sys.stdout)
    else:
        print("デバッグ: トークンが見つかりません。", file=sys.stdout)
except Exception as e:
    print(f"致命的エラー: 初期ロード中にエラー: {e}", file=sys.stderr)
    sys.exit(1)

print("デバッグ: main.py 実行終了 - ステップ1", file=sys.stdout)

# ログファイルクローズ処理
if sys.stdout is not sys.__stdout__:
    print("デバッグ: 強制ログファイル出力終了。", file=sys.stdout)
    sys.stdout.close()
    sys.stderr.close()
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__