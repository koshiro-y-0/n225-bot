"""
generate_report.py
取得した経済指標データを植田総裁口調テンプレートに埋め込みレポートを生成するモジュール
"""

from jinja2 import Environment, FileSystemLoader
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

# 植田総裁口調テンプレート定義
POLICY_COMMENTS = {
    "no_change": "物価の基調は概ね見通し通り。先行きのリスクは上下双方向に存在します。",
    "rate_up":   "物価安定目標の持続的実現に向け、緩やかな利上げ軌道を維持します。",
    "rate_down": "下方リスクへの対応として、金融緩和を強化し経済の下支えを図ります。",
    "cpi_up":    "賃金と物価の好循環が確認されつつある一方、海外リスクに注意が必要です。",
    "cpi_down":  "物価上昇の基調は維持されていますが、先行き不確実性を注意深く見極めます。",
}

# 次回政策決定会合スケジュール（要手動更新）
NEXT_MEETING = "2026年4月30日"


def _determine_policy_comment(data: dict) -> str:
    """指標の状態に応じてテンプレートコメントを選択する"""
    rate_diff = data["policy_rate"] - data["policy_rate_prev"]
    cpi_diff = data["cpi_total"] - data.get("cpi_prev_total", data["cpi_total"])

    if rate_diff > 0:
        return POLICY_COMMENTS["rate_up"]
    if rate_diff < 0:
        return POLICY_COMMENTS["rate_down"]
    if cpi_diff >= 0.5:
        return POLICY_COMMENTS["cpi_up"]
    if cpi_diff <= -0.5:
        return POLICY_COMMENTS["cpi_down"]
    return POLICY_COMMENTS["no_change"]


def _determine_rate_change_label(data: dict) -> str:
    rate_diff = data["policy_rate"] - data["policy_rate_prev"]
    if rate_diff > 0:
        return f"+{rate_diff:.2f}%"
    if rate_diff < 0:
        return f"{rate_diff:.2f}%"
    return "変化なし"


def build_template_context(data: dict, review_data: dict = None) -> dict:
    """テンプレートに渡すコンテキストを構築する"""
    rate_diff = data["policy_rate"] - data["policy_rate_prev"]
    usdjpy_diff = data["usdjpy"] - data["usdjpy_prev"]

    context = {
        **data,
        "policy_comment": _determine_policy_comment(data),
        "policy_rate_changed": rate_diff != 0,
        "rate_change_label": _determine_rate_change_label(data),
        "forex_alert": abs(usdjpy_diff) >= 1.5,
        "usdjpy_diff": usdjpy_diff,
        "next_meeting_date": NEXT_MEETING,
    }

    if review_data:
        context.update(review_data)

    return context


def generate_report(data: dict, review_data: dict = None) -> str:
    """
    経済指標データからレポート文字列を生成する
    Args:
        data: fetch_indicators.fetch_all() の返り値
        review_data: fetch_review_and_outlook() の返り値（振り返り・見通し）
    Returns:
        通知用レポート文字列
    """
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("report.j2")
    context = build_template_context(data, review_data)
    return template.render(context)


def generate_alert(alert_type: str, data: dict) -> str:
    """アラート通知メッセージを生成する"""
    alerts = {
        "forex": (
            f"⚠️ 【緊急為替アラート】\n"
            f"USD/JPY が急変しました。\n"
            f"現在値：{data['usdjpy']:.2f}円"
            f"（前日比 {data['usdjpy'] - data['usdjpy_prev']:+.2f}円）\n"
            f"「為替市場の動向を注意深く見極め、適切に対応してまいります。」"
        ),
        "rate_change": (
            f"📢 【政策変更アラート】\n"
            f"政策金利が変更されました。\n"
            f"変更後：{data['policy_rate']:.2f}%"
            f"（前回：{data['policy_rate_prev']:.2f}%）\n"
            f"「{_determine_policy_comment(data)}」"
        ),
        "cpi": (
            f"📈 【物価動向アラート】\n"
            f"CPI が大きく変動しました。\n"
            f"最新値：{data['cpi_total']:.1f}%"
            f"（前月比 {data['cpi_total'] - data.get('cpi_prev_total', data['cpi_total']):+.1f}%）\n"
            f"「{_determine_policy_comment(data)}」"
        ),
    }
    return alerts.get(alert_type, "アラートが発生しました。")


if __name__ == "__main__":
    # テスト用ダミーデータでレポート生成を確認
    dummy = {
        "fetch_date": "2026年3月16日",
        "fetch_weekday": "月",
        "fetch_time": "08:30",
        "policy_rate": 0.50,
        "policy_rate_prev": 0.50,
        "policy_rate_date": "2026-01",
        "tankan_di": 12,
        "tankan_date": "2025年Q4（12月調査）",
        "cpi_total": 3.2,
        "cpi_core": 2.8,
        "cpi_date": "2026年1月",
        "cpi_prev_total": 3.0,
        "usdjpy": 152.30,
        "eurjpy": 163.45,
        "usdjpy_prev": 151.80,
    }
    review = {
        "review_date": "2026年3月13日",
        "review_weekday": "金",
        "review_lines": ["為替は円安で小幅な動き、USD/JPY 151.80円 → 152.30円（+0.50円）", "政策金利は0.50%で据え置き"],
        "outlook_lines": ["本日、注目の経済イベントはありません", "為替は安定的に推移しており、大きな変動は見込まれません"],
        "is_monday": True,
    }
    print(generate_report(dummy, review))
