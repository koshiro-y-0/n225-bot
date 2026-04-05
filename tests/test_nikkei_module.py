"""
nikkei_module.py の単体テスト
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.nikkei.nikkei_module import (
    _get_milestone_band,
    _find_crossed_milestone,
    check_nikkei_milestones,
    check_eps_milestones,
    MILESTONE_STATE_FILE,
)
from config import NIKKEI_MILESTONES, EPS_MILESTONES


class TestGetMilestoneBand:
    """節目バンド判定のテスト"""

    def test_最低バンド(self):
        assert _get_milestone_band(30000, NIKKEI_MILESTONES) == 0

    def test_中間バンド(self):
        # 36000〜38000 の間 → band=2
        assert _get_milestone_band(37000, NIKKEI_MILESTONES) == 2

    def test_最高バンド(self):
        assert _get_milestone_band(50000, NIKKEI_MILESTONES) == len(NIKKEI_MILESTONES)

    def test_節目ちょうど(self):
        # 36000ちょうど → 次のバンド（36000以上38000未満）
        assert _get_milestone_band(36000, NIKKEI_MILESTONES) == 2


class TestFindCrossedMilestone:
    """超えた節目の特定テスト"""

    def test_上昇(self):
        # band 2 → band 3: 38000を超えた
        result = _find_crossed_milestone(2, 3, NIKKEI_MILESTONES)
        assert result == 38000

    def test_下落(self):
        # band 3 → band 2: 38000を割り込んだ
        result = _find_crossed_milestone(3, 2, NIKKEI_MILESTONES)
        assert result == 38000

    def test_複数バンド飛び越し上昇(self):
        # band 1 → band 3: 36000, 38000を超えた → 最も高い38000を報告
        result = _find_crossed_milestone(1, 3, NIKKEI_MILESTONES)
        assert result == 38000

    def test_複数バンド飛び越し下落(self):
        # band 4 → band 1: 40000, 38000, 36000を割った → 最も低い36000を報告
        result = _find_crossed_milestone(4, 1, NIKKEI_MILESTONES)
        assert result == 36000


class TestCheckNikkeiMilestones:
    """日経平均節目チェックのテスト"""

    def setup_method(self):
        """各テスト前に状態ファイルを初期化"""
        self._cleanup()

    def teardown_method(self):
        """各テスト後に状態ファイルを削除"""
        self._cleanup()

    def _cleanup(self):
        if MILESTONE_STATE_FILE.exists():
            MILESTONE_STATE_FILE.unlink()

    def test_初回は変化なし(self):
        """初回実行時はアラートなし（状態の初期化のみ）"""
        result = check_nikkei_milestones(37000)
        assert result is None

    def test_節目超えでアラート(self):
        """前回と異なるバンドに入るとアラート発生"""
        # 1回目: 37000（band=2, 36000〜38000の間）
        check_nikkei_milestones(37000)
        # 2回目: 39000（band=3, 38000〜40000の間）→ 38000を超えた
        result = check_nikkei_milestones(39000)
        assert result is not None
        assert result["type"] == "nikkei"
        assert result["milestone"] == 38000
        assert result["direction"] == "上昇"

    def test_同一バンドは変化なし(self):
        """同じバンド内の変動ではアラートなし"""
        check_nikkei_milestones(37000)
        result = check_nikkei_milestones(37500)
        assert result is None


class TestCheckEpsMilestones:
    """EPS節目チェックのテスト"""

    def setup_method(self):
        if MILESTONE_STATE_FILE.exists():
            MILESTONE_STATE_FILE.unlink()

    def teardown_method(self):
        if MILESTONE_STATE_FILE.exists():
            MILESTONE_STATE_FILE.unlink()

    def test_初回は変化なし(self):
        result = check_eps_milestones(2350)
        assert result is None

    def test_EPS上昇でアラート(self):
        check_eps_milestones(2350)  # band=2 (2300〜2400)
        result = check_eps_milestones(2450)  # band=3 (2400〜2500)
        assert result is not None
        assert result["type"] == "eps"
        assert result["direction"] == "上昇"
