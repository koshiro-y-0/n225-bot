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


def _fetch_history_safe(ticker, days_back: int = 45):
    """
    yfinance の history() を明示的な start/end で呼ぶ。
    period='1mo' 相当の期間を取得しつつ、end を JST 基準の「翌日」に固定することで
    Yahoo が直近の完了済みバーを必ず含めるようにする。
    （GitHub Actions の UTC 実行環境で、JST 基準の最新営業日バーが欠落する問題への対策）
    """
    jst_today = now_jst().date()
    end_date = jst_today + timedelta(days=1)
    start_date = jst_today - timedelta(days=days_back)
    return ticker.history(
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
    )

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

        # 直近データを取得（前日比算出・52週高値・YTD用）
        # 長期休場（GW・年末年始）後でも確実に複数営業日取れるよう45日分取得
        hist = _fetch_history_safe(ticker, days_back=45)
        if hist.empty or len(hist) < 2:
            raise ValueError("日経平均の直近データが不足しています")

        # --- 前日終値の取得 ---
        # history.iloc[-1] = 直近完了済みセッションの終値、iloc[-2] = その1つ前の営業日。
        # 過去に PR #13 で fast_info['previousClose'] を併用したが、Yahoo の "previousClose"
        # は最新セッション(=現在進行中)の "前日"=昨日終値を意味し、JST 朝の文脈では
        # history.iloc[-1] と同じ営業日ではなく "iloc[-2] 相当" を返してしまう。
        # その結果、close と prev_close を逆向きに入れ替える不具合が発生したため
        # シンプルに history のみを信頼する方式に戻す（PR #14）。
        close      = round(float(hist["Close"].iloc[-1]), 2)
        prev_close = round(float(hist["Close"].iloc[-2]), 2)

        # サニティチェック: history 末尾の日付が古すぎる場合は警告ログを出す
        # （Yahoo Finance のバックエンド遅延で最新営業日が欠落している可能性）
        try:
            last_bar_date = hist.index[-1].date()
            jst_today     = now.date()
            gap_days      = (jst_today - last_bar_date).days
            if gap_days >= 4:
                print(
                    f"[WARN] history 末尾の日付 {last_bar_date} が今日({jst_today})から"
                    f"{gap_days}日前です。最新営業日のデータが欠落している可能性があります。"
                )
        except Exception:
            pass

        diff = round(close - prev_close, 2)
        diff_pct = round((diff / prev_close) * 100, 2) if prev_close else 0.0

        # 52週高値
        high_52w = _fetch_52w_high(ticker)

        # 年初来騰落率（close = 直近完了セッション終値）
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
        # 年初の最初の営業日の終値を取得（年始から10日分取れば十分）
        ytd_end = year_start + timedelta(days=10)
        hist_ytd = ticker.history(
            start=year_start.strftime("%Y-%m-%d"),
            end=ytd_end.strftime("%Y-%m-%d"),
        )
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
        # 祝日を考慮し、十分なバッファを確保（最低2週間分）
        buffer_days = max(days * 2 + 7, 14)
        hist = _fetch_history_safe(ticker, days_back=buffer_days)
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
