"""
forex_alert.py
リアルタイム為替アラート — USD/JPY の急変を検知して通知する
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from src.common.tz import now_jst


import yfinance as yf
from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

# 閾値（デフォルト ±2円）
DEFAULT_THRESHOLD = 2.0


def get_current_usdjpy() -> float | None:
    """
    Yahoo Finance から現在の USD/JPY レートを取得する。
    Returns:
        現在のレート（取得失敗時 None）
    """
    try:
        ticker = yf.Ticker("USDJPY=X")
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        print(f"[ERROR] USD/JPY 取得エラー: {e}")
    return None


def get_last_rate() -> float | None:
    """
    CSV蓄積データから直近の USD/JPY レートを取得する。
    Returns:
        直近のレート（データなし時 None）
    """
    from src.common.data_store import load_recent
    recent = load_recent(1)
    if recent and "usdjpy" in recent[0]:
        return float(recent[0]["usdjpy"])
    return None


def check_alert(current: float, last: float, threshold: float = None) -> dict | None:
    """
    為替変動がアラート閾値を超えているか判定する。
    Args:
        current: 現在のレート
        last: 前回のレート
        threshold: 閾値（円）
    Returns:
        アラート情報の辞書（閾値内なら None）
    """
    if threshold is None:
        env_val = os.getenv("FOREX_ALERT_THRESHOLD", "").strip()
        threshold = float(env_val) if env_val else DEFAULT_THRESHOLD

    diff = current - last
    if abs(diff) <= threshold:
        return None

    pct = (diff / last) * 100
    direction = "円安" if diff > 0 else "円高"

    return {
        "current": current,
        "last": last,
        "diff": diff,
        "pct": pct,
        "direction": direction,
        "threshold": threshold,
        "timestamp": now_jst().strftime("%Y年%-m月%-d日 %H:%M"),
    }


def generate_alert_message(alert_data: dict) -> str:
    """
    アラートメッセージを生成する。
    Args:
        alert_data: check_alert() の返り値
    Returns:
        アラートメッセージ文字列
    """
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("forex_alert.j2")
    return template.render(alert_data)


def main():
    """
    為替アラートのメインルーチン。
    GitHub Actions から15分おきに呼び出される。
    """
    print("[INFO] 為替アラートチェック開始...")

    # 現在レート取得
    current = get_current_usdjpy()
    if current is None:
        print("[WARN] 現在のレートを取得できませんでした。終了します。")
        return

    # 直近レート取得
    last = get_last_rate()
    if last is None:
        print("[WARN] 直近のレートデータがありません。終了します。")
        return

    print(f"[INFO] 前回: {last:.2f}円 → 現在: {current:.2f}円 (差: {current - last:+.2f}円)")

    # アラート判定
    alert = check_alert(current, last)
    if alert is None:
        print("[INFO] 閾値内のため、アラートは送信しません。")
        return

    # アラートメッセージ生成・送信
    message = generate_alert_message(alert)
    print(f"[ALERT] {alert['direction']}方向の急変を検知！")
    print("--- アラートメッセージ ---")
    print(message)
    print("-------------------------")

    from src.common.notify import send_line
    send_line(message, with_quick_reply=True)
    print("[OK] アラート送信完了")


if __name__ == "__main__":
    main()
