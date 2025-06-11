import json
import os
import logging

logger = logging.getLogger(__name__)

MAINTENANCE_FILE = "maintenance_status.json"

def load_maintenance_status() -> bool:
    """
    maintenance_status.json からメンテナンスモードの状態を読み込みます。
    ファイルが存在しない、または読み込みに失敗した場合は False を返します。
    """
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
            logger.error(f"エラー: {MAINTENANCE_FILE} の読み込みに失敗しました。デフォルトの False を使用します。")
            return False
        except Exception as e:
            logger.error(f"エラー: {MAINTENANCE_FILE} のロード中に予期せぬエラーが発生しました: {e}")
            return False
    logger.info(f"デバッグ: {MAINTENANCE_FILE} が存在しないため、デフォルトの False を使用します。")
    return False

def save_maintenance_status(status: bool):
    """
    メンテナンスモードの状態を maintenance_status.json に保存します。
    """
    try:
        with open(MAINTENANCE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'is_maintenance_mode': status}, f, indent=4)
        logger.info(f"デバッグ: メンテナンスモードの状態を {MAINTENANCE_FILE} に保存しました: {status}")
    except Exception as e:
        logger.error(f"エラー: メンテナンスモードの状態を {MAINTENANCE_FILE} に保存できませんでした: {e}")

# (注意: _is_maintenance_mode = load_maintenance_status() のような初期ロードはここには置かず、
# 各モジュールで必要な時に呼び出すようにします)