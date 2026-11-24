"""Nhãn: lợi suất tương lai khớp với cách backtest khớp lệnh (tránh look-ahead).

next_close (mặc định): close(t+1) → close(t+1+h), đúng với engine khớp tại close t+1.
next_open: open(t+1) → open(t+1+h).
"""

from __future__ import annotations

import pandas as pd


def forward_return(panel: pd.DataFrame, horizon: int, entry: str = "next_close") -> pd.Series:
    g = panel.groupby(level="ticker")
    col = "open" if entry == "next_open" else "close"
    px = g[col].shift(-1)
    fut = g[col].shift(-1 - horizon)
    return (fut / px - 1).rename(f"fwd_{horizon}")


def make_label(panel: pd.DataFrame, cfg: dict) -> pd.Series:
    lc = cfg["label"]
    y = forward_return(panel, lc["horizon"], lc.get("entry", "next_close"))
    if lc["type"] == "excess_return":
        y = y - y.groupby(level="date").transform("mean")
    elif lc["type"] == "rank":
        y = y.groupby(level="date").rank(pct=True) - 0.5
    return y.rename("y")
