"""
nikkei_module.py
日経平均のデータ取得・メッセージ整形・節目アラート判定を統合するモジュール
"""

import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.nikkei.fetch_nikkei import fetch_nikkei225
from src.nikkei.jpx_scraper import fetch_per_pbr, calc_eps
from config import NIKKEI_MILESTONES, EPS_MILESTONES

# 前回節目状態を保存するファイルパス
MILESTONE_STATE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "milestone_state.json"


def fetch_nikkei_data() -> dict:
    """
    日経平均の全データ（株価 + PER/EPS）を統合して取得する。
    Returns:
        統合データ辞書
    """
    # 日経平均株価
    nikkei = fetch_nikkei225()

    # JPX PER/PBR
    per_data = fetch_per_pbr()

    # EPS算出
    eps = calc_eps(nikkei["nikkei_close"], per_data["per"])

    return {
        **nikkei,
        "per": per_data["per"],
        "pbr": per_data["pbr"],
        "per_simple": per_data["per_simple"],
        "per_data_month": per_data["data_month"],
        "per_comment": per_data["per_comment"],
        "eps": eps,
    }


def check_nikkei_milestones(current_close: float) -> Optional[dict]:
    """
    日経平均が節目を超えたかチェックする（重複通知防止付き）。
    Args:
        current_close: 現在の日経平均終値
    Returns:
        節目アラート情報の辞書。節目を超えていなければ None。
    """
    prev_state = _load_milestone_state()
    prev_band = prev_state.get("nikkei_band")

    current_band = _get_milestone_band(current_close, NIKKEI_MILESTONES)

    if prev_band is not None and current_band != prev_band:
        # 節目の変化を検知
        direction = "上昇" if current_band > prev_band else "下落"
        milestone = _find_crossed_milestone(prev_band, current_band, NIKKEI_MILESTONES)

        # 状態を更新
        _save_milestone_state(nikkei_band=current_band, eps_band=prev_state.get("eps_band"))

        return {
            "type": "nikkei",
            "milestone": milestone,
            "direction": direction,
            "current": current_close,
        }

    # 初回または変化なし → 状態のみ更新
    _save_milestone_state(nikkei_band=current_band, eps_band=prev_state.get("eps_band"))
    return None


def check_eps_milestones(eps: float) -> Optional[dict]:
    """
    日経EPSが節目を超えたかチェックする（重複通知防止付き）。
    Args:
        eps: 現在のEPS
    Returns:
        節目アラート情報の辞書。節目を超えていなければ None。
    """
    prev_state = _load_milestone_state()
    prev_band = prev_state.get("eps_band")

    current_band = _get_milestone_band(eps, EPS_MILESTONES)

    if prev_band is not None and current_band != prev_band:
        direction = "上昇" if current_band > prev_band else "下落"
        milestone = _find_crossed_milestone(prev_band, current_band, EPS_MILESTONES)

        _save_milestone_state(nikkei_band=prev_state.get("nikkei_band"), eps_band=current_band)

        return {
            "type": "eps",
            "milestone": milestone,
            "direction": direction,
            "current": eps,
        }

    _save_milestone_state(nikkei_band=prev_state.get("nikkei_band"), eps_band=current_band)
    return None


def _get_milestone_band(value: float, milestones: list) -> int:
    """
    値がどの節目バンドに属するかを返す。
    例: milestones=[34000, 36000, 38000], value=37000 → band=2（36000〜38000）
    """
    for i, m in enumerate(milestones):
        if value < m:
            return i
    return len(milestones)


def _find_crossed_milestone(prev_band: int, current_band: int, milestones: list) -> int:
    """超えた節目の値を返す"""
    if current_band > prev_band:
        # 上昇: prev_band 番目の節目を超えた
        idx = min(prev_band, len(milestones) - 1)
        return milestones[idx]
    else:
        # 下落: current_band 番目の節目を下回った
        idx = min(current_band, len(milestones) - 1)
        return milestones[idx]


def _load_milestone_state() -> dict:
    """前回の節目状態をファイルから読み込む"""
    if MILESTONE_STATE_FILE.exists():
        try:
            with open(MILESTONE_STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_milestone_state(nikkei_band: int = None, eps_band: int = None) -> None:
    """節目状態をファイルに保存する"""
    state = {}
    if nikkei_band is not None:
        state["nikkei_band"] = nikkei_band
    if eps_band is not None:
        state["eps_band"] = eps_band

    MILESTONE_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MILESTONE_STATE_FILE, "w") as f:
        json.dump(state, f)


if __name__ == "__main__":
    data = fetch_nikkei_data()
    print("=== 日経平均 統合データ ===")
    for k, v in data.items():
        print(f"  {k}: {v}")

    # 節目判定テスト
    print("\n=== 節目判定テスト ===")
    alert = check_nikkei_milestones(data["nikkei_close"])
    if alert:
        print(f"  日経アラート: {alert}")
    else:
        print("  日経: 節目変化なし")

    alert_eps = check_eps_milestones(data["eps"])
    if alert_eps:
        print(f"  EPSアラート: {alert_eps}")
    else:
        print("  EPS: 節目変化なし")
