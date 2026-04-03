"""
generate_chart.py
matplotlib で為替チャート画像を生成するモジュール
"""

import matplotlib
matplotlib.use("Agg")  # GUI不要のバックエンド

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
from pathlib import Path
import tempfile


def generate_forex_chart(week_data: list[dict], output_path: str = None) -> str:
    """
    USD/JPY の週間チャート画像を生成する。
    Args:
        week_data: data_store.load_week_data() の返り値（日付昇順の辞書リスト）
        output_path: 保存先パス（省略時は一時ファイル）
    Returns:
        生成された画像ファイルのパス
    """
    if not week_data:
        return ""

    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in week_data]
    usdjpy = [d["usdjpy"] for d in week_data]
    weekdays = [d.get("weekday", "") for d in week_data]

    fig, ax = plt.subplots(figsize=(8, 4))

    # 折れ線グラフ
    ax.plot(dates, usdjpy, marker="o", linewidth=2.5, color="#2196F3", markersize=8, markerfacecolor="white", markeredgewidth=2, markeredgecolor="#2196F3")

    # 値のラベル
    for i, (d, v) in enumerate(zip(dates, usdjpy)):
        ax.annotate(f"{v:.2f}", (d, v), textcoords="offset points", xytext=(0, 12), ha="center", fontsize=9, fontweight="bold")

    # X軸ラベル（曜日付き・英語略称でフォント問題を回避）
    weekday_en = {"月": "Mon", "火": "Tue", "水": "Wed", "木": "Thu", "金": "Fri", "土": "Sat", "日": "Sun"}
    labels = [f"{d.strftime('%-m/%-d')}({weekday_en.get(w, w)})" for d, w in zip(dates, weekdays)]
    ax.set_xticks(dates)
    ax.set_xticklabels(labels, fontsize=10)

    # Y軸の範囲（少し余裕をもたせる）
    y_min = min(usdjpy) - 0.5
    y_max = max(usdjpy) + 0.5
    ax.set_ylim(y_min, y_max)

    # グリッド
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.set_ylabel("USD/JPY", fontsize=11)

    # タイトル
    start = dates[0].strftime("%-m/%-d")
    end = dates[-1].strftime("%-m/%-d")
    ax.set_title(f"USD/JPY Weekly Chart ({start} - {end})", fontsize=13, fontweight="bold")

    # 背景色
    ax.set_facecolor("#FAFAFA")
    fig.patch.set_facecolor("white")

    plt.tight_layout()

    # 保存
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        output_path = tmp.name
        tmp.close()

    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"[OK] チャート画像を生成しました: {output_path}")
    return output_path


if __name__ == "__main__":
    # テスト用ダミーデータ
    dummy_week = [
        {"date": "2026-03-09", "weekday": "月", "usdjpy": 151.20, "eurjpy": 162.0, "usdjpy_prev": 150.80, "policy_rate": 0.50, "cpi_total": 3.2, "cpi_core": 2.8, "tankan_di": 12},
        {"date": "2026-03-10", "weekday": "火", "usdjpy": 150.90, "eurjpy": 161.5, "usdjpy_prev": 151.20, "policy_rate": 0.50, "cpi_total": 3.2, "cpi_core": 2.8, "tankan_di": 12},
        {"date": "2026-03-11", "weekday": "水", "usdjpy": 153.50, "eurjpy": 164.0, "usdjpy_prev": 150.90, "policy_rate": 0.50, "cpi_total": 3.2, "cpi_core": 2.8, "tankan_di": 12},
        {"date": "2026-03-12", "weekday": "木", "usdjpy": 152.10, "eurjpy": 163.2, "usdjpy_prev": 153.50, "policy_rate": 0.50, "cpi_total": 3.2, "cpi_core": 2.8, "tankan_di": 12},
        {"date": "2026-03-13", "weekday": "金", "usdjpy": 152.80, "eurjpy": 163.8, "usdjpy_prev": 152.10, "policy_rate": 0.50, "cpi_total": 3.2, "cpi_core": 2.8, "tankan_di": 12},
    ]
    path = generate_forex_chart(dummy_week, "/tmp/test_chart.png")
    print(f"Generated: {path}")
