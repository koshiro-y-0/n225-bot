"""
dispatcher.py
統合エントリーポイント — GitHub Actions から呼び出される
曜日判定・モジュール選択・メッセージ統合を行う
"""

import sys
from pathlib import Path

# プロジェクトルートをモジュール検索パスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    """
    定時配信のメインルーチン（平日 8:30 JST）
    Phase 3 で実装予定:
    - 曜日判定（月曜 → 金曜終値配信）
    - nikkei_module 呼出し
    - ueda_module 呼出し
    - メッセージ統合
    - LINE 送信
    """
    # Phase 3 までは UedaBot の既存 main.py を直接呼び出す
    from src.ueda.main import main as ueda_main
    ueda_main()


if __name__ == "__main__":
    main()
