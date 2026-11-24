"""Xây danh mục long-only từ dự báo + khoảng conformal."""

from __future__ import annotations

import numpy as np
import pandas as pd


def target_weights(day: pd.DataFrame, pcfg: dict) -> pd.Series:
    """day: DataFrame 1 ngày, index=ticker, cột pred, lo, hi. Trả về trọng số >= 0, tổng <= 1."""
    d = day.dropna(subset=["pred"])
    if pcfg.get("sizing") == "conformal":
        d = d[d["lo"] > pcfg.get("min_lower_bound", 0.0)]  # chỉ mua khi "chắc chắn" dương
    d = d.nlargest(pcfg["top_k"], "pred")
    if d.empty:
        return pd.Series(dtype=float)
    if pcfg.get("sizing") == "conformal":
        width = (d["hi"] - d["lo"]).replace(0, np.nan)
        raw = (d["pred"].clip(lower=0) / width).fillna(0)  # dự báo cao, khoảng hẹp → tỷ trọng lớn
    else:
        raw = pd.Series(1.0, index=d.index)
    w = raw / raw.sum() if raw.sum() > 0 else raw
    return _cap(w, pcfg.get("max_weight", 1.0))


def _cap(w: pd.Series, cap: float, iters: int = 10) -> pd.Series:
    for _ in range(iters):
        over = w > cap
        if not over.any():
            break
        excess = (w[over] - cap).sum()
        w[over] = cap
        under = ~over
        if w[under].sum() == 0:
            break
        w[under] += excess * w[under] / w[under].sum()
    return w.clip(upper=cap)
