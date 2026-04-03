"""
fetch_nikkei.py
yfinance を使って日経平均（^N225）のデータを取得するモジュール
"""

import yfinance as yf
from datetime import datetime, timedelta

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.common.tz import now_jst

# 曜日の日本語表記
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

# フォールバック値（API障害時）
FALLBACK_NIKKEI = {
    "close": 38000.0,
    "prev_close": 38000.0,
    "high_52w": 42000.0,
    "ytd_start": 39000.0,
}


def fetch_nikkei225() -> dict:
    """
    日経平均の終値・前日比・52週高値・年初来騰落率を取得する。
    Returns:
        {
            "nikkei_close": float,       # 終値
            "nikkei_prev_close": float,  # 前日終値
            "nikkei_diff": float,        # 前日比（円）
            "nikkei_diff_pct": float,    # 前日比（%）
            "nikkei_high_52w": float,    # 52週高値
            "nikkei_ytd_pct": float,     # 年初来騰落率（%）
            "fetch_date": str,           # 取得日（YYYY年M月D日）
            "fetch_weekday": str,        # 曜日
            "fetch_time": str,           # 時刻（HH:MM）
        }
    """
    now = now_jst()

    try:
        ticker = yf.Ticker("^N225")

        # 直近2日分の終値を取得（前日比算出用）
        hist_2d = ticker.history(period="5d")
        if hist_2d.empty or len(hist_2d) < 2:
            raise ValueError("日経平均の直近データが不足しています")

        close = round(float(hist_2d["Close"].iloc[-1]), 2)
        prev_close = round(float(hist_2d["Close"].iloc[-2]), 2)
        diff = round(close - prev_close, 2)
        diff_pct = round((diff / prev_close) * 100, 2) if prev_close else 0.0

        # 52週高値
        high_52w = _fetch_52w_high(ticker)

        # 年初来騰落率
        ytd_pct = _fetch_ytd_pct(ticker, close)

        return {
            "nikkei_close": close,
            "nikkei_prev_close": prev_close,
            "nikkei_diff": diff,
            "nikkei_diff_pct": diff_pct,
            "nikkei_high_52w": high_52w,
            "nikkei_ytd_pct": ytd_pct,
            "fetch_date": now.strftime("%Y年%-m月%-d日"),
            "fetch_weekday": WEEKDAY_JP[now.weekday()],
            "fetch_time": now.strftime("%H:%M"),
        }

    except Exception as e:
        print(f"[WARN] 日経平均取得エラー: {e}")
        return _build_fallback(now)


def _fetch_52w_high(ticker) -> float:
    """52週（約1年）の高値を取得する"""
    try:
        hist_1y = ticker.history(period="1y")
        if not hist_1y.empty:
            return round(float(hist_1y["High"].max()), 2)
    except Exception as e:
        print(f"[WARN] 52週高値取得エラー: {e}")
    return FALLBACK_NIKKEI["high_52w"]


def _fetch_ytd_pct(ticker, current_close: float) -> float:
    """年初来騰落率（%）を算出する"""
    try:
        now = now_jst()
        year_start = datetime(now.year, 1, 1)
        # 年初の最初の営業日の終値を取得
        hist_ytd = ticker.history(start=year_start.strftime("%Y-%m-%d"), period="5d")
        if not hist_ytd.empty:
            ytd_start = float(hist_ytd["Close"].iloc[0])
            if ytd_start > 0:
                return round(((current_close - ytd_start) / ytd_start) * 100, 1)
    except Exception as e:
        print(f"[WARN] 年初来騰落率算出エラー: {e}")
    return 0.0


def fetch_nikkei225_weekly(days: int = 5) -> list:
    """
    直近N営業日分の日経平均終値を取得する（週次レポート用）。
    Args:
        days: 取得日数（デフォルト5日 = 1週間分）
    Returns:
        [{"date": "YYYY-MM-DD", "weekday": "月", "close": float}, ...]
    """
    try:
        ticker = yf.Ticker("^N225")
        hist = ticker.history(period=f"{days + 3}d")  # 余裕をもって取得
        if hist.empty:
            return []

        result = []
        for idx, row in hist.tail(days).iterrows():
            date = idx.strftime("%Y-%m-%d")
            weekday_num = idx.weekday()
            result.append({
                "date": date,
                "weekday": WEEKDAY_JP[weekday_num],
                "close": round(float(row["Close"]), 2),
            })

        return result

    except Exception as e:
        print(f"[WARN] 日経平均週次データ取得エラー: {e}")
        return []


def _build_fallback(now: datetime) -> dict:
    """API障害時のフォールバック値を返す"""
    fb = FALLBACK_NIKKEI
    return {
        "nikkei_close": fb["close"],
        "nikkei_prev_close": fb["prev_close"],
        "nikkei_diff": 0.0,
        "nikkei_diff_pct": 0.0,
        "nikkei_high_52w": fb["high_52w"],
        "nikkei_ytd_pct": 0.0,
        "fetch_date": now.strftime("%Y年%-m月%-d日"),
        "fetch_weekday": WEEKDAY_JP[now.weekday()],
        "fetch_time": now.strftime("%H:%M"),
    }


if __name__ == "__main__":
    data = fetch_nikkei225()
    print("=== 日経平均データ ===")
    for k, v in data.items():
        print(f"  {k}: {v}")

    print("\n=== 週次データ ===")
    weekly = fetch_nikkei225_weekly()
    for d in weekly:
        print(f"  {d['date']}（{d['weekday']}）: {d['close']}")
