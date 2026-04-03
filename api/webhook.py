"""
webhook.py
Vercel Serverless Function — LINE Webhook を受信して詳細レポートを返す
"""

import os
import json
import hashlib
import hmac
import base64
from http.server import BaseHTTPRequestHandler

import sys
from pathlib import Path

# プロジェクトルートをモジュール検索パスに追加
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import requests
from src.ueda.generate_detail import generate_detail_report, parse_detail_command
from src.ueda.generate_glossary import parse_glossary_command, generate_glossary_list, generate_glossary_report
from src.common.notify import _build_quick_reply

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_TOKEN = os.getenv("LINE_CHANNEL_TOKEN", "")


def verify_signature(body: str, signature: str) -> bool:
    """
    LINE Webhook の署名を検証する
    Args:
        body: リクエストボディ（生文字列）
        signature: X-Line-Signature ヘッダーの値
    Returns:
        署名が正しければ True
    """
    if not LINE_CHANNEL_SECRET:
        print("[WARN] LINE_CHANNEL_SECRET が未設定です")
        return False

    hash_value = hmac.new(
        LINE_CHANNEL_SECRET.encode("utf-8"),
        body.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected = base64.b64encode(hash_value).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def reply_message(reply_token: str, text: str) -> bool:
    """
    LINE Reply Message API でメッセージを返信する（Quick Reply ボタン付き）
    Args:
        reply_token: Webhook イベントの replyToken
        text: 返信するテキスト
    Returns:
        送信成功なら True
    """
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_TOKEN}",
        "Content-Type": "application/json",
    }
    text_message = {"type": "text", "text": text, "quickReply": _build_quick_reply()}
    payload = {
        "replyToken": reply_token,
        "messages": [text_message],
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"[OK] Reply送信成功")
        return True
    except Exception as e:
        print(f"[ERROR] Reply送信失敗: {e}")
        return False


def handle_webhook_event(event: dict) -> None:
    """
    Webhook イベントを処理する
    Args:
        event: LINE Webhook のイベントオブジェクト
    """
    event_type = event.get("type")
    if event_type != "message":
        return

    message = event.get("message", {})
    if message.get("type") != "text":
        return

    text = message.get("text", "")
    reply_token = event.get("replyToken", "")

    # 「解説:〇〇」コマンドを解析
    glossary_key = parse_glossary_command(text)
    if glossary_key is not None:
        try:
            if glossary_key == "一覧":
                report = generate_glossary_list()
            else:
                report = generate_glossary_report(glossary_key)
            reply_message(reply_token, report)
        except Exception as e:
            print(f"[ERROR] 用語解説生成エラー: {e}")
            reply_message(reply_token, "⚠️ 用語解説の生成中にエラーが発生しました。")
        return

    # 「詳細:〇〇」コマンドを解析
    category = parse_detail_command(text)
    if category is None:
        return

    # 詳細レポートを生成して返信
    try:
        report = generate_detail_report(category)
        reply_message(reply_token, report)
    except Exception as e:
        print(f"[ERROR] 詳細レポート生成エラー: {e}")
        reply_message(reply_token, "⚠️ 詳細データの取得中にエラーが発生しました。\nしばらくしてからもう一度お試しください。")


class handler(BaseHTTPRequestHandler):
    """Vercel Serverless Function のハンドラー"""

    def do_GET(self):
        """ヘルスチェック用"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "bot": "uedabot"}).encode())

    def do_POST(self):
        """LINE Webhook イベントを受信"""
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")

        # 署名検証
        signature = self.headers.get("X-Line-Signature", "")
        if not verify_signature(body, signature):
            print("[ERROR] 署名検証に失敗しました")
            self.send_response(403)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Invalid signature"}).encode())
            return

        # イベント処理
        try:
            data = json.loads(body)
            events = data.get("events", [])
            for event in events:
                handle_webhook_event(event)
        except json.JSONDecodeError:
            print("[ERROR] JSONパースエラー")

        # LINE には 200 を返す（必須）
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok"}).encode())
