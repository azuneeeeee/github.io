import json
import os
import logging

logger = logging.getLogger(__name__)

# プロジェクトのルートディレクトリにファイルを保存するよう絶対パスを指定
# Railwayでは /app がルートディレクトリになるため、それに合わせる
# RAILWAY_VOLUME_MOUNT_PATH 環境変数が設定されていない場合は、一般的なボリュームパス '/data' を使用
MAINTENANCE_FILE = os.path.join(os.getenv('RAILWAY_VOLUME_MOUNT_PATH', '/data'), "maintenance_status.json")

def load_maintenance_status() -> bool:
    """
    maintenance_status.json からメンテナンスモードの状態を読み込みます。
    ファイルが存在しない、または読み込みに失敗した場合は False を返します。
    """
    logger.debug(f"デバッグ: メンテナンスモードの状態を {MAINTENANCE_FILE} からロードしようとしています。")
    if os.path.exists(MAINTENANCE_FILE):
        try:
            with open(MAINTENANCE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'is_maintenance_mode' in data and isinstance(data['is_maintenance_mode'], bool):
                    logger.info(f"デバッグ: メンテナンスモードの状態を {MAINTENANCE_FILE} からロードしました: {data['is_maintenance_mode']}")
                    return data['is_maintenance_mode']
                else:
                    logger.warning(f"警告: {MAINTENANCE_FILE} の形式が不正です。デフォルトの False を使用します。")
                    return False
        except json.JSONDecodeError:
            logger.error(f"エラー: {MAINTENANCE_FILE} の読み込みに失敗しました（JSON形式エラー）。デフォルトの False を使用します。")
            return False
        except Exception as e:
            logger.error(f"エラー: {MAINTENANCE_FILE} のロード中に予期せぬエラーが発生しました: {e}", exc_info=True) # exc_info=Trueで詳細なトレースバックを出力
            return False
    logger.info(f"デバッグ: {MAINTENANCE_FILE} が存在しないため、デフォルトの False を使用します。")
    return False

def save_maintenance_status(status: bool):
    """
    メンテナンスモードの状態を maintenance_status.json に保存します。
    """
    logger.debug(f"デバッグ: メンテナンスモードの状態を {MAINTENANCE_FILE} に保存しようとしています: {status}")
    try:
        # ★ 変更点: ディレクトリが存在しない場合に作成する処理を追加 ★
        os.makedirs(os.path.dirname(MAINTENANCE_FILE), exist_ok=True)
        
        with open(MAINTENANCE_FILE, 'w', encoding='utf-8') as f:
            # ★ 変更点: ensure_ascii=False を追加し、日本語が正しく保存されるようにする ★
            json.dump({'is_maintenance_mode': status}, f, indent=4, ensure_ascii=False)
        logger.info(f"デバッグ: メンテナンスモードの状態を {MAINTENANCE_FILE} に保存しました: {status}")
    except Exception as e:
        logger.error(f"エラー: メンテナンスモードの状態を {MAINTENANCE_FILE} に保存できませんでした: {e}", exc_info=True) # exc_info=Trueで詳細なトレースバックを出力