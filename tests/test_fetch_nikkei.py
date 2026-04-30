"""
fetch_nikkei.py の単体テスト
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.nikkei.fetch_nikkei import fetch_nikkei225, fetch_nikkei225_weekly, _build_fallback, FALLBACK_NIKKEI


class TestFetchNikkei225:
    """fetch_nikkei225 のテスト"""

    @patch("src.nikkei.fetch_nikkei.yf")
    def test_正常取得(self, mock_yf):
        """正常にデータを取得できるケース"""
        mock_ticker = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker

        # 5日分のダミーデータ
        dates = pd.date_range("2026-03-27", periods=5, freq="B")
        hist_5d = pd.DataFrame({
            "Close": [35000.0, 35500.0, 35200.0, 35800.0, 36000.0],
            "High": [35100.0, 35600.0, 35400.0, 35900.0, 36100.0],
        }, index=dates)

        # 1年分のダミーデータ（52週高値用）
        dates_1y = pd.date_range("2025-04-01", periods=250, freq="B")
        hist_1y = pd.DataFrame({
            "High": [35000 + i * 20 for i in range(250)],
            "Close": [35000 + i * 20 for i in range(250)],
        }, index=dates_1y)

        # 年初データ（YTD用）
        ytd_dates = pd.date_range("2026-01-02", periods=5, freq="B")
        hist_ytd = pd.DataFrame({
            "Close": [34000.0, 34100.0, 34200.0, 34300.0, 34400.0],
        }, index=ytd_dates)

        def history_side_effect(**kwargs):
            period = kwargs.get("period", "")
            start = kwargs.get("start", "")
            if period == "1y":
                return hist_1y
            # YTD は年始 (1月) からスタート、それ以外は main の直近45日取得
            if start.endswith("-01-01") or "-01-" in start[:8]:
                return hist_ytd
            return hist_5d

        mock_ticker.history.side_effect = history_side_effect

        result = fetch_nikkei225()

        # close = hist[-1], prev_close = hist[-2] のシンプルロジック
        assert result["nikkei_close"] == 36000.0
        assert result["nikkei_prev_close"] == 35800.0
        assert result["nikkei_diff"] == 200.0
        assert result["nikkei_diff_pct"] > 0
        assert "fetch_date" in result
        assert "fetch_weekday" in result

    @patch("src.nikkei.fetch_nikkei.yf")
    def test_fast_infoは使われない(self, mock_yf):
        """fast_info の値が history と異なっても history を信頼する（PR #14 リグレッション防止）"""
        mock_ticker = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker

        # history: 4/27=60537, 4/28=59917 が末尾
        hist_main = pd.DataFrame({
            "Close": [59716.0, 60537.0, 59917.0],
            "High":  [59800.0, 60600.0, 60000.0],
        }, index=pd.date_range("2026-04-24", periods=3, freq="B"))

        dates_1y = pd.date_range("2025-04-01", periods=250, freq="B")
        hist_1y = pd.DataFrame({
            "High":  [35000 + i * 20 for i in range(250)],
            "Close": [35000 + i * 20 for i in range(250)],
        }, index=dates_1y)
        ytd_dates = pd.date_range("2026-01-02", periods=5, freq="B")
        hist_ytd = pd.DataFrame({
            "Close": [34000.0, 34100.0, 34200.0, 34300.0, 34400.0],
        }, index=ytd_dates)

        def history_side_effect(**kwargs):
            period = kwargs.get("period", "")
            start  = kwargs.get("start", "")
            if period == "1y":
                return hist_1y
            if start.endswith("-01-01") or "-01-" in start[:8]:
                return hist_ytd
            return hist_main

        mock_ticker.history.side_effect = history_side_effect
        # Yahoo の fast_info はしばしば "1日前" の値を previousClose として返すが
        # 我々のロジックではこれを無視し、history を信頼する
        mock_ticker.fast_info = {"previousClose": 60537.0}  # 1日前の値（罠）

        result = fetch_nikkei225()

        # close は history[-1] = 4/28終値、prev_close は history[-2] = 4/27終値
        assert result["nikkei_close"] == 59917.0
        assert result["nikkei_prev_close"] == 60537.0
        assert result["nikkei_diff"] == round(59917.0 - 60537.0, 2)
        assert result["nikkei_diff_pct"] < 0

    @patch("src.nikkei.fetch_nikkei.yf")
    def test_API障害時はフォールバック(self, mock_yf):
        """yfinance がエラーの場合フォールバック値を返す"""
        mock_yf.Ticker.side_effect = Exception("API Error")

        result = fetch_nikkei225()

        assert result["nikkei_close"] == FALLBACK_NIKKEI["close"]
        assert result["nikkei_diff"] == 0.0

    def test_フォールバック構造(self):
        """フォールバック値が正しい構造を持つ"""
        from src.common.tz import now_jst
        result = _build_fallback(now_jst())

        required_keys = [
            "nikkei_close", "nikkei_prev_close", "nikkei_diff",
            "nikkei_diff_pct", "nikkei_high_52w", "nikkei_ytd_pct",
            "fetch_date", "fetch_weekday", "fetch_time",
        ]
        for key in required_keys:
            assert key in result, f"キー '{key}' がフォールバックに存在しない"


class TestFetchNikkeiWeekly:
    """fetch_nikkei225_weekly のテスト"""

    @patch("src.nikkei.fetch_nikkei.yf")
    def test_正常取得(self, mock_yf):
        mock_ticker = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker

        dates = pd.date_range("2026-03-24", periods=8, freq="B")
        hist = pd.DataFrame({
            "Close": [35000 + i * 100 for i in range(8)],
        }, index=dates)
        mock_ticker.history.return_value = hist

        result = fetch_nikkei225_weekly(5)

        assert len(result) == 5
        assert "date" in result[0]
        assert "weekday" in result[0]
        assert "close" in result[0]

    @patch("src.nikkei.fetch_nikkei.yf")
    def test_空データ(self, mock_yf):
        mock_ticker = MagicMock()
        mock_yf.Ticker.return_value = mock_ticker
        mock_ticker.history.return_value = pd.DataFrame()

        result = fetch_nikkei225_weekly()
        assert result == []
