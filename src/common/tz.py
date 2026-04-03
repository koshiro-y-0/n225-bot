"""
tz.py
日本標準時 (JST) を返すユーティリティ
"""

from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


def now_jst() -> datetime:
    """日本標準時の現在時刻を返す"""
    return datetime.now(JST)
