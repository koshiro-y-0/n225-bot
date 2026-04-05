"""
nikkei_alert.py
日経平均・EPSの節目アラート判定と送信
GitHub Actions の alert.yml から30分おきに呼び出される
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from jinja2 import Environment, FileSystemLoader

from src.common.notify import send_line
from src.nikkei.nikkei_module import (
    fetch_nikkei_data,
    check_nikkei_milestones,
    check_eps_milestones,
)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def render_alert(alert_type: str, alert_info: dict, data: dict) -> str:
    """節目アラートメッセージを生成"""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("nikkei_alert.j2")
    context = {
        "alert_type": alert_type,
        "milestone": alert_info["milestone"],
        "direction": alert_info["direction"],
        "current": alert_info["current"],
        "diff_pct": data.get("nikkei_diff_pct", 0.0),
        "nikkei_close": data.get("nikkei_close", 0.0),
        "per": data.get("per", 0.0),
        "eps": data.get("eps", 0.0),
    }
    return template.render(**context)


def main():
    """
    節目アラートのメインルーチン。
    日経平均・EPSが節目を超えた場合のみ通知を送信する。
    """
    print("[INFO] 日経節目アラートチェック開始...")

    data = fetch_nikkei_data()
    print(f"[INFO] 日経平均: {data['nikkei_close']:,.0f}円 / EPS: {data['eps']:,.0f}円")

    sent = False

    # 日経平均の節目チェック
    nikkei_alert = check_nikkei_milestones(data["nikkei_close"])
    if nikkei_alert:
        msg = render_alert("nikkei", nikkei_alert, data)
        print(f"[ALERT] 日経平均 {nikkei_alert['direction']}: {nikkei_alert['milestone']:,}円を{nikkei_alert['direction']}")
        print(msg)
        send_line(msg)
        sent = True

    # EPS の節目チェック
    eps_alert = check_eps_milestones(data["eps"])
    if eps_alert:
        msg = render_alert("eps", eps_alert, data)
        print(f"[ALERT] EPS {eps_alert['direction']}: {eps_alert['milestone']:,}円を{eps_alert['direction']}")
        print(msg)
        send_line(msg)
        sent = True

    if not sent:
        print("[INFO] 節目変化なし")


if __name__ == "__main__":
    main()
