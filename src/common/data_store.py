"""
data_store.py
日次指標データをCSVに蓄積・読取するモジュール
"""

import csv
import os
from datetime import datetime, timedelta
from pathlib import Path
from src.common.tz import now_jst

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
CSV_PATH = DATA_DIR / "daily_indicators.csv"

CSV_COLUMNS = [
    "date",
    "weekday",
    "usdjpy",
    "eurjpy",
    "usdjpy_prev",
    "policy_rate",
    "cpi_total",
    "cpi_core",
    "tankan_di",
]


def save_daily(data: dict) -> None:
    """
    日次指標データをCSVに1行追記する。
    同じ日付のデータが既にあれば上書きしない（重複防止）。
    Args:
        data: fetch_all() の返り値
    """
    today = now_jst().strftime("%Y-%m-%d")

    # 既に今日のデータがあれば何もしない
    if _has_date(today):
        print(f"[INFO] {today} のデータは既に保存済みです")
        return

    row = {
        "date": today,
        "weekday": data.get("fetch_weekday", ""),
        "usdjpy": data.get("usdjpy", 0),
        "eurjpy": data.get("eurjpy", 0),
        "usdjpy_prev": data.get("usdjpy_prev", 0),
        "policy_rate": data.get("policy_rate", 0),
        "cpi_total": data.get("cpi_total", 0),
        "cpi_core": data.get("cpi_core", 0),
        "tankan_di": data.get("tankan_di", 0),
    }

    file_exists = CSV_PATH.exists() and CSV_PATH.stat().st_size > 0

    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    print(f"[OK] {today} のデータをCSVに保存しました")


def _has_date(date_str: str) -> bool:
    """指定日のデータがCSVに存在するか確認する"""
    if not CSV_PATH.exists():
        return False
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("date") == date_str:
                return True
    return False


def load_recent(days: int = 5) -> list[dict]:
    """
    直近N日分のデータをCSVから読み取る（日付降順）。
    Args:
        days: 取得する日数
    Returns:
        辞書のリスト（日付降順）
    """
    if not CSV_PATH.exists():
        return []

    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 数値型に変換
            for col in ["usdjpy", "eurjpy", "usdjpy_prev", "policy_rate", "cpi_total", "cpi_core"]:
                if col in row and row[col]:
                    row[col] = float(row[col])
            if "tankan_di" in row and row["tankan_di"]:
                row["tankan_di"] = int(float(row["tankan_di"]))
            rows.append(row)

    # 日付降順でソートし、直近N件を返す
    rows.sort(key=lambda r: r.get("date", ""), reverse=True)
    return rows[:days]


def load_week_data(target_date: datetime = None) -> list[dict]:
    """
    指定日が属する週（月〜金）のデータを返す。
    Args:
        target_date: 基準日（デフォルト: 今日）
    Returns:
        辞書のリスト（日付昇順）
    """
    if target_date is None:
        target_date = now_jst()

    # 週の月曜日を計算
    monday = target_date - timedelta(days=target_date.weekday())
    friday = monday + timedelta(days=4)

    monday_str = monday.strftime("%Y-%m-%d")
    friday_str = friday.strftime("%Y-%m-%d")

    if not CSV_PATH.exists():
        return []

    rows = []
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date = row.get("date", "")
            if monday_str <= date <= friday_str:
                for col in ["usdjpy", "eurjpy", "usdjpy_prev", "policy_rate", "cpi_total", "cpi_core"]:
                    if col in row and row[col]:
                        row[col] = float(row[col])
                if "tankan_di" in row and row["tankan_di"]:
                    row["tankan_di"] = int(float(row["tankan_di"]))
                rows.append(row)

    rows.sort(key=lambda r: r.get("date", ""))
    return rows


if __name__ == "__main__":
    # テスト: ダミーデータを保存して読み取り
    dummy = {
        "fetch_weekday": "月",
        "usdjpy": 152.30,
        "eurjpy": 163.45,
        "usdjpy_prev": 151.80,
        "policy_rate": 0.50,
        "cpi_total": 3.2,
        "cpi_core": 2.8,
        "tankan_di": 12,
    }
    save_daily(dummy)
    recent = load_recent(5)
    for row in recent:
        print(row)
