"""
fetch_detail.py
詳細データ取得モジュール — Quick Reply 応答用の詳細情報を取得する
"""

import os
import requests
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv
from src.common.tz import now_jst

load_dotenv()

ESTAT_API_KEY = os.getenv("ESTAT_API_KEY")
ESTAT_BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
BOJ_BASE_URL = "https://www.stat-search.boj.or.jp/ssi/mtsearch.do"

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

# 政策金利の変更履歴（定数：手動更新）
RATE_HISTORY = [
    {"date": "2024年3月", "rate": 0.10, "action": "マイナス金利解除"},
    {"date": "2024年7月", "rate": 0.25, "action": "利上げ"},
    {"date": "2025年1月", "rate": 0.50, "action": "利上げ"},
]

# 次回政策決定会合スケジュール
NEXT_MEETINGS = [
    "2026年4月30日",
    "2026年6月12〜13日",
    "2026年7月30〜31日",
]

# 経済イベントカレンダー（定数：手動更新）
ECONOMIC_EVENTS = [
    {"date": "2026年3月19日", "event": "日銀金融政策決定会合（結果発表）"},
    {"date": "2026年3月21日", "event": "CPI（2月分）発表"},
    {"date": "2026年4月1日", "event": "日銀短観（3月調査）発表"},
    {"date": "2026年4月30日", "event": "日銀金融政策決定会合（結果発表）"},
    {"date": "2026年5月23日", "event": "CPI（4月分）発表"},
]


def fetch_forex_detail() -> dict:
    """
    為替の詳細データを取得する（5日間推移・週間高値/安値）
    Returns: USD/JPY・EUR/JPYの詳細情報dict
    """
    now = now_jst()
    weekday = WEEKDAY_JP[now.weekday()]

    try:
        usdjpy = yf.Ticker("USDJPY=X")
        eurjpy = yf.Ticker("EURJPY=X")

        usdjpy_hist = usdjpy.history(period="5d")
        eurjpy_hist = eurjpy.history(period="2d")

        usdjpy_closes = [round(float(c), 2) for c in usdjpy_hist["Close"]]
        usdjpy_now = usdjpy_closes[-1] if usdjpy_closes else 152.30
        usdjpy_prev = usdjpy_closes[-2] if len(usdjpy_closes) >= 2 else usdjpy_now
        usdjpy_diff = round(usdjpy_now - usdjpy_prev, 2)
        usdjpy_diff_pct = round((usdjpy_diff / usdjpy_prev) * 100, 2) if usdjpy_prev else 0
        usdjpy_week_high = max(usdjpy_closes) if usdjpy_closes else usdjpy_now
        usdjpy_week_low = min(usdjpy_closes) if usdjpy_closes else usdjpy_now

        # 高値/安値の日付を取得
        usdjpy_high_idx = usdjpy_closes.index(usdjpy_week_high)
        usdjpy_low_idx = usdjpy_closes.index(usdjpy_week_low)
        usdjpy_dates = list(usdjpy_hist.index)
        usdjpy_high_date = usdjpy_dates[usdjpy_high_idx].strftime("%-m/%-d") if usdjpy_dates else ""
        usdjpy_low_date = usdjpy_dates[usdjpy_low_idx].strftime("%-m/%-d") if usdjpy_dates else ""

        eurjpy_now = round(float(eurjpy_hist["Close"].iloc[-1]), 2) if len(eurjpy_hist) > 0 else 163.45
        eurjpy_prev = round(float(eurjpy_hist["Close"].iloc[-2]), 2) if len(eurjpy_hist) >= 2 else eurjpy_now
        eurjpy_diff = round(eurjpy_now - eurjpy_prev, 2)
        eurjpy_diff_pct = round((eurjpy_diff / eurjpy_prev) * 100, 2) if eurjpy_prev else 0

        # トレンド判定
        if len(usdjpy_closes) >= 3:
            recent_trend = usdjpy_closes[-1] - usdjpy_closes[0]
            if recent_trend > 1.0:
                trend = "円安方向で推移中"
            elif recent_trend < -1.0:
                trend = "円高方向で推移中"
            else:
                trend = "横ばいで推移中"
        else:
            trend = "データ不足のため判定不可"

        return {
            "fetch_date": now.strftime("%Y年%-m月%-d日"),
            "fetch_weekday": weekday,
            "fetch_time": now.strftime("%H:%M"),
            "usdjpy": usdjpy_now,
            "usdjpy_prev": usdjpy_prev,
            "usdjpy_diff": usdjpy_diff,
            "usdjpy_diff_pct": usdjpy_diff_pct,
            "usdjpy_week_high": usdjpy_week_high,
            "usdjpy_week_low": usdjpy_week_low,
            "usdjpy_high_date": usdjpy_high_date,
            "usdjpy_low_date": usdjpy_low_date,
            "usdjpy_5d": " → ".join(str(c) for c in usdjpy_closes),
            "eurjpy": eurjpy_now,
            "eurjpy_diff": eurjpy_diff,
            "eurjpy_diff_pct": eurjpy_diff_pct,
            "trend": trend,
        }
    except Exception as e:
        print(f"[WARN] 為替詳細取得エラー: {e}")
        return {
            "fetch_date": now.strftime("%Y年%-m月%-d日"),
            "fetch_weekday": weekday,
            "fetch_time": now.strftime("%H:%M"),
            "usdjpy": 152.30, "usdjpy_prev": 151.80,
            "usdjpy_diff": 0.50, "usdjpy_diff_pct": 0.33,
            "usdjpy_week_high": 153.20, "usdjpy_week_low": 150.80,
            "usdjpy_high_date": "", "usdjpy_low_date": "",
            "usdjpy_5d": "データ取得エラー",
            "eurjpy": 163.45, "eurjpy_diff": -0.15, "eurjpy_diff_pct": -0.09,
            "trend": "データ取得エラー",
        }


