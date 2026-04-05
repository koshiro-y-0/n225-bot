"""
dispatcher.py
統合エントリーポイント — GitHub Actions から呼び出される
UedaBot + 日経モジュールを統合して1通の配信にまとめる
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from jinja2 import Environment, FileSystemLoader

from src.common.tz import now_jst
from src.common.notify import send_all
from src.common.data_store import save_daily
from src.ueda.main import build_ueda_report
from src.ueda.generate_report import generate_alert
from src.nikkei.nikkei_module import fetch_nikkei_data

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
TARGET_HOUR = 8
TARGET_MINUTE = 30


def _wait_until_target_time():
    """08:30 JST まで待機する（最大35分）"""
    now = now_jst()
    if now.hour > TARGET_HOUR or (now.hour == TARGET_HOUR and now.minute >= TARGET_MINUTE):
        return
    target = now.replace(hour=TARGET_HOUR, minute=TARGET_MINUTE, second=0, microsecond=0)
    wait_seconds = (target - now).total_seconds()
    if 0 < wait_seconds <= 2100:
        print(f"[INFO] 08:30 JST まで {int(wait_seconds)} 秒待機します...")
        time.sleep(wait_seconds)


def _get_prev_friday_date() -> str:
    """月曜日配信時に表示する「先週金曜」の日付文字列を返す"""
    now = now_jst()
    # 月曜(weekday=0)なら3日前が金曜
    days_back = 3 if now.weekday() == 0 else 1
    prev = now.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    prev = prev - timedelta(days=days_back)
    return prev.strftime("%Y年%-m月%-d日")


def render_nikkei_block(data: dict, is_monday: bool) -> str:
    """daily_nikkei.j2 をレンダリング"""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("daily_nikkei.j2")
    prev_date = _get_prev_friday_date() if is_monday else ""
    return template.render(is_monday=is_monday, prev_date=prev_date, **data)


def render_integrated(nikkei_block: str, ueda_block: str) -> str:
    """統合テンプレートをレンダリング"""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("daily_integrated.j2")
    return template.render(nikkei_block=nikkei_block, ueda_block=ueda_block)


def main():
    # 0. 08:30 JST まで待機
    _wait_until_target_time()

    is_monday = now_jst().weekday() == 0
    print(f"[INFO] 配信開始 (月曜判定: {is_monday})")

    # 1. UedaBot レポート生成
    print("[INFO] UedaBot レポート生成中...")
    ueda_report, ueda_data, ueda_alerts = build_ueda_report()

    # 2. UedaBot アラート（為替/金利/CPI）は先に個別送信
    for alert_type in ueda_alerts:
        alert_msg = generate_alert(alert_type, ueda_data)
        print(f"[ALERT] {alert_type}: 送信します")
        send_all(alert_msg)

    # 3. 日経モジュール レポート生成
    print("[INFO] 日経モジュール レポート生成中...")
    nikkei_data = fetch_nikkei_data()
    nikkei_block = render_nikkei_block(nikkei_data, is_monday)

    # 4. 統合メッセージを組み立てて送信
    integrated = render_integrated(nikkei_block, ueda_report)
    print("--- 統合メッセージ ---")
    print(integrated)
    print("----------------------")
    send_all(integrated, with_quick_reply=True)

    # 5. 日次データをCSVに蓄積（UedaBot分）
    save_daily(ueda_data)


if __name__ == "__main__":
    main()
