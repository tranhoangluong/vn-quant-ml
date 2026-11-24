"""Ghép tất cả nhóm feature theo config."""

from __future__ import annotations

import pandas as pd

from . import price
from .cross_section import cs_rank

GROUPS = {
    "momentum": lambda p, w: price.momentum(p, w),
    "volatility": lambda p, w: price.volatility(p, [x for x in w if x >= 5]),
    "liquidity": lambda p, w: price.liquidity(p, [x for x in w if x <= 63]),
    "reversal": lambda p, w: price.reversal(p),
    "technical": lambda p, w: price.technical(p),
}


def build_features(panel: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    fc = cfg["features"]
    parts = [GROUPS[g](panel, fc["windows"]) for g in fc["groups"]]
    X = pd.concat(parts, axis=1)
    if fc.get("cross_sectional_rank", True):
        X = cs_rank(X)
    return X
