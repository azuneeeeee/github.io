import sys
import os
import time

print("デバッグ: main.py 実行開始 - 最終ファイル書き込みテスト。", file=sys.__stdout__) # 直接元のstdoutに出力

try:
    test_file_path = "/tmp/render_test_file.log" # /tmp には試す
    
    # まずは /tmp への書き込みを試す
    try:
        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write("Render test: This file was created successfully in /tmp.\n")
            f.write(f"Current time: {time.ctime()}\n")
        print(f"デバッグ: 成功 - ファイル '{test_file_path}' を作成しました。", file=sys.__stdout__)
    except Exception as e:
        print(f"デバッグ: 失敗 - /tmp への書き込みエラー: {e}", file=sys.__stderr__)

    # もう一つ、異なる場所 (例: /opt/render/project/src/) への書き込みを試す
    # これはプロジェクトのルートディレクトリであることが多い
    project_root_test_file_path = "/opt/render/project/src/render_test_file_in_root.log"
    try:
        with open(project_root_test_file_path, "w", encoding="utf-8") as f:
            f.write("Render test: This file was created successfully in project root.\n")
            f.write(f"Current time: {time.ctime()}\n")
        print(f"デバッグ: 成功 - ファイル '{project_root_test_file_path}' を作成しました。", file=sys.__stdout__)
    except Exception as e:
        print(f"デバッグ: 失敗 - プロジェクトルートへの書き込みエラー: {e}", file=sys.__stderr__)


except Exception as e:
    print(f"致命的エラー: 全体で予期せぬエラーが発生しました: {e}", file=sys.__stderr__)
    sys.exit(1)

print("デバッグ: プロセス終了前の最終メッセージ。", file=sys.__stdout__) # これも常に元のstdoutに出る