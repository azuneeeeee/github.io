import os
import sys
from dotenv import load_dotenv

print("デバッグ: main.py 実行開始 - 環境変数テスト。", file=sys.stdout)

try:
    load_dotenv()
    print("デバッグ: .env ファイルをロードしました。", file=sys.stdout)

    token = os.getenv('DISCORD_BOT_TOKEN')
    if token:
        print(f"デバッグ: トークンを読み込みました。長さ: {len(token)} 文字。", file=sys.stdout)
        # トークンの最初の数文字と最後の数文字だけ表示して、正しく読み込めているか確認
        print(f"デバッグ: トークンの一部: {token[:5]}...{token[-5:]}", file=sys.stdout)
    else:
        print("致命的エラー: 環境変数 'DISCORD_BOT_TOKEN' が見つかりません。", file=sys.stderr)
        sys.exit(1)

except Exception as e:
    print(f"致命的エラー: 環境変数の読み込み中にエラーが発生しました: {e}", file=sys.stderr)
    sys.exit(1)

print("デバッグ: 環境変数テストを終了しました。", file=sys.stdout)

# このテストが成功したら、ボットの残りのコードをここに記述していく
# ただし、今はテストのため、これ以上は書かない