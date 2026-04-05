"""
generate_chart.py
matplotlib で日経平均の週間チャート画像を生成するモジュール
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from datetime import datetime
import tempfile


def generate_nikkei_chart(week_data: list, output_path: str = None) -> str:
    """
    日経平均の週間チャート画像を生成する。
    Args:
        week_data: [{"date": "YYYY-MM-DD", "weekday": "月", "close": float}, ...]
        output_path: 保存先パス（省略時は一時ファイル）
    Returns:
        生成された画像ファイルのパス
    """
    if not week_data:
        return ""

    dates = [datetime.strptime(d["date"], "%Y-%m-%d") for d in week_data]
    closes = [d["close"] for d in week_data]
    weekdays = [d.get("weekday", "") for d in week_data]

    fig, ax = plt.subplots(figsize=(8, 4))

    # 折れ線グラフ
    ax.plot(
        dates, closes,
        marker="o", linewidth=2.5, color="#E53935",
        markersize=8, markerfacecolor="white",
        markeredgewidth=2, markeredgecolor="#E53935",
    )

    # 値のラベル
    for d, v in zip(dates, closes):
        ax.annotate(
            f"{v:,.0f}", (d, v),
            textcoords="offset points", xytext=(0, 12),
            ha="center", fontsize=9, fontweight="bold",
        )

    # X軸ラベル（曜日付き・英語略称でフォント問題を回避）
    weekday_en = {"月": "Mon", "火": "Tue", "水": "Wed", "木": "Thu", "金": "Fri", "土": "Sat", "日": "Sun"}
    labels = [f"{d.strftime('%-m/%-d')}({weekday_en.get(w, w)})" for d, w in zip(dates, weekdays)]
    ax.set_xticks(dates)
    ax.set_xticklabels(labels, fontsize=10)

    # Y軸の範囲（±300円の余裕）
    y_min = min(closes) - 300
    y_max = max(closes) + 300
    ax.set_ylim(y_min, y_max)

    # Y軸フォーマット（カンマ区切り）
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{int(x):,}"))

    # グリッド
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.set_ylabel("Nikkei 225 (JPY)", fontsize=11)

    # タイトル
    start = dates[0].strftime("%-m/%-d")
    end = dates[-1].strftime("%-m/%-d")
    ax.set_title(f"Nikkei 225 Weekly Chart ({start} - {end})", fontsize=13, fontweight="bold")

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

    print(f"[OK] 日経チャート画像を生成しました: {output_path}")
    return output_path


if __name__ == "__main__":
    dummy = [
        {"date": "2026-03-30", "weekday": "月", "close": 38100.0},
        {"date": "2026-03-31", "weekday": "火", "close": 38350.0},
        {"date": "2026-04-01", "weekday": "水", "close": 38200.0},
        {"date": "2026-04-02", "weekday": "木", "close": 38650.0},
        {"date": "2026-04-03", "weekday": "金", "close": 38800.0},
    ]
    path = generate_nikkei_chart(dummy, "/tmp/test_nikkei_chart.png")
    print(f"Generated: {path}")
