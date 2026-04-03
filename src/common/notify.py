"""
notify.py
LINE Messaging API と Discord Webhook への通知送信モジュール
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

LINE_CHANNEL_TOKEN = os.getenv("LINE_CHANNEL_TOKEN")
LINE_USER_ID = os.getenv("LINE_USER_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")


# Quick Reply ボタン定義（詳細情報の選択肢）
QUICK_REPLY_ITEMS = [
    {"label": "📊 為替詳細", "text": "詳細:為替"},
    {"label": "🎯 金利詳細", "text": "詳細:金利"},
    {"label": "📈 CPI詳細", "text": "詳細:CPI"},
    {"label": "🏭 短観詳細", "text": "詳細:短観"},
    {"label": "📖 用語解説", "text": "解説:一覧"},
]


def _build_quick_reply() -> dict:
    """Quick Reply ボタンのペイロードを構築する"""
    return {
        "items": [
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": item["label"],
                    "text": item["text"],
                },
            }
            for item in QUICK_REPLY_ITEMS
        ]
    }


def send_line(message: str, with_quick_reply: bool = False) -> bool:
    """
    LINE Messaging API でメッセージを送信する
    Args:
        message: 送信するテキスト
        with_quick_reply: True の場合、Quick Reply ボタンを付与する
    Returns:
        送信成功ならTrue
    """
    if not LINE_CHANNEL_TOKEN or not LINE_USER_ID:
        print("[WARN] LINE環境変数が未設定のため送信をスキップします")
        return False

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_TOKEN}",
        "Content-Type": "application/json",
    }
    text_message = {"type": "text", "text": message}
    if with_quick_reply:
        text_message["quickReply"] = _build_quick_reply()

    payload = {
        "to": LINE_USER_ID,
        "messages": [text_message],
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        print("[OK] LINE送信成功" + ("（Quick Reply付き）" if with_quick_reply else ""))
        return True
    except requests.HTTPError as e:
        print(f"[ERROR] LINE送信失敗: {e.response.status_code} {e.response.text}")
        return False
    except Exception as e:
        print(f"[ERROR] LINE送信エラー: {e}")
        return False


def send_line_image(image_url: str, preview_url: str = None) -> bool:
    """
    LINE Messaging API で画像を送信する
    Args:
        image_url: 画像のURL
        preview_url: プレビュー画像のURL（省略時はimage_urlと同じ）
    Returns:
        送信成功ならTrue
    """
    if not LINE_CHANNEL_TOKEN or not LINE_USER_ID:
        print("[WARN] LINE環境変数が未設定のため画像送信をスキップします")
        return False

    if preview_url is None:
        preview_url = image_url

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{
            "type": "image",
            "originalContentUrl": image_url,
            "previewImageUrl": preview_url,
        }],
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        print("[OK] LINE画像送信成功")
        return True
    except requests.HTTPError as e:
        print(f"[ERROR] LINE画像送信失敗: {e.response.status_code} {e.response.text}")
        return False
    except Exception as e:
        print(f"[ERROR] LINE画像送信エラー: {e}")
        return False


def send_discord(message: str) -> bool:
    """
    Discord Webhook にメッセージを送信する
    Args:
        message: 送信するテキスト
    Returns:
        送信成功ならTrue
    """
    if not DISCORD_WEBHOOK_URL:
        print("[WARN] DISCORD_WEBHOOK_URLが未設定のため送信をスキップします")
        return False

    payload = {"content": message}
    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
        response.raise_for_status()
        print("[OK] Discord送信成功")
        return True
    except requests.HTTPError as e:
        print(f"[ERROR] Discord送信失敗: {e.response.status_code} {e.response.text}")
        return False
    except Exception as e:
        print(f"[ERROR] Discord送信エラー: {e}")
        return False


def send_all(message: str, with_quick_reply: bool = False) -> None:
    """
    設定済みのすべての通知先にメッセージを送信する
    Args:
        message: 送信するテキスト
        with_quick_reply: True の場合、LINE に Quick Reply ボタンを付与する
    """
    line_ok = send_line(message, with_quick_reply=with_quick_reply)
    discord_ok = send_discord(message)

    if not line_ok and not discord_ok:
        print("[WARN] すべての通知チャンネルへの送信に失敗しました")


def check_alerts(data: dict) -> list[str]:
    """
    指標データからアラートの種別リストを返す
    Args:
        data: fetch_indicators.fetch_all() の返り値
    Returns:
        発生したアラート種別のリスト（例: ["forex", "cpi"]）
    """
    alerts = []

    usdjpy_diff = abs(data["usdjpy"] - data["usdjpy_prev"])
    if usdjpy_diff >= 1.5:
        alerts.append("forex")

    rate_diff = data["policy_rate"] - data["policy_rate_prev"]
    if rate_diff != 0:
        alerts.append("rate_change")

    cpi_diff = abs(data["cpi_total"] - data.get("cpi_prev_total", data["cpi_total"]))
    if cpi_diff >= 0.5:
        alerts.append("cpi")

    return alerts


if __name__ == "__main__":
    test_msg = "🏦 テスト送信：植田総裁Botの通知テストです。"
    send_all(test_msg)
