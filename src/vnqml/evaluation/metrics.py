"""Chỉ số dự báo và chỉ số danh mục."""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 250


def ic_series(pred: pd.Series, y: pd.Series, method: str = "spearman") -> pd.Series:
    df = pd.concat({"p": pred, "y": y}, axis=1).dropna()
    return df.groupby(level="date").apply(lambda g: g["p"].corr(g["y"], method=method))


def ic_summary(ic: pd.Series) -> dict:
    return {
        "ic_mean": ic.mean(),
        "ic_std": ic.std(),
        "icir": ic.mean() / ic.std() * np.sqrt(TRADING_DAYS / 5),
    }


def sharpe(r: pd.Series, periods: int = TRADING_DAYS) -> float:
    return float(r.mean() / r.std(ddof=1) * np.sqrt(periods)) if r.std() > 0 else 0.0


def max_drawdown(r: pd.Series) -> float:
    eq = (1 + r).cumprod()
    return float((eq / eq.cummax() - 1).min())


def portfolio_summary(r: pd.Series, turnover: pd.Series | None = None) -> dict:
    ann = (1 + r).prod() ** (TRADING_DAYS / max(len(r), 1)) - 1
    out = {
        "ann_return": ann,
        "ann_vol": r.std() * np.sqrt(TRADING_DAYS),
        "sharpe": sharpe(r),
        "max_dd": max_drawdown(r),
    }
    if turnover is not None:
        out["avg_turnover"] = turnover.mean()
    return out


def coverage(y: np.ndarray, lo: np.ndarray, hi: np.ndarray) -> float:
    return float(np.mean((y >= lo) & (y <= hi)))


def rolling_coverage(y: pd.Series, lo: pd.Series, hi: pd.Series, window: int = 63) -> pd.Series:
    hit = ((y >= lo) & (y <= hi)).astype(float).groupby(level="date").mean()
    return hit.rolling(window).mean()
