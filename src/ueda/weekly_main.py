"""
weekly_main.py
金曜日の週間サマリー配信エントリーポイント
GitHub Actions から呼び出される
"""

import os
import sys
from pathlib import Path

# プロジェクトルートをモジュール検索パスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


from src.common.data_store import load_week_data
from src.ueda.generate_weekly import generate_weekly_report
from src.ueda.generate_chart import generate_forex_chart
from src.common.notify import send_line, send_line_image
from src.common.tz import now_jst


def upload_chart_to_github(image_path: str) -> str:
    """
    チャート画像を GitHub リポジトリの data/ にコミットし、
    raw URL を返す。GitHub Actions 上で実行される前提。
    Args:
        image_path: ローカルの画像ファイルパス
    Returns:
        GitHub raw URL
    """
    import shutil

    filename = f"chart_weekly_{now_jst().strftime('%Y%m%d')}.png"
    dest = Path(__file__).parent.parent / "data" / filename
    shutil.copy2(image_path, dest)

    # GitHub の raw URL を構築
    repo = os.getenv("GITHUB_REPOSITORY", "koshiro-y-0/uedabot")
    branch = "main"
    raw_url = f"https://raw.githubusercontent.com/{repo}/{branch}/data/{filename}"

    print(f"[OK] チャート画像をコピーしました: {dest}")
    print(f"[INFO] 画像URL（push後に有効）: {raw_url}")
    return str(dest)


def main():
    # 1. 今週のデータを取得
    week_data = load_week_data()

    if not week_data:
        print("[WARN] 今週のデータがありません。サマリーを送信しません。")
        return

    # 2. 週間サマリーレポートを生成
    report = generate_weekly_report(week_data)
    print("--- 週間サマリー ---")
    print(report)
    print("--------------------")

    # 3. チャート画像を生成
    chart_path = generate_forex_chart(week_data)

    # 4. テキストレポートを送信
    send_line(report, with_quick_reply=True)

    # 5. チャート画像をリポジトリに保存（push はワークフロー側で行う）
    if chart_path:
        saved_path = upload_chart_to_github(chart_path)

        # チャートのパスを環境変数ファイルに出力（後続ステップで利用）
        github_output = os.getenv("GITHUB_OUTPUT")
        if github_output:
            with open(github_output, "a") as f:
                f.write(f"chart_path={saved_path}\n")

        # 元の一時ファイルを削除
        try:
            os.unlink(chart_path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
