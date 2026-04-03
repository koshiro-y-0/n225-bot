"""
generate_weekly.py
週間サマリーレポートを生成するモジュール
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path
from src.common.tz import now_jst
from jinja2 import Environment, FileSystemLoader


from src.common.data_store import load_week_data
from src.ueda.fetch_detail import ECONOMIC_EVENTS

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

# 植田総裁口調の週間コメント
WEEKLY_COMMENTS = {
    "stable": "今週も市場は概ね安定的に推移しました。\n 引き続き経済・物価の動向を注意深く見極めてまいります。",
    "yen_weak": "今週は円安方向への動きが目立ちました。\n 為替市場の動向とその経済への影響を注視してまいります。",
    "yen_strong": "今週は円高方向への動きが見られました。\n 輸出企業への影響を含め、経済への波及を注視してまいります。",
    "volatile": "今週は為替の変動が大きい一週間でした。\n 市場の安定に向け、適切に対応してまいります。",
}


def _determine_weekly_comment(week_change: float, week_range: float) -> str:
    """週間の為替動向に応じてコメントを選択する"""
    if week_range >= 3.0:
        return WEEKLY_COMMENTS["volatile"]
    if week_change >= 1.5:
        return WEEKLY_COMMENTS["yen_weak"]
    if week_change <= -1.5:
        return WEEKLY_COMMENTS["yen_strong"]
    return WEEKLY_COMMENTS["stable"]


def _get_next_week_events(target_date: datetime = None) -> list[dict]:
    """来週の注目イベントを取得する"""
    if target_date is None:
        target_date = now_jst()

    # timezone-naive に統一して日付比較
    if target_date.tzinfo is not None:
        target_date = target_date.replace(tzinfo=None)

    # 来週の月曜〜金曜
    next_monday = target_date + timedelta(days=(7 - target_date.weekday()))
    next_friday = next_monday + timedelta(days=4)

    events = []
    for ev in ECONOMIC_EVENTS:
        try:
            ev_date = datetime.strptime(ev["date"], "%Y年%-m月%-d日")
        except ValueError:
            # フォーマットが合わない場合はスキップ
            try:
                # 別フォーマットも試行
                for fmt in ["%Y年%m月%d日", "%Y年%-m月%-d日"]:
                    try:
                        ev_date = datetime.strptime(ev["date"], fmt)
                        break
                    except ValueError:
                        continue
                else:
                    continue
            except Exception:
                continue

        if next_monday <= ev_date <= next_friday:
            weekday = WEEKDAY_JP[ev_date.weekday()]
            events.append({
                "date": ev["date"],
                "weekday": weekday,
                "event": ev["event"],
            })

    return events


def build_weekly_summary(week_data: list[dict], target_date: datetime = None) -> dict:
    """
    週間サマリーデータを構築する。
    Args:
        week_data: data_store.load_week_data() の返り値
        target_date: 基準日
    Returns:
        テンプレートに渡すコンテキスト辞書
    """
    if target_date is None:
        target_date = now_jst()

    if not week_data:
        return {
            "has_data": False,
            "week_start": "",
            "week_end": "",
        }

    # 週間データから集計
    usdjpy_list = [d["usdjpy"] for d in week_data]
    eurjpy_list = [d.get("eurjpy", 0) for d in week_data]

    week_start_date = week_data[0]["date"]
    week_end_date = week_data[-1]["date"]

    usdjpy_open = usdjpy_list[0]
    usdjpy_close = usdjpy_list[-1]
    week_change = usdjpy_close - usdjpy_open
    week_change_pct = (week_change / usdjpy_open) * 100

    usdjpy_high = max(usdjpy_list)
    usdjpy_low = min(usdjpy_list)
    usdjpy_high_date = week_data[usdjpy_list.index(usdjpy_high)]["date"]
    usdjpy_low_date = week_data[usdjpy_list.index(usdjpy_low)]["date"]
    week_range = usdjpy_high - usdjpy_low

    # 高値/安値の日付を短縮表示
    high_date_short = datetime.strptime(usdjpy_high_date, "%Y-%m-%d").strftime("%-m/%-d")
    low_date_short = datetime.strptime(usdjpy_low_date, "%Y-%m-%d").strftime("%-m/%-d")

    # 週初/週末の日付を表示用に変換
    ws = datetime.strptime(week_start_date, "%Y-%m-%d")
    we = datetime.strptime(week_end_date, "%Y-%m-%d")
    week_start_display = ws.strftime("%Y年%-m月%-d日")
    week_end_display = we.strftime("%-m月%-d日")

    # 政策金利・CPI・短観（最新値）
    latest = week_data[-1]
    policy_rate = latest.get("policy_rate", 0.50)
    cpi_total = latest.get("cpi_total", 0)
    cpi_core = latest.get("cpi_core", 0)
    tankan_di = latest.get("tankan_di", 0)

    # 来週の注目イベント
    next_events = _get_next_week_events(target_date)

    # コメント
    comment = _determine_weekly_comment(week_change, week_range)

    return {
        "has_data": True,
        "week_start": week_start_display,
        "week_end": week_end_display,
        "usdjpy_open": usdjpy_open,
        "usdjpy_close": usdjpy_close,
        "week_change": week_change,
        "week_change_pct": week_change_pct,
        "usdjpy_high": usdjpy_high,
        "usdjpy_low": usdjpy_low,
        "high_date": high_date_short,
        "low_date": low_date_short,
        "week_range": week_range,
        "policy_rate": policy_rate,
        "cpi_total": cpi_total,
        "cpi_core": cpi_core,
        "tankan_di": tankan_di,
        "next_events": next_events,
        "weekly_comment": comment,
    }


def generate_weekly_report(week_data: list[dict], target_date: datetime = None) -> str:
    """
    週間サマリーレポートを生成する。
    Args:
        week_data: data_store.load_week_data() の返り値
        target_date: 基準日
    Returns:
        レポート文字列
    """
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("weekly_summary.j2")
    context = build_weekly_summary(week_data, target_date)
    return template.render(context)


if __name__ == "__main__":
    dummy_week = [
        {"date": "2026-03-09", "weekday": "月", "usdjpy": 151.20, "eurjpy": 162.0, "usdjpy_prev": 150.80, "policy_rate": 0.50, "cpi_total": 3.2, "cpi_core": 2.8, "tankan_di": 12},
        {"date": "2026-03-10", "weekday": "火", "usdjpy": 150.90, "eurjpy": 161.5, "usdjpy_prev": 151.20, "policy_rate": 0.50, "cpi_total": 3.2, "cpi_core": 2.8, "tankan_di": 12},
        {"date": "2026-03-11", "weekday": "水", "usdjpy": 153.50, "eurjpy": 164.0, "usdjpy_prev": 150.90, "policy_rate": 0.50, "cpi_total": 3.2, "cpi_core": 2.8, "tankan_di": 12},
        {"date": "2026-03-12", "weekday": "木", "usdjpy": 152.10, "eurjpy": 163.2, "usdjpy_prev": 153.50, "policy_rate": 0.50, "cpi_total": 3.2, "cpi_core": 2.8, "tankan_di": 12},
        {"date": "2026-03-13", "weekday": "金", "usdjpy": 152.80, "eurjpy": 163.8, "usdjpy_prev": 152.10, "policy_rate": 0.50, "cpi_total": 3.2, "cpi_core": 2.8, "tankan_di": 12},
    ]
    print(generate_weekly_report(dummy_week))