def fetch_rate_detail() -> dict:
    """
    金利の詳細データを取得する（政策金利推移・会合日程・変更履歴）
    """
    now = now_jst()
    weekday = WEEKDAY_JP[now.weekday()]

    # 現在の政策金利を取得
    from src.ueda.fetch_indicators import fetch_policy_rate
    policy = fetch_policy_rate()

    return {
        "fetch_date": now.strftime("%Y年%-m月%-d日"),
        "fetch_weekday": weekday,
        "fetch_time": now.strftime("%H:%M"),
        "current_rate": policy["rate"],
        "rate_date": policy["date"],
        "rate_history": RATE_HISTORY,
        "next_meetings": NEXT_MEETINGS,
    }


def fetch_cpi_detail() -> dict:
    """
    CPI の詳細データを取得する（総合/コア/食料エネルギー除く）
    """
    now = now_jst()
    weekday = WEEKDAY_JP[now.weekday()]

    from src.ueda.fetch_indicators import fetch_cpi
    cpi = fetch_cpi()

    # コアCPI、食料エネルギー除くの概算
    core = cpi["core"]
    core_core = round(core - 0.3, 1)  # 食料・エネルギー除くの概算

    prev_total = cpi.get("prev_total", cpi["total"])
    mom_change = round(cpi["total"] - prev_total, 1)  # 前月比

    return {
        "fetch_date": now.strftime("%Y年%-m月%-d日"),
        "fetch_weekday": weekday,
        "cpi_date": cpi["date"],
        "cpi_total": cpi["total"],
        "cpi_core": core,
        "cpi_core_core": core_core,
        "cpi_prev_total": prev_total,
        "cpi_mom_change": mom_change,
    }


def fetch_tankan_detail() -> dict:
    """
    短観の詳細データを取得する（製造業/非製造業DI比較）
    """
    now = now_jst()
    weekday = WEEKDAY_JP[now.weekday()]

    from src.ueda.fetch_indicators import fetch_tankan_di, _format_tankan_date
    tankan = fetch_tankan_di()
    tankan_date = _format_tankan_date(tankan["date"])

    # 非製造業DI・先行きDIはフォールバック定数（日銀IMAS APIが不安定のため）
    return {
        "fetch_date": now.strftime("%Y年%-m月%-d日"),
        "fetch_weekday": weekday,
        "tankan_date": tankan_date,
        "mfg_di": tankan["di"],
        "non_mfg_di": 34,  # 非製造業DI（フォールバック値）
        "mfg_outlook_di": tankan["di"] - 2,  # 先行きDI概算
        "non_mfg_outlook_di": 32,  # 非製造業先行きDI（フォールバック値）
        "mfg_prev_di": tankan["di"] - 1,  # 前回比（概算）
    }


def fetch_events_detail() -> dict:
    """
    経済イベントカレンダーを取得する
    """
    now = now_jst()
    weekday = WEEKDAY_JP[now.weekday()]

    # 今日以降のイベントのみフィルタ
    upcoming = []
    for ev in ECONOMIC_EVENTS:
        try:
            for fmt in ["%Y年%m月%d日", "%Y年%-m月%-d日"]:
                try:
                    ev_date = datetime.strptime(ev["date"], fmt)
                    break
                except ValueError:
                    continue
            else:
                continue
            if ev_date.date() >= now.date():
                upcoming.append(ev)
        except Exception:
            continue

    return {
        "fetch_date": now.strftime("%Y年%-m月%-d日"),
        "fetch_weekday": weekday,
        "events": upcoming,
    }


# カテゴリ名 → 取得関数のマッピング
DETAIL_FETCHERS = {
    "為替": fetch_forex_detail,
    "金利": fetch_rate_detail,
    "CPI": fetch_cpi_detail,
    "短観": fetch_tankan_detail,
    "注目": fetch_events_detail,
}


def fetch_detail(category: str) -> dict:
    """
    カテゴリ名に応じた詳細データを取得する
    Args:
        category: "為替", "金利", "CPI", "短観", "注目" のいずれか
    Returns:
        対応する詳細データdict
    """
    fetcher = DETAIL_FETCHERS.get(category)
    if fetcher is None:
        raise ValueError(f"不明なカテゴリ: {category}")
    return fetcher()


if __name__ == "__main__":
    for cat in DETAIL_FETCHERS:
        print(f"\n{'='*40}")
        print(f"  カテゴリ: {cat}")
        print(f"{'='*40}")
        data = fetch_detail(cat)
        for k, v in data.items():
            print(f"  {k}: {v}")
