import sys
import os
import time

# --- 強制ログファイル出力開始 (修正版) ---
# プロセス開始直後にログファイルを開き、標準出力もそこにリダイレクト
# ただし、エラーが発生した場合は元々の stdout に出力する
original_stdout = sys.__stdout__
original_stderr = sys.__stderr__
log_file_opened_successfully = False

try:
    log_file_path = "/tmp/bot_startup_debug.log" 
    # 'w' (書き込みモード) で毎回新規作成
    sys.stdout = open(log_file_path, "w", encoding="utf-8")
    sys.stderr = open(log_file_path, "w", encoding="utf-8")
    log_file_opened_successfully = True

    print("デバッグ: 強制ログファイル出力開始。Pythonの起動テストを行います。", file=sys.stdout)
    print("デバッグ: sys.stdout と sys.stderr がファイルにリダイレクトされました。", file=sys.stdout)

except Exception as e:
    # ログファイルを開くこと自体に失敗した場合、元の標準出力に出力
    print(f"致命的エラー: ログファイルを開けませんでした: {e}", file=original_stderr) 
    sys.exit(1) # プロセスを終了

# --- ここから究極にシンプルなテストコード ---
try:
    if log_file_opened_successfully:
        print("デバッグ: main.py 実行開始 - 究極シンプルテスト。", file=sys.stdout)
    else:
        # ここには到達しないはずだが念のため
        print("デバッグ: main.py 実行開始 - 強制ログファイル開けず。", file=original_stdout)

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
    # テストコード内でエラーが発生した場合
    print(f"致命的エラー: 究極シンプルテスト中にエラーが発生しました: {e}", file=sys.stderr)
    sys.exit(1)

finally:
    # ログファイルクローズ処理
    if log_file_opened_successfully: # 正常に開けていればクローズ
        print("デバッグ: 強制ログファイル出力終了。", file=sys.stdout)
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = original_stdout # 元に戻す
        sys.stderr = original_stderr
    # このメッセージは常に元の標準出力に出る
    print("デバッグ: プロセス終了前の最終メッセージ。", file=original_stdout)