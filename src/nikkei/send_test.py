"""
send_test.py
日経モジュール単体の通しテスト:
  fetch_nikkei_data() → daily_nikkei.j2 レンダリング → LINE送信
GitHub Actions workflow_dispatch から手動実行する用途。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from jinja2 import Environment, FileSystemLoader

from src.common.notify import send_line, send_discord
from src.common.tz import now_jst
from src.nikkei.nikkei_module import fetch_nikkei_data

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def render_daily_nikkei(data: dict) -> str:
    """daily_nikkei.j2 をレンダリングして本文を返す"""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("daily_nikkei.j2")

    now = now_jst()
    is_monday = now.weekday() == 0
    prev_date = ""  # 月曜日の場合の「先週金曜」表記はPhase 3で対応

    return template.render(
        is_monday=is_monday,
        prev_date=prev_date,
        **data,
    )


def main() -> int:
    print("=" * 50)
    print("日経モジュール 通しテスト開始")
    print("=" * 50)

    # 1. データ取得
    print("\n[1/3] データ取得中...")
    data = fetch_nikkei_data()
    print(f"  日経平均終値: {data['nikkei_close']:,.0f}円")
    print(f"  前日比:       {data['nikkei_diff']:+,.0f}円 ({data['nikkei_diff_pct']:+.2f}%)")
    print(f"  PER:          {data['per']:.1f}倍")
    print(f"  EPS:          {data['eps']:,.0f}円")

    # 2. テンプレートレンダリング
    print("\n[2/3] テンプレートレンダリング中...")
    message = render_daily_nikkei(data)
    print("--- メッセージ本文 ---")
    print(message)
    print("--- ここまで ---")

    # 3. 送信
    print("\n[3/3] 送信中...")
    line_ok = send_line(message)
    discord_ok = send_discord(message)

    print("\n" + "=" * 50)
    print(f"結果: LINE={'OK' if line_ok else 'NG'}  Discord={'OK' if discord_ok else 'NG'}")
    print("=" * 50)

    return 0 if (line_ok or discord_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
