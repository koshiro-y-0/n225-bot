"""
dispatcher.py
統合エントリーポイント — GitHub Actions から呼び出される
UedaBot（為替/金利/CPI）と 日経モジュールを別メッセージで配信する
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
from src.nikkei.nikkei_module import fetch_nikkei_data

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
TARGET_HOUR = 9
TARGET_MINUTE = 10


def _wait_until_target_time():
    """09:10 JST まで待機する（最大35分）

    Tokyo市場が9:00 JSTに開場すると yfinance の ^N225 履歴データが
    前日バーを反映する。9:10 まで待つことで stale なデータを掴むリスクを排除。
    """
    now = now_jst()
    if now.hour > TARGET_HOUR or (now.hour == TARGET_HOUR and now.minute >= TARGET_MINUTE):
        return
    target = now.replace(hour=TARGET_HOUR, minute=TARGET_MINUTE, second=0, microsecond=0)
    wait_seconds = (target - now).total_seconds()
    if 0 < wait_seconds <= 2100:
        print(f"[INFO] 09:10 JST まで {int(wait_seconds)} 秒待機します...")
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


def main():
    # 0. 08:30 JST まで待機
    _wait_until_target_time()

    is_monday = now_jst().weekday() == 0
    print(f"[INFO] 配信開始 (月曜判定: {is_monday})")

    # 1. UedaBot レポート生成
    # アラートはメインレポート内にインライン表示されるため、別送はしない
    # （report.j2 の forex_alert / policy_rate_changed で「⚠️ 急変注意」等を表示）
    print("[INFO] UedaBot レポート生成中...")
    ueda_report, ueda_data, _ = build_ueda_report()

    # 2. 日経モジュール レポート生成
    print("[INFO] 日経モジュール レポート生成中...")
    nikkei_data = fetch_nikkei_data()
    nikkei_block = render_nikkei_block(nikkei_data, is_monday)

    # 3. UedaBot レポート（為替/金利/CPI）を送信
    print("--- UedaBot レポート ---")
    print(ueda_report)
    print("------------------------")
    send_all(ueda_report, with_quick_reply=True)

    # 4. 少し間隔を空けて日経レポートを別メッセージで送信
    time.sleep(2)
    print("--- 日経レポート ---")
    print(nikkei_block)
    print("--------------------")
    send_all(nikkei_block)

    # 5. 日次データをCSVに蓄積（UedaBot分）
    save_daily(ueda_data)


if __name__ == "__main__":
    main()
