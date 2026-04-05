"""
weekly_report.py
日経モジュールの週次レポート生成とLINE送信
金曜15:30 JST に weekly.yml から呼び出される
"""

import os
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from jinja2 import Environment, FileSystemLoader

from src.common.notify import send_line, send_line_image
from src.common.tz import now_jst
from src.nikkei.fetch_nikkei import fetch_nikkei225_weekly
from src.nikkei.jpx_scraper import fetch_per_pbr, calc_eps
from src.nikkei.generate_chart import generate_nikkei_chart

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def compute_weekly_stats(week_data: list, per: float) -> dict:
    """週間データから騰落額・率・PER/EPS変化を算出"""
    if not week_data or len(week_data) < 2:
        return {}

    first = week_data[0]
    last = week_data[-1]
    week_diff = round(last["close"] - first["close"], 2)
    week_diff_pct = round((week_diff / first["close"]) * 100, 2) if first["close"] else 0.0
    high = round(max(d["close"] for d in week_data), 2)
    low = round(min(d["close"] for d in week_data), 2)
    eps = calc_eps(last["close"], per)

    return {
        "week_start_date": first["date"],
        "week_end_date": last["date"],
        "week_open": first["close"],
        "week_close": last["close"],
        "week_diff": week_diff,
        "week_diff_pct": week_diff_pct,
        "week_high": high,
        "week_low": low,
        "per": per,
        "eps": eps,
    }


def render_weekly_report(stats: dict, per_data: dict) -> str:
    """週次テンプレートをレンダリング"""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("weekly_nikkei.j2")
    now = now_jst()
    return template.render(
        fetch_date=now.strftime("%Y年%-m月%-d日"),
        per_data_month=per_data.get("data_month", ""),
        per_comment=per_data.get("per_comment", ""),
        **stats,
    )


def save_chart_for_push(chart_path: str) -> str:
    """生成したチャートを data/ にコピーして raw URL を返す"""
    DATA_DIR.mkdir(exist_ok=True)
    filename = f"nikkei_weekly_{now_jst().strftime('%Y%m%d')}.png"
    dest = DATA_DIR / filename
    shutil.copy2(chart_path, dest)

    repo = os.getenv("GITHUB_REPOSITORY", "koshiro-y-0/n225-bot")
    raw_url = f"https://raw.githubusercontent.com/{repo}/main/data/{filename}"
    print(f"[OK] 日経チャート画像を保存: {dest}")
    print(f"[INFO] 画像URL（push後に有効）: {raw_url}")
    return str(dest)


def main():
    print("[INFO] 日経週次レポート生成開始...")

    # 1. 週間データ取得
    week_data = fetch_nikkei225_weekly(days=5)
    if not week_data:
        print("[WARN] 週次データ取得失敗。終了します。")
        return

    # 2. PER/EPS 取得
    per_data = fetch_per_pbr()

    # 3. 週次統計算出
    stats = compute_weekly_stats(week_data, per_data["per"])
    if not stats:
        print("[WARN] 週次統計の算出失敗。終了します。")
        return

    # 4. テキストレポート生成
    report = render_weekly_report(stats, per_data)
    print("--- 日経週次レポート ---")
    print(report)
    print("------------------------")

    # 5. テキスト送信
    send_line(report)

    # 6. チャート生成
    chart_path = generate_nikkei_chart(week_data)
    if chart_path:
        save_chart_for_push(chart_path)
        try:
            os.unlink(chart_path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
