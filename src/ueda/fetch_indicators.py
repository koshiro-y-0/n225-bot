"""
fetch_indicators.py
日銀IMAS API・総務省e-Stat API・Yahoo Financeから経済指標を取得するモジュール
"""

import os
import locale
import requests
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv
from src.common.tz import now_jst

# 曜日の日本語表記
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

load_dotenv()

ESTAT_API_KEY = os.getenv("ESTAT_API_KEY")

# 日銀IMAS API（JSON APIが不安定なためフォールバック値を併用）
BOJ_BASE_URL = "https://www.stat-search.boj.or.jp/ssi/mtsearch.do"
# 総務省e-Stat API
ESTAT_BASE_URL = "https://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"


def fetch_policy_rate() -> dict:
    """
    日銀IMAS APIから政策金利（無担保コール翌日物）を取得する
    Returns: {"rate": float, "date": str, "prev_rate": float}
    """
    params = {
        "type": "ST",
        "fc": "FM01'MABASE",  # 無担保コールレート系列
        "oc": "LE",
        "dateType": "12",
        "cnt": 2,
        "outputType": "json",
    }
    try:
        response = requests.get(BOJ_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        records = data.get("items", [])
        if len(records) >= 2:
            return {
                "rate": float(records[0]["value"]),
                "date": records[0]["date"],
                "prev_rate": float(records[1]["value"]),
            }
    except Exception as e:
        print(f"[WARN] 政策金利取得エラー: {e}")
    # フォールバック（APIが不安定な場合）
    return {"rate": 0.50, "date": now_jst().strftime("%Y-%m"), "prev_rate": 0.50}


def fetch_tankan_di() -> dict:
    """
    日銀IMAS APIから短観・大企業製造業DIを取得する
    Returns: {"di": int, "date": str}
    """
    params = {
        "type": "ST",
        "fc": "QT'CG10",  # 大企業製造業業況判断DI
        "oc": "LE",
        "dateType": "12",
        "cnt": 1,
        "outputType": "json",
    }
    try:
        response = requests.get(BOJ_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        records = data.get("items", [])
        if records:
            return {
                "di": int(float(records[0]["value"])),
                "date": records[0]["date"],
            }
    except Exception as e:
        print(f"[WARN] 短観DI取得エラー: {e}")
    now = now_jst()
    quarter = (now.month - 1) // 3 + 1
    return {"di": 12, "date": f"{now.year}-Q{quarter}"}


def fetch_cpi() -> dict:
    """
    総務省e-Stat APIからCPI（消費者物価指数）を取得する
    Returns: {"total": float, "core": float, "date": str, "prev_total": float}
    """
    if not ESTAT_API_KEY:
        print("[WARN] ESTAT_API_KEY が未設定です。フォールバック値を使用します。")
        return {"total": 3.2, "core": 2.8, "date": "2026年1月", "prev_total": 3.0}

    # 総合CPI（statsDataId: 0003427112）
    params = {
        "appId": ESTAT_API_KEY,
        "statsDataId": "0003427112",
        "metaGetFlg": "N",
        "cntGetFlg": "N",
        "explanationGetFlg": "N",
        "limit": 2,
    }
    try:
        response = requests.get(ESTAT_BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        stat_data = data.get("GET_STATS_DATA", {})
        result = stat_data.get("STATISTICAL_DATA", stat_data.get("RESULT", {}))
        data_inf = result.get("DATA_INF", {})
        values = data_inf.get("VALUE", [])
        if not values:
            raise ValueError("e-Stat APIからデータが取得できませんでした")
        latest = values[-1]
        prev = values[-2] if len(values) >= 2 else latest
        return {
            "total": float(latest["$"]),
            "core": float(latest["$"]) - 0.4,  # コアCPIの概算
            "date": latest.get("@time", "不明"),
            "prev_total": float(prev["$"]),
        }
    except Exception as e:
        print(f"[WARN] CPI取得エラー: {e}")
    return {"total": 3.2, "core": 2.8, "date": "2026年1月", "prev_total": 3.0}


def fetch_forex() -> dict:
    """
    Yahoo Finance から USD/JPY・EUR/JPY のレートを取得する
    Returns: {"usdjpy": float, "eurjpy": float, "usdjpy_prev": float}
    """
    try:
        usdjpy = yf.Ticker("USDJPY=X")
        eurjpy = yf.Ticker("EURJPY=X")

        usdjpy_hist = usdjpy.history(period="2d")
        eurjpy_hist = eurjpy.history(period="1d")

        usdjpy_now = round(float(usdjpy_hist["Close"].iloc[-1]), 2)
        usdjpy_prev = round(float(usdjpy_hist["Close"].iloc[-2]), 2) if len(usdjpy_hist) >= 2 else usdjpy_now
        eurjpy_now = round(float(eurjpy_hist["Close"].iloc[-1]), 2)

        return {
            "usdjpy": usdjpy_now,
            "eurjpy": eurjpy_now,
            "usdjpy_prev": usdjpy_prev,
        }
    except Exception as e:
        print(f"[WARN] 為替取得エラー: {e}")
    return {"usdjpy": 152.30, "eurjpy": 163.45, "usdjpy_prev": 152.30}


QUARTER_MONTH = {"Q1": "3月調査", "Q2": "6月調査", "Q3": "9月調査", "Q4": "12月調査"}


def _format_tankan_date(raw: str) -> str:
    """短観日付を読みやすい形式に変換する（例: "2025-Q4" → "2025年Q4（12月調査）"）"""
    try:
        parts = raw.split("-")
        year = parts[0]
        quarter = parts[1]
        month_label = QUARTER_MONTH.get(quarter, "")
        if month_label:
            return f"{year}年{quarter}（{month_label}）"
        return raw
    except (IndexError, ValueError):
        return raw


def fetch_all() -> dict:
    """
    すべての指標を取得してまとめて返す
    Returns: 全指標をまとめたdict
    """
    print("経済指標を取得中...")
    policy = fetch_policy_rate()
    tankan = fetch_tankan_di()
    cpi = fetch_cpi()
    forex = fetch_forex()

    now = now_jst()
    weekday = WEEKDAY_JP[now.weekday()]

    # 短観日付を読みやすいフォーマットに変換（例: "2025-Q4" → "2025年Q4（12月調査）"）
    tankan_date_raw = tankan["date"]
    tankan_date_formatted = _format_tankan_date(tankan_date_raw)

    return {
        "fetch_date": now.strftime("%Y年%-m月%-d日"),
        "fetch_weekday": weekday,
        "fetch_time": now.strftime("%H:%M"),
        "policy_rate": policy["rate"],
        "policy_rate_prev": policy["prev_rate"],
        "policy_rate_date": policy["date"],
        "tankan_di": tankan["di"],
        "tankan_date": tankan_date_formatted,
        "cpi_total": cpi["total"],
        "cpi_core": cpi["core"],
        "cpi_date": cpi["date"],
        "cpi_prev_total": cpi.get("prev_total", cpi["total"]),
        "usdjpy": forex["usdjpy"],
        "eurjpy": forex["eurjpy"],
        "usdjpy_prev": forex["usdjpy_prev"],
    }


def _get_review_date(now: datetime) -> datetime:
    """
    振り返り対象日を返す（月曜なら前の金曜、それ以外は前日）
    """
    if now.weekday() == 0:  # 月曜
        return now - timedelta(days=3)
    return now - timedelta(days=1)


def fetch_review_and_outlook(data: dict) -> dict:
    """
    昨日の振り返り（月曜なら金曜日）と今日の見通しを生成する
    Args:
        data: fetch_all() の返り値
    Returns:
        振り返りと見通しのdict
    """
    now = now_jst()
    review_date = _get_review_date(now)
    review_weekday = WEEKDAY_JP[review_date.weekday()]
    review_date_str = review_date.strftime("%Y年%-m月%-d日")

    # 為替の前日変動
    usdjpy_diff = data["usdjpy"] - data["usdjpy_prev"]
    usdjpy_direction = "円安" if usdjpy_diff > 0 else "円高" if usdjpy_diff < 0 else "横ばい"

    # 振り返りコメント生成
    review_lines = []
    if abs(usdjpy_diff) >= 1.0:
        review_lines.append(f"為替は{usdjpy_direction}方向に大きく動き、USD/JPY {data['usdjpy_prev']:.2f}円 → {data['usdjpy']:.2f}円（{usdjpy_diff:+.2f}円）")
    else:
        review_lines.append(f"為替は{usdjpy_direction}で小幅な動き、USD/JPY {data['usdjpy_prev']:.2f}円 → {data['usdjpy']:.2f}円（{usdjpy_diff:+.2f}円）")

    rate_diff = data["policy_rate"] - data["policy_rate_prev"]
    if rate_diff != 0:
        review_lines.append(f"政策金利が{data['policy_rate_prev']:.2f}% → {data['policy_rate']:.2f}%に変更")
    else:
        review_lines.append(f"政策金利は{data['policy_rate']:.2f}%で据え置き")

    # 今日の見通し生成
    outlook_lines = []

    # 経済イベントチェック（今日のイベントがあれば表示）
    today_str = now.strftime("%Y年%-m月%-d日")
    from src.ueda.fetch_detail import ECONOMIC_EVENTS
    today_events = [e for e in ECONOMIC_EVENTS if e["date"] == today_str]
    if today_events:
        for ev in today_events:
            outlook_lines.append(f"本日のイベント：{ev['event']}")
    else:
        outlook_lines.append("本日、注目の経済イベントはありません")

    # 今後の注目イベント（今日以降のものをフィルタ）
    upcoming_events = []
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
                upcoming_events.append(ev)
        except Exception:
            continue

    # 為替トレンドに基づく見通し
    if abs(usdjpy_diff) >= 1.5:
        outlook_lines.append("為替の急変動が続く可能性があり、引き続き注意が必要です")
    elif data["usdjpy"] >= 155:
        outlook_lines.append("円安水準が続いており、為替介入への警戒感が意識されます")
    elif data["usdjpy"] <= 140:
        outlook_lines.append("円高方向への動きが見られ、輸出企業への影響に注目です")
    else:
        outlook_lines.append("為替は安定的に推移しており、大きな変動は見込まれません")

    return {
        "review_date": review_date_str,
        "review_weekday": review_weekday,
        "review_lines": review_lines,
        "outlook_lines": outlook_lines,
        "is_monday": now.weekday() == 0,
        "upcoming_events": upcoming_events,
    }


if __name__ == "__main__":
    indicators = fetch_all()
    for key, value in indicators.items():
        print(f"  {key}: {value}")
