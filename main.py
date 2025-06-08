import sys
import os
import time

# --- 強制ログファイル出力開始 ---
# プロセス開始直後にログファイルを開き、標準出力もそこにリダイレクト
try:
    log_file_path = "/tmp/bot_startup_debug.log" 
    # 'a' (追記モード) ではなく 'w' (書き込みモード) を使うことで、毎回ファイルを新規作成
    sys.stdout = open(log_file_path, "w", encoding="utf-8")
    sys.stderr = open(log_file_path, "w", encoding="utf-8")

    print("デバッグ: 強制ログファイル出力開始。Pythonの起動テストを行います。", file=sys.stdout)
    print("デバッグ: sys.stdout と sys.stderr がファイルにリダイレクトされました。", file=sys.stdout)

except Exception as e:
    # ログファイルを開くこと自体に失敗した場合の最終手段。Renderの通常のログに出ることを期待。
    print(f"致命的エラー: ログファイルを開けませんでした: {e}", file=sys.__stdout__) 
    sys.exit(1) # プロセスを終了

# --- ここから究極にシンプルなテストコード ---
try:
    print("デバッグ: main.py 実行開始 - 究極シンプルテスト。", file=sys.stdout)

    # 簡単な変数代入と計算
    a = 10
    b = 20
    c = a + b
    print(f"デバッグ: 計算結果: {c}", file=sys.stdout)

    # 短いスリープ（OSリソース消費を確認）
    time.sleep(1) 
    print("デバッグ: 1秒スリープしました。", file=sys.stdout)

    # 別のファイル書き込みテスト
    test_file_path = "/tmp/simple_test_output.txt"
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("このファイルはシンプルなPythonテストで作成されました。\n")
        f.write(f"現在の時刻: {time.ctime()}\n")
    print(f"デバッグ: テストファイル '{test_file_path}' を作成しました。", file=sys.stdout)

    print("デバッグ: main.py 実行終了 - 究極シンプルテスト。", file=sys.stdout)

except Exception as e:
    print(f"致命的エラー: 究極シンプルテスト中にエラーが発生しました: {e}", file=sys.stderr)
    sys.exit(1)

finally:
    # ログファイルクローズ処理
    if sys.stdout is not sys.__stdout__: 
        print("デバッグ: 強制ログファイル出力終了。", file=sys.stdout)
        sys.stdout.close()
        sys.stderr.close()
        # 元の標準出力に戻す (Renderのログに出るようになる)
        sys.stdout = sys.__stdout__ 
        sys.stderr = sys.__stderr__ 
    print("デバッグ: プロセス終了前の最終メッセージ。", file=sys.__stdout__) # 元のstdoutにも出力