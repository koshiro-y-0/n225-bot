"""
config.py の基本テスト
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import NIKKEI_MILESTONES, EPS_MILESTONES, PER_LONG_TERM_AVERAGE


def test_nikkei_milestones_sorted():
    assert NIKKEI_MILESTONES == sorted(NIKKEI_MILESTONES)


def test_eps_milestones_sorted():
    assert EPS_MILESTONES == sorted(EPS_MILESTONES)


def test_per_average_positive():
    assert PER_LONG_TERM_AVERAGE > 0
