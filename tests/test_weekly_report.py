"""
src/nikkei/weekly_report.py の単体テスト
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.nikkei.weekly_report import compute_weekly_stats, render_weekly_report


class TestComputeWeeklyStats:
    """週次統計算出のテスト"""

    def _week(self):
        return [
            {"date": "2026-03-30", "weekday": "月", "close": 38100.0},
            {"date": "2026-03-31", "weekday": "火", "close": 38350.0},
            {"date": "2026-04-01", "weekday": "水", "close": 38200.0},
            {"date": "2026-04-02", "weekday": "木", "close": 38650.0},
            {"date": "2026-04-03", "weekday": "金", "close": 38800.0},
        ]

    def test_正常算出(self):
        stats = compute_weekly_stats(self._week(), per=15.5)
        assert stats["week_open"] == 38100.0
        assert stats["week_close"] == 38800.0
        assert stats["week_diff"] == 700.0
        assert stats["week_high"] == 38800.0
        assert stats["week_low"] == 38100.0
        assert stats["per"] == 15.5
        assert stats["eps"] > 0

    def test_空リスト(self):
        assert compute_weekly_stats([], per=15.0) == {}

    def test_1件のみ(self):
        assert compute_weekly_stats([{"date": "2026-04-03", "weekday": "金", "close": 38000.0}], per=15.0) == {}

    def test_週間下落(self):
        data = [
            {"date": "2026-03-30", "weekday": "月", "close": 39000.0},
            {"date": "2026-04-03", "weekday": "金", "close": 38000.0},
        ]
        stats = compute_weekly_stats(data, per=15.0)
        assert stats["week_diff"] == -1000.0
        assert stats["week_diff_pct"] < 0


class TestRenderWeeklyReport:
    """weekly_nikkei.j2 レンダリングのテスト"""

    def test_レンダリング(self):
        stats = {
            "week_start_date": "2026-03-30",
            "week_end_date": "2026-04-03",
            "week_open": 38100.0,
            "week_close": 38800.0,
            "week_diff": 700.0,
            "week_diff_pct": 1.84,
            "week_high": 38800.0,
            "week_low": 38100.0,
            "per": 15.5,
            "eps": 2503.0,
        }
        per_data = {"data_month": "2026年3月", "per_comment": "PERは概ね水準"}
        result = render_weekly_report(stats, per_data)
        assert "38,100円" in result
        assert "38,800円" in result
        assert "+700円" in result
        assert "+1.84%" in result
        assert "PERは概ね水準" in result
