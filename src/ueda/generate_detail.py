"""
generate_detail.py
詳細レポート生成モジュール — Quick Reply 応答用の詳細レポートを生成する
"""

from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from src.ueda.fetch_detail import fetch_detail

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"

# カテゴリ → テンプレートファイルのマッピング
DETAIL_TEMPLATES = {
    "為替": "detail_forex.j2",
    "金利": "detail_rate.j2",
    "CPI": "detail_cpi.j2",
    "短観": "detail_tankan.j2",
    "注目": "detail_events.j2",
}


def generate_detail_report(category: str) -> str:
    """
    カテゴリに応じた詳細レポートを生成する
    Args:
        category: "為替", "金利", "CPI", "短観", "注目" のいずれか
    Returns:
        詳細レポート文字列
    """
    template_name = DETAIL_TEMPLATES.get(category)
    if template_name is None:
        return f"⚠️ 「{category}」は不明なカテゴリです。\n為替・金利・CPI・短観・注目 のいずれかを指定してください。"

    data = fetch_detail(category)

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template(template_name)
    return template.render(data)


def parse_detail_command(text: str) -> str | None:
    """
    ユーザーメッセージから詳細カテゴリを抽出する
    Args:
        text: ユーザーの送信テキスト（例: "詳細:為替"）
    Returns:
        カテゴリ名（マッチしなければ None）
    """
    if not text.startswith("詳細:") and not text.startswith("詳細："):
        return None
    # "詳細:" or "詳細：" の後の文字列を取得
    category = text.split(":", 1)[-1] if ":" in text else text.split("：", 1)[-1]
    category = category.strip()
    if category in DETAIL_TEMPLATES:
        return category
    return None


if __name__ == "__main__":
    for cat in DETAIL_TEMPLATES:
        print(f"\n{'='*50}")
        print(generate_detail_report(cat))
