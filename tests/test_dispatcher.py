"""
dispatcher.py の単体テスト
"""

import sys
from pathlib import Path
from unittest.mock import patch
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import dispatcher


class TestGetPrevFridayDate:
    """_get_prev_friday_date のテスト"""

    def test_月曜は3日前を返す(self):
        # 2026-04-06(月) → 2026-04-03(金)
        mock_now = datetime(2026, 4, 6, 8, 30)
        with patch("dispatcher.now_jst", return_value=mock_now):
            result = dispatcher._get_prev_friday_date()
        assert "4月3日" in result

    def test_火曜は1日前を返す(self):
        # 2026-04-07(火) → 2026-04-06(月)
        mock_now = datetime(2026, 4, 7, 8, 30)
        with patch("dispatcher.now_jst", return_value=mock_now):
            result = dispatcher._get_prev_friday_date()
        assert "4月6日" in result


class TestRenderNikkeiBlock:
    """render_nikkei_block のテスト"""

    def _sample_data(self):
        return {
            "nikkei_close": 38500.0,
            "nikkei_prev_close": 38200.0,
            "nikkei_diff": 300.0,
            "nikkei_diff_pct": 0.78,
            "nikkei_high_52w": 42000.0,
            "nikkei_ytd_pct": 5.5,
            "per": 15.5,
            "eps": 2484.0,
            "per_comment": "PERは概ね水準",
            "fetch_date": "2026年4月7日",
            "fetch_weekday": "火",
            "fetch_time": "08:30",
        }

    def test_平日レンダリング(self):
        result = dispatcher.render_nikkei_block(self._sample_data(), is_monday=False)
        assert "38,500円" in result
        assert "前日終値" in result
        assert "先週金曜日" not in result

    def test_月曜レンダリング(self):
        result = dispatcher.render_nikkei_block(self._sample_data(), is_monday=True)
        assert "金曜終値" in result
        assert "先週金曜日" in result


class TestRenderIntegrated:
    """render_integrated のテスト"""

    def test_両ブロック含まれる(self):
        nikkei = "【日経】テスト日経ブロック"
        ueda = "【日銀】テスト日銀ブロック"
        result = dispatcher.render_integrated(nikkei, ueda)
        assert "テスト日経ブロック" in result
        assert "テスト日銀ブロック" in result
