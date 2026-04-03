"""
generate_richmenu.py
Pillow でリッチメニュー画像を生成し、LINE Messaging API で登録するモジュール
"""

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import requests

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# リッチメニュー画像サイズ（LINE推奨）
WIDTH = 2500
HEIGHT = 843
HALF_W = WIDTH // 3
HALF_H = HEIGHT // 2

# 6分割ボタン定義
MENU_BUTTONS = [
    # 上段
    {"label": "為替", "emoji": "📊", "text": "詳細:為替", "row": 0, "col": 0},
    {"label": "金利", "emoji": "🎯", "text": "詳細:金利", "row": 0, "col": 1},
    {"label": "CPI", "emoji": "📈", "text": "詳細:CPI", "row": 0, "col": 2},
    # 下段
    {"label": "短観", "emoji": "🏭", "text": "詳細:短観", "row": 1, "col": 0},
    {"label": "用語", "emoji": "📖", "text": "解説:一覧", "row": 1, "col": 1},
    {"label": "注目", "emoji": "📰", "text": "詳細:注目", "row": 1, "col": 2},
]

# 配色
BG_COLOR = "#1A237E"       # 深い紺色（日銀イメージ）
CELL_BG = "#283593"        # セル背景
BORDER_COLOR = "#3949AB"   # 境界線
TEXT_COLOR = "#FFFFFF"      # テキスト白
ACCENT_COLOR = "#FFD54F"   # アクセント（ゴールド）


def generate_richmenu_image(output_path: str = None) -> str:
    """
    2500×843px のリッチメニュー画像を生成する。
    Args:
        output_path: 保存先パス（省略時はプロジェクト内のデフォルトパス）
    Returns:
        生成された画像ファイルのパス
    """
    if output_path is None:
        output_path = str(PROJECT_ROOT / "data" / "richmenu.png")

    # data/ ディレクトリ作成
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # フォント設定（システムフォントを試行）
    font_large = _get_font(48)
    font_emoji = _get_font(36)

    for btn in MENU_BUTTONS:
        x0 = btn["col"] * HALF_W
        y0 = btn["row"] * HALF_H
        x1 = x0 + HALF_W
        y1 = y0 + HALF_H

        # セル背景
        draw.rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2], fill=CELL_BG)

        # 境界線
        draw.rectangle([x0, y0, x1, y1], outline=BORDER_COLOR, width=3)

        # テキスト描画（中央揃え）
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2

        # ラベル（大きく）
        label = btn["label"]
        bbox = draw.textbbox((0, 0), label, font=font_large)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((cx - tw // 2, cy - th // 2 + 10), label, fill=TEXT_COLOR, font=font_large)

        # サブテキスト（小さく）
        sub = btn["text"]
        font_sub = _get_font(24)
        bbox_sub = draw.textbbox((0, 0), sub, font=font_sub)
        sw = bbox_sub[2] - bbox_sub[0]
        draw.text((cx - sw // 2, cy + th // 2 + 20), sub, fill=ACCENT_COLOR, font=font_sub)

    img.save(output_path)
    print(f"[OK] リッチメニュー画像を生成しました: {output_path}")
    return output_path


def _get_font(size: int):
    """利用可能なフォントを取得する"""
    font_candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    for path in font_candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def build_richmenu_object() -> dict:
    """
    LINE Messaging API に送信するリッチメニューオブジェクトを構築する。
    Returns:
        リッチメニューのJSON構造
    """
    areas = []
    for btn in MENU_BUTTONS:
        x = btn["col"] * HALF_W
        y = btn["row"] * HALF_H
        areas.append({
            "bounds": {
                "x": x,
                "y": y,
                "width": HALF_W,
                "height": HALF_H,
            },
            "action": {
                "type": "message",
                "text": btn["text"],
            },
        })

    return {
        "size": {"width": WIDTH, "height": HEIGHT},
        "selected": True,
        "name": "植田総裁Bot メニュー",
        "chatBarText": "メニューを開く",
        "areas": areas,
    }


def register_richmenu() -> str | None:
    """
    LINE Messaging API でリッチメニューを登録する。
    1. リッチメニューオブジェクト作成
    2. 画像アップロード
    3. デフォルトリッチメニューに設定
    Returns:
        リッチメニューID（失敗時 None）
    """
    token = os.getenv("LINE_CHANNEL_TOKEN")
    if not token:
        print("[ERROR] LINE_CHANNEL_TOKEN が未設定です")
        return None

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # 1. リッチメニューオブジェクト作成
    print("[1/3] リッチメニューオブジェクトを作成中...")
    menu_obj = build_richmenu_object()
    resp = requests.post(
        "https://api.line.me/v2/bot/richmenu",
        json=menu_obj,
        headers=headers,
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"[ERROR] リッチメニュー作成失敗: {resp.status_code} {resp.text}")
        return None
    richmenu_id = resp.json().get("richMenuId")
    print(f"[OK] リッチメニューID: {richmenu_id}")

    # 2. 画像アップロード
    print("[2/3] リッチメニュー画像をアップロード中...")
    image_path = generate_richmenu_image()
    with open(image_path, "rb") as f:
        image_data = f.read()
    resp = requests.post(
        f"https://api-data.line.me/v2/bot/richmenu/{richmenu_id}/content",
        data=image_data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "image/png",
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"[ERROR] 画像アップロード失敗: {resp.status_code} {resp.text}")
        return None
    print("[OK] 画像アップロード完了")

    # 3. デフォルトリッチメニューに設定
    print("[3/3] デフォルトリッチメニューに設定中...")
    resp = requests.post(
        f"https://api.line.me/v2/bot/user/all/richmenu/{richmenu_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"[ERROR] デフォルト設定失敗: {resp.status_code} {resp.text}")
        return None
    print("[OK] デフォルトリッチメニューに設定完了")

    return richmenu_id


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--register":
        # LINE API にリッチメニューを登録
        result = register_richmenu()
        if result:
            print(f"\n✅ リッチメニュー登録完了: {result}")
        else:
            print("\n❌ リッチメニュー登録に失敗しました")
    else:
        # 画像のみ生成
        path = generate_richmenu_image()
        print(f"Generated: {path}")
        print("登録するには: python src/generate_richmenu.py --register")
