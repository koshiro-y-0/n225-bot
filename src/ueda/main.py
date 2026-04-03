"""
main.py
GitHub Actions から呼び出されるエントリーポイント
fetch → generate → notify の一連の処理を実行する
"""

import sys
from pathlib import Path

# プロジェクトルートをモジュール検索パスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


import time
from src.common.tz import now_jst
from src.ueda.fetch_indicators import fetch_all, fetch_review_and_outlook
from src.ueda.generate_report import generate_report, generate_alert
from src.common.notify import send_all, check_alerts
from src.common.data_store import save_daily

TARGET_HOUR = 8
TARGET_MINUTE = 30


def _wait_until_target_time():
    """08:30 JST まで待機する（最大35分）"""
    now = now_jst()
    target_hour = TARGET_HOUR
    target_minute = TARGET_MINUTE

    if now.hour == target_hour and now.minute >= target_minute:
        return  # 既に過ぎている
    if now.hour > target_hour:
        return  # 既に過ぎている

    target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    wait_seconds = (target - now).total_seconds()

    if wait_seconds > 0 and wait_seconds <= 2100:  # 最大35分
        print(f"[INFO] 08:30 JST まで {int(wait_seconds)} 秒待機します...")
        time.sleep(wait_seconds)
        print(f"[INFO] 08:30 JST になりました。レポート配信を開始します。")


def main():
    # 0. 08:30 JST まで待機
    _wait_until_target_time()

    # 1. 経済指標を取得
    data = fetch_all()

    # 2. アラート確認（緊急通知が必要か）
    alerts = check_alerts(data)
    for alert_type in alerts:
        alert_msg = generate_alert(alert_type, data)
        print(f"[ALERT] {alert_type}: 送信します")
        send_all(alert_msg)

    # 3. 昨日の振り返り・今日の見通しを生成
    review_data = fetch_review_and_outlook(data)

    # 4. 通常レポートを生成して送信（振り返り・見通し付き）
    report = generate_report(data, review_data)
    print("--- 生成されたレポート ---")
    print(report)
    print("-------------------------")
    send_all(report, with_quick_reply=True)

    # 5. 日次データをCSVに蓄積
    save_daily(data)


if __name__ == "__main__":
    main()
