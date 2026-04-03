"""
jpx_scraper.py の単体テスト
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.nikkei.jpx_scraper import (
    calc_eps,
    _generate_per_comment,
    _format_month,
    _build_fallback,
)


class TestCalcEps:
    """EPS 算出のテスト"""

    def test_正常算出(self):
        assert calc_eps(36000.0, 15.0) == 2400.0

    def test_PERゼロ(self):
        assert calc_eps(36000.0, 0) == 0.0

    def test_PERマイナス(self):
        assert calc_eps(36000.0, -5.0) == 0.0


class TestGeneratePerComment:
    """PER水準コメントのテスト"""

    def test_大幅上回り(self):
        comment = _generate_per_comment(20.0)
        assert "上回" in comment

    def test_やや上回り(self):
        comment = _generate_per_comment(16.5)
        assert "やや上回" in comment

    def test_水準(self):
        comment = _generate_per_comment(15.0)
        assert "水準" in comment

    def test_やや下回り(self):
        comment = _generate_per_comment(13.5)
        assert "やや下回" in comment

    def test_大幅下回り(self):
        comment = _generate_per_comment(10.0)
        assert "下回" in comment


class TestFormatMonth:
    """月フォーマットのテスト"""

    def test_正常(self):
        assert _format_month("2026/03") == "2026年3月"

    def test_異常値(self):
        result = _format_month("invalid")
        assert result == "invalid"


class TestBuildFallback:
    """フォールバックのテスト"""

    def test_構造(self):
        fb = _build_fallback()
        assert "per" in fb
        assert "pbr" in fb
        assert "per_comment" in fb
        assert "data_month" in fb
        assert fb["per"] > 0
