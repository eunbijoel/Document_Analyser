"""HWP analysis repo path — 기존 A/B 코드 재사용."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_DA_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_HWP_ROOT = Path("/home/eunbi/HWP analysis")

HWP_ANALYSIS_ROOT = Path(os.environ.get("HWP_ANALYSIS_ROOT", str(_DEFAULT_HWP_ROOT))).resolve()


def ensure_hwp_paths() -> Path:
    root = HWP_ANALYSIS_ROOT
    if not root.is_dir():
        raise RuntimeError(
            f"HWP analysis repo not found: {root}\n"
            "Set HWP_ANALYSIS_ROOT to the directory containing hwp_core/."
        )
    for p in (root, root / "HWP_v2"):
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)
    return root
